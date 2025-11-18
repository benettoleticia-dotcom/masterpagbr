import json
import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

UTMIFY_URL = "https://api.utmify.com.br/api-credentials/orders"
API_TOKEN = "izzLJJoH2orGwZFm7BgeruinzULoJ0hMv5fV"

# Controle interno para impedir vendas duplicadas
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

    # Evita duplicação
    if order_id in processed_orders:
        return jsonify({"status": "duplicate_ignored"})
    processed_orders.add(order_id)

    # CAPTURA O STATUS REAL
    status_master = data.get("status") or "pending"  # se não tiver, assume pendente

    # Converte para status UTMify
    status_map = {
        "paid": "paid",
        "approved": "paid",
        "pending": "pending",
        "waiting_payment": "pending",
        "expired": "refused",
        "refused": "refused"
    }

    status_final = status_map.get(status_master, "pending")

    # Produto
    item = data.get("items", [{}])[0]

    product = {
        "id": order_id,
        "planId": order_id,
        "planName": item.get("title", "Produto"),
        "name": item.get("title", "Produto"),
        "priceInCents": item.get("unitPrice", 0) * 100,
        "quantity": item.get("quantity", 1)
    }

    # Cliente
    customer = data.get("customer", {})

    payload = {
        "orderId": order_id,
        "platform": "MasterPagBR",
        "paymentMethod": data.get("paymentMethod"),
        "status": status_final,
        "createdAt": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "approvedDate": None if status_final != "paid" else datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "refundedAt": None,

        "customer": {
            "name": customer.get("name"),
            "email": customer.get("email"),
            "phone": customer.get("phone"),
            "document": customer.get("document", {}).get("number"),
            "country": "BR",
            "ip": "0.0.0.0"
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
