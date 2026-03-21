# Onekey AI Knowledge Base

Last updated: 2026-03-21
Scope: repository-wide product and implementation facts for AI assistants.

## 1. Product Summary
Onekey is a FastAPI-based API-key vault and proxy platform.
It stores user API keys in encrypted form, authenticates users with JWT or OAuth, and proxies provider requests through unified routes.
It also includes a Python SDK (onekey_sdk), a static web frontend, and a RAG chatbot endpoint.

## 2. Repository Structure
- backend: FastAPI application code (auth, vault, proxy, usage, rag)
- frontend: static HTML/CSS/JS UI mounted at /static
- onekey_sdk: Python SDK with category clients and provider registry
- build.py: local binary build helper using PyInstaller
- Dockerfile: container build for backend + frontend static assets
- requirements.txt: Python dependencies

## 3. Runtime Entry Points
- API app: backend.main:app
- Root path / redirects to /static/index.html
- Mounted static assets: /static -> frontend directory

## 4. Core Architecture
- Auth layer: JWT + OAuth routes in backend.auth
- Current user resolution: backend.dependencies.get_current_user
- Vault layer: backend.vault for key CRUD and platform key retrieval
- Proxy layer: backend.proxy for provider/category request forwarding
- Usage layer: backend.usage for usage log retrieval
- RAG layer: backend.rag_router + backend.rag for SQL-backed assistant

## 5. Auth and Identity
Supported auth methods in user records:
- jwt
- github
- gitlab
- bitbucket

JWT behavior:
- HS256 signing using JWT_SECRET
- Subject claim stores user id as string
- Expiration uses JWT_EXPIRATION_MINUTES

Primary auth endpoints:
- POST /auth/register
- POST /auth/login
- GET /auth/me
- POST /auth/password
- GET /auth/github/login
- GET /auth/github/callback
- GET /auth/gitlab/login
- GET /auth/gitlab/callback
- GET /auth/bitbucket/login
- GET /auth/bitbucket/callback
- DELETE /auth/account

## 6. Data Model (Current)
users table (key fields):
- id
- username
- hashed_password (nullable for OAuth users)
- email
- github_id / gitlab_id / bitbucket_id
- github_username / gitlab_username / bitbucket_username
- auth_method
- is_subscribed
- platform_unified_key_encrypted
- created_at

api_keys table (key fields):
- id
- user_id
- api_provider
- name
- name_slug
- encrypted_key
- unified_key_encrypted (legacy field)
- unified_endpoint (legacy-compatible field)
- expires_at
- created_at

usage_logs table (key fields):
- id
- user_id
- api_key_id
- api_provider
- endpoint_or_model
- request_tokens
- response_tokens
- total_tokens
- latency_ms
- status_code
- created_at

Unique constraints:
- api_keys has unique constraint on (user_id, api_provider, name_slug)

## 7. Key Management Flow
When adding a key:
1. Request is authenticated as current user.
2. Provider is either explicit or auto-detected from key prefix.
3. Key is encrypted using Fernet before DB write.
4. A per-user platform key is created on demand if missing.
5. Response includes masked provider key and platform key.

Vault endpoints:
- POST /keys
- GET /keys
- GET /keys/status
- GET /keys/platform-key
- DELETE /keys/{key_id}
- POST /keys/upgrade

## 8. Encryption and Secrets
- Encryption primitive: cryptography.fernet.Fernet
- Encryption key source: ENCRYPTION_KEY environment variable
- Stored provider keys are encrypted at rest
- Platform unified key is encrypted at rest

Security notes for AI consumers:
- Treat ENCRYPTION_KEY and JWT_SECRET as high-risk secrets.
- Never expose encrypted_key, unified_key_encrypted, hashed_password.
- Never suggest logging plaintext provider keys.

## 9. Proxy Routes and Auth Modes
User JWT routes:
- POST /proxy/{provider}/{name_slug}
- POST /proxy/{provider}

Platform key routes:
- POST /proxy/u/{provider}/{name_slug}
- POST /proxy/sdk/{category}/{provider}/{name_slug}
- POST /proxy/sdk/{category}/{provider}

Behavior:
- Provider aliases are canonicalized (claude -> anthropic)
- Provider/category mismatch is rejected
- Expired keys are rejected
- Usage logs are written for proxy calls

## 10. Supported Provider Categories (Current)
LLM:
- openai
- groq
- anthropic
- gemini
- openrouter
- mistral
- together
- fireworks
- anyscale
- deepinfra
- nebius
- cohere
- ai21
- perplexity
- deepseek
- qwen
- grok
- replicate
- baseten
- huggingface

Vector DB:
- pinecone
- weaviate
- qdrant
- milvus
- lancedb

Database:
- neondb
- xata
- supabase
- mongodb
- planetscale
- cockroachdb

Data Engineering:
- airbyte
- dbt
- fivetran
- dagster
- prefect
- astronomer
- meltano

DevOps:
- github
- gitlab
- bitbucket
- vercel
- render
- cloudflare
- railway

APIs:
- stripe
- twilio
- sendgrid
- slack
- notion
- shopify
- discord

## 11. Provider Auto-Detection
Auto-detection is prefix/regex based in backend.provider_detection.
Not all providers can be reliably identified from key shape.
System fallback: caller can explicitly pass provider when creating keys.

Important implementation caveat:
- Prefix map currently contains overlapping patterns (example: sk- mapped more than once).
- Assistants should prefer explicit provider for ambiguous keys.

## 12. SDK Contract
Core client:
- OnekeyClient(base_url, platform_api_key, timeout)
- invoke(category, provider, payload) posts to /proxy/sdk/{category}/{provider}

LLM client:
- LLMClient.chat(provider, model, messages, **kwargs)

SDK registry categories are defined in onekey_sdk.registry.IntegrationRegistry.

## 13. Usage API Contract
- GET /usage returns list of serialized usage logs for current user
- GET /usage/{key_id} returns key metadata plus logs for that key

Serialized log fields:
- id
- api_key_id
- provider
- model
- status
- latency_ms
- total_tokens
- created_at

## 14. RAG Chatbot
Endpoint:
- POST /chat

Request:
- question: string

Response:
- answer: string

RAG design:
- Uses LangChain + ChatGroq
- Generates SQL against users, api_keys, usage_logs
- Enforces prompt-level read-only guidance
- Returns concise answer text

## 15. Frontend Facts
- Frontend is static and served from /static
- Main operational pages include dashboard, integrations, usage pages, profile, docs
- Integrations page renders provider cards from in-file category arrays
- Provider logos are loaded from frontend/static/images/logos

## 16. Build and Deployment Facts
Dockerfile:
- Multi-stage Python 3.11 alpine build
- Copies backend and frontend
- Runs uvicorn backend.main:app on port 8000

build.py:
- PyInstaller onefile build helper for a CLI script named cli.py
- Output binary moved into bin directory

## 17. AI Safety and Grounding Rules for this Repo
Use these rules when generating responses/code:
1. Prefer facts from code over README claims when they conflict.
2. Treat provider support as implementation-defined by backend.proxy and registry.
3. Do not assume all provider keys are auto-detectable.
4. Do not output or request real secret values in examples.
5. Use masked keys in sample outputs.
6. Mention when a route requires JWT versus platform key.

## 18. Known Inconsistencies to Watch
- README may describe security/architecture details that differ from current code.
- provider_detection has overlapping prefixes that can cause ambiguity.
- Some logos and provider display aliases are frontend-only conventions.

## 19. Recommended AI Prompt Seed
Use this as a base system context when feeding another AI:
"You are assisting with the Onekey repository. Ground all answers in the current codebase. Distinguish JWT-auth routes from platform-key routes. Never expose secrets. Prefer explicit provider selection when key auto-detection may be ambiguous."
