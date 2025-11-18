import json
import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

UTMIFY_URL = "https://api.utmify.com.br/api-credentials/orders"
API_TOKEN = "izzLJJoH2orGwZFm7BgeruinzULoJ0hMv5fV"


# === SISTEMA DE IDEMPOTÊNCIA (evita duplicação) ===
PROCESSED_FILE = "processed_ids.json"

if not os.path.exists(PROCESSED_FILE):
    with open(PROCESSED_FILE, "w") as f:
        json.dump([], f)

def load_processed_ids():
    with open(PROCESSED_FILE, "r") as f:
        return json.load(f)

def save_processed_id(trx_id):
    ids = load_processed_ids()
    ids.append(trx_id)
    with open(PROCESSED_FILE, "w") as f:
        json.dump(ids, f)


@app.route("/masterpagbr-webhook", methods=["POST"])
def masterpagbr_webhook():

    data = request.json
    print("\n=== WEBHOOK RECEBIDO ===")
    print(json.dumps(data, indent=4))

    trx = data.get("data", {})
    status = trx.get("status")
    trx_id = str(trx.get("id"))

    # 🚨 1 — PROCESSAR SOMENTE STATUS = paid
    if status != "paid":
        print(f">>> Ignorado: status '{status}' não é 'paid'")
        return jsonify({"ignored": True})

    # 🚨 2 — BLOQUEAR IDs JÁ PROCESSADOS
    processed = load_processed_ids()
    if trx_id in processed:
        print(f">>> Pagamento {trx_id} já enviado para UTMify. Ignorando.")
        return jsonify({"duplicated": True})

    print(f">>> Pagamento {trx_id} será processado.")

    # === ITEM ===
    item = trx.get("items", [{}])[0]

    product = {
        "id": trx_id,
        "planId": trx_id,
        "planName": item.get("title"),
        "name": item.get("title"),
        "priceInCents": item.get("unitPrice", 0) * 100,
        "quantity": item.get("quantity", 1)
    }

    # === CLIENTE ===
    customer = trx.get("customer", {})

    payload = {
        "orderId": trx_id,
        "platform": "MasterPagBR",
        "paymentMethod": trx.get("paymentMethod"),
        "status": status,
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

        # ⚠ SE TUDO OK → salvar ID para evitar duplicação
        if response.status_code == 200:
            save_processed_id(trx_id)

    except Exception as e:
        print(">>> ERRO AO ENVIAR PARA UTMIFY:", str(e))

    return jsonify({"status": "processed"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
