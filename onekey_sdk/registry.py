from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrationRegistry:
    # Langchain-style grouping foundation. Add providers as backend support grows.
    categories: dict[str, list[str]] = None

    def __post_init__(self):
        if self.categories is None:
            object.__setattr__(
                self,
                "categories",
                {
                    "llm": [
                        "openai", "anthropic", "groq", "gemini", "openrouter", "mistral",
                        "together", "fireworks", "anyscale", "deepinfra", "nebius", "cohere",
                        "ai21", "perplexity", "deepseek", "qwen", "zhipu", "01ai", "grok",
                        "aleph_alpha", "replicate", "baseten", "huggingface",
                    ],
                    "database": ["neondb", "redis", "xata"],
                    "vector_db": ["pinecone", "weaviate", "qdrant", "milvus"],
                    "data_engineering": ["airbyte", "dbt", "fivetran"],
                    "devops": ["github", "gitlab", "bitbucket"],
                    "apis": ["stripe", "twilio", "sendgrid"],
                },
            )

    def providers_for(self, category: str) -> list[str]:
        return self.categories.get(category, [])

    def all_categories(self) -> list[str]:
        return sorted(self.categories.keys())
