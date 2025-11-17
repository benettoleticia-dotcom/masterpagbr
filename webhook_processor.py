# pegar dados do cliente no padrão do masterpagBR

customer_name = trx.get("customerName")
customer_email = trx.get("customerEmail")
customer_document = trx.get("customerDocument")

# itens do pedido
item = trx.get("items", [{}])[0]

product = {
    "id": str(trx.get("id")),
    "planId": str(trx.get("id")),
    "planName": item.get("name", "Produto"),
    "name": item.get("name", "Produto"),
    "priceInCents": item.get("value", 0) * 100,
    "quantity": item.get("quantity", 1)
}

payload = {
    "orderId": str(trx.get("id")),
    "platform": "MasterPagBR",
    "paymentMethod": trx.get("paymentMethod"),
    "status": trx.get("status"),
    "createdAt": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    "approvedDate": trx.get("paidAt"),
    "refundedAt": trx.get("refundedAt"),

    "customer": {
        "name": customer_name,
        "email": customer_email,
        "phone": trx.get("customerPhone"),
        "document": customer_document,
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
