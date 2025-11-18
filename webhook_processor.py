import json
import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

UTMIFY_URL = "https://api.utmify.com.br/api-credentials/orders"
API_TOKEN = "izzLJJoH2orGwZFm7BgeruinzULoJ0hMv5fV"

processed_orders = set()

@app.route("/masterpagbr-webhook", methods=["POST"])
def masterpagbr_webhook():
    data = request.json

    print("\n=== JSON RECEBIDO DA MASTER ===")
    print(json.dumps(data, indent=4))

    # ID da compra
    order_id = (
        str(data.get("externalRef"))
        or str(data.get("metadata"))
        or "sem_id"
    )

    # Evitar duplicação
    if order_id in processed_orders:
        print(">>> Pedido já processado, ignorando:", order_id)
        return jsonify({"status": "duplicate_ignored"})

    processed_orders.add(order_id)

    # STATUS REAL vindo da MasterPag
    mp_status = data.get("status", "").lower()

    # MAPEAMENTO PARA UTMIFY
    status_map = {
        "waiting_payment": "pending",
        "pending": "pending",
        "paid": "paid",
        "approved": "paid",
        "expired": "refused",
        "canceled": "refused",
        "refused": "refused"
    }

    utm_status = status_map.get(mp_status, "pending")

    # DADOS DO PRODUTO
    item = data.get("items", [{}])[0]

    product = {
        "id": order_id,
        "planId": order_id,
        "planName": item.get("title", "Produto"),
        "name": item.get("title", "Produto"),
        "priceInCents": item.get("unitPrice", 0) * 100,
        "quantity": item.get("quantity", 1)
    }

    # CLIENTE
    customer = data.get("customer", {})

    payload = {
        "orderId": order_id,
        "platform": "MasterPagBR",
        "paymentMethod": data.get("paymentMethod"),
        "status": utm_status,

        "createdAt": data.get("createdAt", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
        "approvedDate": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S") if utm_status == "paid" else None,
        "refundedAt": None,

        "customer": {
            "name": customer.get("name"),
            "email": customer.get("email"),
            "phone": customer.get("phone"),
            "document": customer.get("document", {}).get("number"),
            "country": "BR",
            "ip": data.get("ip") or "0.0.0.0"
        },

        "products": [product],

        "trackingParameters": {
            "src": data.get("src"),
            "sck": data.get("sck"),
            "utm_source": data.get("utm_source"),
            "utm_campaign": data.get("utm_campaign"),
            "utm_medium": data.get("utm_medium"),
            "utm_content": data.get("utm_content"),
            "utm_term": data.get("utm_term")
        },

        "commission": {
            "totalPriceInCents": data.get("amount", 0) * 100,
            "gatewayFeeInCents": 0,
            "userCommissionInCents": 0
        },

        "isTest": False
    }

    print("\n=== ENVIANDO PARA UTMIFY ===")
    print(json.dumps(payload, indent=4))

    headers = {
        "Content-Type": "application/json",
        "x-api-token": API_TOKEN
    }

    try:
        response = requests.post(UTMIFY_URL, json=payload, headers=headers)
        print(">>> RESPOSTA UTMIFY:", response.status_code, response.text)
    except Exception as e:
        print(">>> ERRO AO ENVIAR PARA UTMIFY:", str(e))

    return jsonify({"status": "ok"})
