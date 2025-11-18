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

    print("\n=== JSON RECEBIDO DA MASTER (CURTO) ===")
    print(json.dumps(data, indent=4))

    # O ID da venda (vem do externalRef ou metadata)
    order_id = str(data.get("externalRef")) or str(data.get("metadata")) or "sem_id"

    # 🔥 Impede duplicações
    if order_id in processed_orders:
        print(">>> Pedido duplicado detectado. Ignorando:", order_id)
        return jsonify({"status": "duplicate_ignored"})

    processed_orders.add(order_id)

    # ===== PROCESSAR PRODUTO =====
    item = data.get("items", [{}])[0]

    product = {
        "id": order_id,
        "planId": order_id,
        "planName": item.get("title", "Plano"),
        "name": item.get("title", "Plano"),
        "priceInCents": item.get("unitPrice", 0) * 100,
        "quantity": item.get("quantity", 1)
    }

    # ===== CLIENTE =====
    customer = data.get("customer", {})

    payload = {
        "orderId": order_id,
        "platform": "MasterPagBR",
        "paymentMethod": data.get("paymentMethod"),
        "status": "paid",  # JSON curto, então já consideramos como pago
        "createdAt": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "approvedDate": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
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
            "src": None,
            "sck": None,
            "utm_source": None,
            "utm_campaign": None,
            "utm_medium": None,
            "utm_content": None,
            "utm_term": None
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
