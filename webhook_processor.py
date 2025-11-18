from flask import Flask, request, jsonify
import requests
from datetime import datetime, timezone

app = Flask(__name__)

UTMIFY_URL = "https://api.utmify.com.br/webhook/transaction"

def master_to_utmify_status(master_status):
    if master_status == "waiting_payment":
        return "waiting_payment"
    if master_status == "paid":
        return "paid"
    if master_status == "refused":
        return "refused"
    if master_status == "refunded":
        return "refunded"
    return "waiting_payment"

@app.route("/masterpagbr-webhook", methods=["POST"])
def masterpag_webhook():
    try:
        data = request.json
        print("=== JSON RECEBIDO DA MASTER ===")
        print(data)

        tx = data.get("data", {})

        # Customer
        customer = tx.get("customer", {}) or {}
        document = customer.get("document", {}) or {}

        # Product
        items = tx.get("items", [])
        product = items[0] if items else {}

        # Datas formatadas
        created_at = tx.get("createdAt")
        if created_at:
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00")) \
                        .astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        paid_at = tx.get("paidAt")
        if paid_at:
            paid_at = datetime.fromisoformat(paid_at.replace("Z", "+00:00")) \
                        .astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # JSON da UTMIFY correto
        utm_json = {
            "orderId": str(tx.get("id")),
            "platform": "MasterPagBR",
            "paymentMethod": tx.get("paymentMethod"),
            "status": master_to_utmify_status(tx.get("status")),
            "createdAt": created_at,
            "approvedDate": paid_at,
            "refundedAt": tx.get("refundedAt"),
            "customer": {
                "name": customer.get("name"),
                "email": customer.get("email"),
                "phone": customer.get("phone"),
                "document": document.get("number"),
                "country": "BR",
                "ip": tx.get("ip") or "0.0.0.0"
            },
            "products": [
                {
                    "id": str(tx.get("id")),
                    "planId": None,
                    "planName": product.get("title"),
                    "name": product.get("title"),
                    "priceInCents": product.get("unitPrice", 0),
                    "quantity": product.get("quantity", 1)
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
                "totalPriceInCents": tx.get("amount", 0),
                "gatewayFeeInCents": tx.get("fee", {}).get("estimatedFee", 0),
                "userCommissionInCents": 0
            },
            "isTest": False
        }

        print("=== ENVIANDO PARA UTMIFY ===")
        print(utm_json)

        headers = {"Content-Type": "application/json"}
        response = requests.post(UTMIFY_URL, json=utm_json, headers=headers)

        print(">>> RESPOSTA UTMIFY:", response.status_code, response.text)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print("ERRO:", str(e))
        return jsonify({"error": str(e)}), 500


@app.route("/", methods=["GET"])
def home():
    return "Webhook MasterPagBR rodando!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
