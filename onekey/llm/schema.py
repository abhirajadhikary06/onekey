from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional, Union

@dataclass
class BaseMessage:
    content: str
    additional_kwargs: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, str]:
        raise NotImplementedError

@dataclass
class SystemMessage(BaseMessage):
    def to_dict(self) -> dict[str, str]:
        return {"role": "system", "content": self.content}

@dataclass
class HumanMessage(BaseMessage):
    def to_dict(self) -> dict[str, str]:
        return {"role": "user", "content": self.content}

@dataclass
class AIMessage(BaseMessage):
    def to_dict(self) -> dict[str, str]:
        return {"role": "assistant", "content": self.content}

MessageLike = Union[str, BaseMessage, dict[str, str]]

def convert_to_messages(inputs: Union[str, list[MessageLike]]) -> list[BaseMessage]:
    if isinstance(inputs, str):
        return [HumanMessage(content=inputs)]
    
    messages = []
    for m in inputs:
        if isinstance(m, str):
            messages.append(HumanMessage(content=m))
        elif isinstance(m, BaseMessage):
            messages.append(m)
        elif isinstance(m, dict):
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                messages.append(SystemMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))
    return messages
