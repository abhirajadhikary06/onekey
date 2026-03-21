from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrationRegistry:
    # Currently implemented and proxy-backed integrations.
    categories: dict[str, list[str]] = None
    # Planned integrations for upcoming categories.
    planned_categories: dict[str, list[str]] = None

    def __post_init__(self):
        if self.categories is None:
            object.__setattr__(
                self,
                "categories",
                {
                    "llm": [
                        "openai", "anthropic", "claude", "groq", "gemini", "openrouter", "mistral",
                        "together", "fireworks", "anyscale", "deepinfra", "nebius", "cohere",
                        "ai21", "perplexity", "deepseek", "qwen", "zhipu", "01ai", "grok",
                        "aleph_alpha", "replicate", "baseten", "huggingface",
                    ],
                    "database": ["neondb", "redis", "xata"],
                    "vector_db": ["pinecone", "weaviate", "qdrant", "milvus"],
                    "data_engineering": ["airbyte", "dbt", "fivetran"],
                    "devops": ["github", "gitlab", "bitbucket"],
                },
            )
        if self.planned_categories is None:
            object.__setattr__(
                self,
                "planned_categories",
                {
                    "database": ["supabase", "mongodb", "planetscale"],
                    "vector_db": ["chroma", "pgvector"],
                    "data_engineering": ["dagster", "prefect", "airflow"],
                    "devops": ["vercel", "render", "cloudflare"],
                    "apis": ["stripe", "twilio", "sendgrid", "slack", "notion", "shopify"],
                },
            )

    def providers_for(self, category: str) -> list[str]:
        return self.categories.get(category, [])

    def planned_for(self, category: str) -> list[str]:
        return self.planned_categories.get(category, [])

    def all_categories(self) -> list[str]:
        all_keys = set(self.categories.keys()) | set(self.planned_categories.keys())
        return sorted(all_keys)
