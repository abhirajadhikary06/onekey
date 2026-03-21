from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrationRegistry:
    # Currently implemented and proxy-backed integrations.
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
                        "ai21", "perplexity", "deepseek", "qwen", "grok",
                        "replicate", "baseten", "huggingface",
                    ],
                    "database": ["neondb", "xata", "supabase", "mongodb", "planetscale", "cockroachdb"],
                    "vector_db": ["pinecone", "weaviate", "qdrant", "milvus", "lancedb"],
                    "data_engineering": ["airbyte", "dbt", "fivetran", "dagster", "prefect", "astronomer", "meltano"],
                    "devops": ["github", "gitlab", "bitbucket", "vercel", "render", "cloudflare", "railway"],
                    "apis": ["stripe", "twilio", "sendgrid", "slack", "notion", "shopify", "discord"],
                },
            )

    def providers_for(self, category: str) -> list[str]:
        return self.categories.get(category, [])

    def all_categories(self) -> list[str]:
        return sorted(self.categories.keys())
