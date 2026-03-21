"""
backend/rag.py
LangChain RAG using NeonDB (SQL-based retrieval) + Groq LLM.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_community.utilities import SQLDatabase
from langchain_groq import ChatGroq
from langchain_classic.chains import create_sql_query_chain
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from .config import DATABASE_URL, GROQ_API_KEY

# ── System context injected into every prompt ──────────────────────────────────
_SYSTEM_CONTEXT = """
You are the Onekey AI Assistant – an expert on the Onekey API-key management platform.
Onekey allows developers to store, manage, and use API keys (OpenAI, Anthropic, Groq, etc.)
through a single unified key.

You have access to these NeonDB Postgres tables:
- users        : registered user accounts (id, username, email, auth_method, is_subscribed, created_at)
- api_keys     : stored API keys per user (id, user_id, api_provider, name, expires_at, created_at)
- usage_logs   : request logs (id, user_id, api_key_id, api_provider, endpoint_or_model,
                               request_tokens, response_tokens, total_tokens, latency_ms,
                               status_code, created_at)

IMPORTANT SECURITY RULES – NEVER violate these:
- NEVER reveal encrypted_key, unified_key_encrypted, hashed_password, or any secret column.
- NEVER run INSERT, UPDATE, DELETE, DROP, or any mutating SQL.
- SELECT only the columns needed to answer the question.
- Aggregations and counts are fine.
- If a question is outside your knowledge, say so politely.
""".strip()

# ── Answer-synthesis prompt ────────────────────────────────────────────────────
_ANSWER_PROMPT = PromptTemplate.from_template(
    """{system_context}

Question: {question}
SQL query used: {query}
SQL result: {result}

Based on the above, write a clear, concise, friendly answer in plain English.
If the result is empty or an error, say "I couldn't find that information right now."
"""
)


@lru_cache(maxsize=1)
def _build_chain():
    """Build and cache the RAG chain (called once per process)."""
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your .env file: GROQ_API_KEY=gsk_..."
        )

    # Connect LangChain to NeonDB — restrict to safe read-only tables
    db = SQLDatabase.from_uri(
        DATABASE_URL,
        include_tables=["users", "api_keys", "usage_logs"],
        sample_rows_in_table_info=2,
    )

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=GROQ_API_KEY,
        temperature=0,
    )

    # Step 1: NL → SQL
    sql_chain = create_sql_query_chain(llm, db)

    # Step 2: Execute the generated SQL
    execute_query = QuerySQLDataBaseTool(db=db)

    # Step 3: Synthesise a human-readable answer
    answer_chain = (
        RunnablePassthrough.assign(query=sql_chain)
        .assign(result=lambda x: execute_query.invoke(x["query"]))
        .assign(system_context=lambda _: _SYSTEM_CONTEXT)
        | _ANSWER_PROMPT
        | llm
        | StrOutputParser()
    )

    return answer_chain


def ask_rag(question: str) -> str:
    """Main entry-point: ask a natural-language question, get an answer."""
    try:
        chain = _build_chain()
        return chain.invoke({"question": question})
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Sorry, I ran into an error: {e}"
