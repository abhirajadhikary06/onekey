from __future__ import annotations
from typing import Any, Iterator, Optional, Union

from ..client import OnekeyClient
from .schema import BaseMessage, HumanMessage, AIMessage, SystemMessage, convert_to_messages

class ChatOnekey:
    def __init__(
        self, 
        provider: str, 
        model: str, 
        base_url: Optional[str] = None, 
        platform_api_key: Optional[str] = None,
        **kwargs: Any
    ):
        self.provider = provider
        self.model = model
        self.kwargs = kwargs
        # Use the existing OnekeyClient logic
        self.client = OnekeyClient(base_url=base_url, platform_api_key=platform_api_key)

    def invoke(self, input: Union[str, list[Union[str, BaseMessage, dict[str, str]]]]) -> AIMessage:
        """Unified invoke method similar to LangChain."""
        messages = convert_to_messages(input)
        api_messages = [m.to_dict() for m in messages]
        
        resp = self.client.llm.chat(
            provider=self.provider,
            model=self.model,
            messages=api_messages,
            **self.kwargs
        )
        
        content = ""
        if "choices" in resp and len(resp["choices"]) > 0:
            content = resp["choices"][0]["message"].get("content", "")
        
        return AIMessage(content=content, additional_kwargs=resp)

    # Note: Real streaming would require backend support, but we can mimic it or wait for future implementation.
    # For now, we'll just implement invoke as it's the most common "LangChain-like" entry point shown in examples.
