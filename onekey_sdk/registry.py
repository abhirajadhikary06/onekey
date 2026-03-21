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
                        "openai", "anthropic", "claude", "groq", "gemini", "openrouter", "mistral",
                        "together", "fireworks", "anyscale", "deepinfra", "nebius", "cohere",
                        "ai21", "perplexity", "deepseek", "qwen", "zhipu", "01ai", "grok",
                        "aleph_alpha", "replicate", "baseten", "huggingface",
                    ],
                    "database": ["neondb", "redis", "xata", "supabase", "mongodb", "planetscale", "cockroachdb"],
                    "vector_db": ["pinecone", "weaviate", "qdrant", "milvus", "chroma", "pgvector", "lancedb"],
                    "data_engineering": ["airbyte", "dbt", "fivetran", "dagster", "prefect", "airflow", "meltano"],
                    "devops": ["github", "gitlab", "bitbucket", "vercel", "render", "cloudflare", "railway"],
                    "apis": ["stripe", "twilio", "sendgrid", "slack", "notion", "shopify", "discord"],
                },
            )

    def providers_for(self, category: str) -> list[str]:
        return self.categories.get(category, [])

    def all_categories(self) -> list[str]:
        return sorted(self.categories.keys())
