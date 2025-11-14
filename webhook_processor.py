import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime
import os

app = Flask(__name__)

UTMIFY_URL = "https://api.utmify.com.br/api-credentials/orders"
API_TOKEN = "QsbTenFjSEaR6ww4QXHwvOBV0qZRbs5IZEug"

@app.route("/masterpagbr-webhook", methods=["POST"])
def masterpagbr_webhook():
    data = request.json
    print("\n=== JSON RECEBIDO DA MASTER ===")
    print("================================")
    print(json.dumps(data, indent=4))

    trx = data.get("data", {})

    # PEGA O PRODUTO
    item = trx.get("items", [{}])[0]

    product = {
        "id": str(trx.get("id")),
        "planId": str(trx.get("id")),
        "planName": item.get("title", "Plano"),
        "name": item.get("title", "Plano"),
        "priceInCents": item.get("unitPrice", 0) * 100,
        "quantity": item.get("quantity", 1)
    }

    # DADOS DO CLIENTE
    customer = trx.get("customer", {})

    payload = {
        "orderId": str(trx.get("id")),
        "platform": "MasterPagBR",
        "paymentMethod": trx.get("paymentMethod"),
        "status": trx.get("status"),
        "createdAt": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "approvedDate": trx.get("paidAt"),
        "refundedAt": trx.get("refundedAt"),

        "customer": {
            "name": customer.get("name"),
            "email": customer.get("email"),
            "phone": customer.get("phone"),
            "document": customer.get("document", {}).get("number"),
            "country": "BR",
            "ip": trx.get("ip") or "0.0.0.0"
        },

        "products": [product],

        "trackingParameters": {
            "src": None,
            "sck": None,
            "utm_source": None,
            "utm_campaign": None,
            "utm_medium": None,
            "utm_content": None,
            "utm_term": None
        },

        "commission": {
            "totalPriceInCents": trx.get("amount", 0) * 100,
            "gatewayFeeInCents": 0,
            "userCommissionInCents": 0
        },

        "isTest": False
    }

    print("==============================")
    print("=== ENVIANDO À UTMIFY ===")
    print("==============================")
    print(payload)
    print("==============================\n")

    headers = {
        "Content-Type": "application/json",
        "x-api-token": API_TOKEN
    }

    try:
        print(">>> Enviando requisição para UTMIFY...")
        response = requests.post(UTMIFY_URL, json=payload, headers=headers)
        print(">>> Resposta da UTMIFY:", response.status_code, response.text)
    except Exception as e:
        print(">>> ERRO AO ENVIAR PARA A UTMIFY:", str(e))

    return jsonify({"status": "ok"})
