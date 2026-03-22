from __future__ import annotations

from typing import Any

from ..client import OnekeyClient


class LLMClient:
    def __init__(self, client: OnekeyClient):
        self.client = client

    def chat(self, provider: str, model: str, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        """Send a chat completion request."""
        payload: dict[str, Any] = {"model": model, "messages": messages}
        payload.update(kwargs)
        return self.client.invoke("llm", provider, payload)

    def completion(self, provider: str, model: str, prompt: str, **kwargs: Any) -> dict[str, Any]:
        """Send a legacy text completion request."""
        payload: dict[str, Any] = {"model": model, "prompt": prompt}
        payload.update(kwargs)
        return self.client.invoke("llm", provider, payload)

    def embed(self, provider: str, model: str, input: str | list[str], **kwargs: Any) -> dict[str, Any]:
        """Generate text embeddings."""
        payload: dict[str, Any] = {"model": model, "input": input}
        payload.update(kwargs)
        return self.client.invoke("llm", provider, payload)
