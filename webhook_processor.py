import json
import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# 🔑 SUA KEY DA UTMIFY
API_TOKEN = "izzLJJoH2orGwZFm7BgeruinzULoJ0hMv5fV"
UTMIFY_URL = "https://api.utmify.com.br/api-credentials/orders"

# Controle interno para impedir duplicações
processed_orders = set()

def gerar_order_id(mp):
    """
    Gera um orderId confiável garantindo que nunca será None.
    PRIORIDADE:
    1) externalRef (se existir)
    2) metadata (se for numérico)
    3) id da transação MasterPag
    """
    external = mp.get("externalRef")
    metadata = mp.get("metadata")
    trans_id = mp.get("id")

    # 1 — externalRef válido
    if external and str(external).strip() != "" and external != "null":
        return str(external)

    # 2 — metadata numérico (evita nomes como "Plano Semanal")
    if metadata and str(metadata).isdigit():
        return str(metadata)

    # 3 — último fallback: ID da transação MasterPag (sempre existe)
    return str(trans_id)


@app.route("/masterpagbr-webhook", methods=["POST"])
def masterpagbr_webhook():
    data = request.json

    print("\n=== JSON RECEBIDO DA MASTER ===")
    print(json.dumps(data, indent=4))

    # O MasterPag envia tudo dentro de "data"
    mp = data.get("data", {})

    # Gera orderId seguro
    order_id = gerar_order_id(mp)

    # Verifica duplicação
    if order_id in processed_orders:
        print(f">>> Pedido já processado, ignorando: {order_id}")
        return jsonify({"status": "duplicate_ignored"})
    processed_orders.add(order_id)

    # Mapeamento de status MasterPag → UTMify
    mp_status = mp.get("status")

    if mp_status == "paid":
        utm_status = "paid"
    elif mp_status == "waiting_payment":
        utm_status = "waiting_payment"
    elif mp_status == "refused":
        utm_status = "refused"
    elif mp_status == "refunded":
        utm_status = "refunded"
    else:
        utm_status = "waiting_payment"

    # CLIENTE
    customer = mp.get("customer", {})

    # PRODUTO
    item = mp.get("items", [{}])[0]

    payload = {
        "orderId": order_id,
        "platform": "MasterPagBR",
        "paymentMethod": mp.get("paymentMethod"),
        "status": utm_status,

        "createdAt": mp.get("createdAt", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
        "approvedDate": mp.get("paidAt"),
        "refundedAt": mp.get("refundedAt"),

        "customer": {
            "name": customer.get("name"),
            "email": customer.get("email"),
            "phone": customer.get("phone"),
            "document": customer.get("document", {}).get("number"),
            "country": "BR",
            "ip": "0.0.0.0"
        },

        "products": [
            {
                "id": order_id,
                "planId": item.get("externalRef") or order_id,
                "planName": item.get("title", "Produto"),
                "name": item.get("title", "Produto"),
                "priceInCents": int(item.get("unitPrice", 0)),
                "quantity": item.get("quantity", 1)
            }
        ],

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
            "totalPriceInCents": int(mp.get("amount", 0)),
            "gatewayFeeInCents": int(mp.get("fee", {}).get("estimatedFee", 0)),
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
