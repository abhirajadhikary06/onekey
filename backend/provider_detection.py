"""
Auto-detection of API provider based on key prefix patterns.
Add new providers here to expand platform support.
"""

import re

# Map of key prefixes to provider names
# Ordered by specificity (more specific prefixes first)
PROVIDER_PREFIX_MAP = {
    # Specific prefixes before broad/shared patterns
    "sk-or-": "openrouter",
    "sk-live-": "stripe",
    "sk-test-": "stripe",
    "shpat_": "shopify",
    "shpca_": "shopify",
    "secret_": "notion",
    "ntn_": "notion",
    "xoxb-": "slack",
    "xoxp-": "slack",
    "xapp-": "slack",
    "xoxa-": "slack",
    "SG.": "sendgrid",
    "sk-ant-": "anthropic",
    "claude-": "anthropic",
    "sk-proj-": "openai",
    "sk-svcacct-": "openai",
    "sk-": "openai",
    "AIza": "gemini",
    "xai-": "grok",
    "gsk_": "groq",
    "mistral_": "mistral",
    "together_": "together",
    "fw-": "fireworks",
    "as-": "anyscale",
    "di_": "deepinfra",
    "neb-": "nebius",
    "nb-": "nebius",
    "co_": "cohere",
    "ai21_": "ai21",
    "aa_": "aleph_alpha",
    "r8_": "replicate",
    "bt_": "baseten",
    "hf_": "huggingface",
    "pplx-": "perplexity",
    "ds_": "deepseek",
    "qwen_": "qwen",
    "glm_": "zhipu",
    "yi_": "01ai",
    "neon_": "neondb",
    "rs_": "redis",
    "sbp_": "supabase",
    "pscale_tkn_": "planetscale",
    "crdb_": "cockroachdb",
    "pcsk_": "pinecone",
    "wcs_": "weaviate",
    "qdr_": "qdrant",
    "milvus_": "milvus",
    "chroma_": "chroma",
    "pgv_": "pgvector",
    "lancedb_": "lancedb",
    "xau_": "xata",
    "ab_": "airbyte",
    "dbtc_": "dbt",
    "fivetran_": "fivetran",
    "dag_": "dagster",
    "pnu_": "prefect",
    "pnb_": "prefect",
    "airflow_": "airflow",
    "meltano_": "meltano",
    "ghp_": "github",
    "github_pat_": "github",
    "glpat-": "gitlab",
    "bbat-": "bitbucket",
    "vercel_": "vercel",
    "rnd_": "render",
    "cfpat_": "cloudflare",
    "railway_": "railway",
    "discord_": "discord",
}


# Regex patterns for keys that can be recognized beyond simple prefixes.
# Keep these strict to avoid accidental provider misclassification.
PROVIDER_REGEX_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^github_pat_[A-Za-z0-9_]+$"), "github"),
    (re.compile(r"^ghp_[A-Za-z0-9]+$"), "github"),
    (re.compile(r"^glpat-[A-Za-z0-9_-]+$"), "gitlab"),
    (re.compile(r"^SG\.[A-Za-z0-9_-]+$"), "sendgrid"),
    (re.compile(r"^xox[bap]-[A-Za-z0-9-]+$"), "slack"),
    (re.compile(r"^shpat_[A-Za-z0-9]+$"), "shopify"),
    (re.compile(r"^sk_(live|test)_[A-Za-z0-9]+$"), "stripe"),
    (re.compile(r"^SQ[A-Za-z0-9]{32}$"), "twilio"),
    (re.compile(r"^SK[A-Za-z0-9]{32}$"), "twilio"),
    (re.compile(r"^AC[A-Za-z0-9]{32}$"), "twilio"),
    (re.compile(r"^pnu_[A-Za-z0-9]+$"), "prefect"),
    (re.compile(r"^pnb_[A-Za-z0-9]+$"), "prefect"),
]


def detect_provider(api_key: str) -> str:
    """
    Auto-detect the provider from an API key based on its prefix.
    
    Args:
        api_key: The API key string to analyze
        
    Returns:
        Provider name (e.g., 'openai', 'anthropic', 'groq')
        
    Raises:
        ValueError: If the provider cannot be detected
    """
    if not api_key or not isinstance(api_key, str):
        raise ValueError("Invalid API key")
    
    api_key = api_key.strip()

    # Regex checks first where format guarantees better classification.
    for pattern, provider in PROVIDER_REGEX_PATTERNS:
        if pattern.match(api_key):
            return provider
    
    # Check prefixes in order (most specific first)
    for prefix, provider in PROVIDER_PREFIX_MAP.items():
        if api_key.startswith(prefix):
            return provider
    
    # If no match found
    raise ValueError(
        f"Could not detect provider from API key. "
        f"Key should start with a known prefix like: {', '.join(list(PROVIDER_PREFIX_MAP.keys())[:5])}... "
        f"For providers that do not expose stable key prefixes, pass provider explicitly."
    )


def get_supported_providers() -> list[str]:
    """
    Get a list of all supported provider names.
    
    Returns:
        Sorted list of unique provider names
    """
    return sorted(set(PROVIDER_PREFIX_MAP.values()))
