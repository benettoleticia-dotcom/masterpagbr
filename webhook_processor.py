import json
import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

UTMIFY_URL = "https://api.utmify.com.br/api-credentials/orders"
API_TOKEN = "izzLJJoH2orGwZFm7BgeruinzULoJ0hMv5fV"   # SUA CHAVE INSERIDA AQUI

@app.route("/masterpagbr-webhook", methods=["POST"])
def masterpagbr_webhook():
    data = request.json

    print("\n=== JSON RECEBIDO DA MASTER ===")
    print(json.dumps(data, indent=4))

    trx = data.get("data", {})

    # ITEM
    item = trx.get("items", [{}])[0]

    product = {
        "id": str(trx.get("id")),
        "planId": str(trx.get("id")),
        "planName": item.get("title", "Plano"),
        "name": item.get("title", "Plano"),
        "priceInCents": item.get("unitPrice", 0) * 100,
        "quantity": item.get("quantity", 1)
    }

    # CLIENTE
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

    print("\n=== ENVIANDO PARA UTMIFY ===")
    print(payload)

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
