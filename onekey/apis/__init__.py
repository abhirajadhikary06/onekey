from __future__ import annotations

from typing import Any

from ..category_client import CategoryClient


class APIsClient(CategoryClient):
    def __init__(self, client):
        super().__init__(client, "apis")

    def create_payment_intent(self, provider: str, **kwargs: Any):
        payload = {"operation": "create_payment_intent"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def retrieve_payment_intent(self, provider: str, **kwargs: Any):
        payload = {"operation": "retrieve_payment_intent"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def list_customers(self, provider: str, **kwargs: Any):
        payload = {"operation": "list_customers"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def create_customer(self, provider: str, **kwargs: Any):
        payload = {"operation": "create_customer"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def send_sms(self, provider: str, **kwargs: Any):
        payload = {"operation": "send_sms"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def list_messages(self, provider: str, **kwargs: Any):
        payload = {"operation": "list_messages"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def send_email(self, provider: str, **kwargs: Any):
        payload = {"operation": "send_email"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def post_message(self, provider: str, **kwargs: Any):
        payload = {"operation": "post_message"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def list_channels(self, provider: str, **kwargs: Any):
        payload = {"operation": "list_channels"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def query_database(self, provider: str, **kwargs: Any):
        payload = {"operation": "query_database"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def create_page(self, provider: str, **kwargs: Any):
        payload = {"operation": "create_page"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def list_products(self, provider: str, **kwargs: Any):
        payload = {"operation": "list_products"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def create_product(self, provider: str, **kwargs: Any):
        payload = {"operation": "create_product"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def list_orders(self, provider: str, **kwargs: Any):
        payload = {"operation": "list_orders"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def create_message(self, provider: str, **kwargs: Any):
        payload = {"operation": "create_message"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def get_channel(self, provider: str, **kwargs: Any):
        payload = {"operation": "get_channel"}
        payload.update(kwargs)
        return self.call(provider, payload)


__all__ = ["APIsClient"]
