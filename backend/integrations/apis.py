from fastapi import HTTPException, status

from .common import required


def map_api_operation(provider: str, operation: str, body: dict) -> dict:
    if provider == "stripe":
        if operation == "create_payment_intent":
            return {
                "method": "POST",
                "endpoint": "/payment_intents",
                "data": required(body, "payload", operation),
            }
        if operation == "retrieve_payment_intent":
            return {
                "method": "GET",
                "endpoint": f"/payment_intents/{required(body, 'payment_intent_id', operation)}",
            }
        if operation == "list_customers":
            return {"method": "GET", "endpoint": "/customers"}
        if operation == "create_customer":
            return {
                "method": "POST",
                "endpoint": "/customers",
                "data": required(body, "payload", operation),
            }

    if provider == "dodo_payments":
        if operation == "create_checkout_session":
            return {
                "method": "POST",
                "endpoint": "/checkouts",
                "json": required(body, "payload", operation),
            }
        if operation == "get_checkout_session":
            return {
                "method": "GET",
                "endpoint": f"/checkouts/{required(body, 'session_id', operation)}",
            }
        if operation == "create_customer":
            return {
                "method": "POST",
                "endpoint": "/customers",
                "json": required(body, "payload", operation),
            }
        if operation == "list_customers":
            return {"method": "GET", "endpoint": "/customers"}
        if operation == "retrieve_customer":
            return {
                "method": "GET",
                "endpoint": f"/customers/{required(body, 'customer_id', operation)}",
            }
        if operation == "create_subscription":
            return {
                "method": "POST",
                "endpoint": "/subscriptions",
                "json": required(body, "payload", operation),
            }
        if operation == "retrieve_usage_history":
            return {
                "method": "GET",
                "endpoint": f"/subscriptions/{required(body, 'subscription_id', operation)}/usage-history",
            }
        if operation == "ingest_usage_events":
            return {
                "method": "POST",
                "endpoint": "/usage-events",
                "json": required(body, "payload", operation),
            }

    if provider == "twilio":
        account_sid = required(body, "account_sid", operation)
        if operation == "send_sms":
            return {
                "method": "POST",
                "endpoint": f"/Accounts/{account_sid}/Messages.json",
                "basic_username": account_sid,
                "data": {
                    "To": required(body, "to", operation),
                    "From": required(body, "from", operation),
                    "Body": required(body, "body", operation),
                },
            }
        if operation == "list_messages":
            return {
                "method": "GET",
                "endpoint": f"/Accounts/{account_sid}/Messages.json",
                "basic_username": account_sid,
            }

    if provider == "sendgrid":
        if operation == "send_email":
            return {"method": "POST", "endpoint": "/mail/send", "json": required(body, "payload", operation)}
        if operation == "list_templates":
            return {"method": "GET", "endpoint": "/templates"}

    if provider == "slack":
        if operation == "post_message":
            return {
                "method": "POST",
                "endpoint": "/chat.postMessage",
                "json": {
                    "channel": required(body, "channel", operation),
                    "text": required(body, "text", operation),
                },
            }
        if operation == "list_channels":
            return {"method": "GET", "endpoint": "/conversations.list"}

    if provider == "notion":
        if operation == "query_database":
            return {
                "method": "POST",
                "endpoint": f"/databases/{required(body, 'database_id', operation)}/query",
                "json": body.get("payload", {}),
            }
        if operation == "create_page":
            return {"method": "POST", "endpoint": "/pages", "json": required(body, "payload", operation)}

    if provider == "shopify":
        if operation == "list_products":
            return {"method": "GET", "endpoint": "/admin/api/2024-10/products.json"}
        if operation == "create_product":
            return {
                "method": "POST",
                "endpoint": "/admin/api/2024-10/products.json",
                "json": required(body, "payload", operation),
            }
        if operation == "list_orders":
            return {"method": "GET", "endpoint": "/admin/api/2024-10/orders.json"}

    if provider == "discord":
        if operation == "create_message":
            return {
                "method": "POST",
                "endpoint": f"/channels/{required(body, 'channel_id', operation)}/messages",
                "json": {"content": required(body, "content", operation)},
            }
        if operation == "get_channel":
            return {"method": "GET", "endpoint": f"/channels/{required(body, 'channel_id', operation)}"}

    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        f"Unsupported apis operation '{operation}' for provider '{provider}'",
    )
