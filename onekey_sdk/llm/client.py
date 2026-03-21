from __future__ import annotations

from typing import Any

from ..client import OnekeyClient


class LLMClient:
    def __init__(self, client: OnekeyClient):
        self.client = client

    def chat(self, provider: str, model: str, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": model, "messages": messages}
        payload.update(kwargs)
        return self.client.invoke("llm", provider, payload)
