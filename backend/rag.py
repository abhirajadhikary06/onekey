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

Instructions:
1. If the SQL result contains 'general', answer the user's Question directly using your general knowledge as the friendly Onekey AI Assistant. Make it short, crisp, and concise!
2. Otherwise, write a very short, crisp, and direct answer to the user's question using ONLY the provided SQL result.
3. Do NOT add conversational filler (e.g., "I'd be happy to help", "Here is a summary").
4. Do NOT mention SQL, queries, or the database. Just give the final answer.
5. If the SQL result is empty, completely blank, or an error, return EXACTLY the following string and nothing else: "I couldn't find that information right now."
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

    # We need a strict prompt so Llama doesn't output markdown formatting
    # which breaks the SQLAlchemy execution.
    sql_prompt = PromptTemplate.from_template(
        """You are a PostgreSQL expert and the Onekey AI Assistant. 
Analyze the input question.
If the question is conversational (e.g., "hello", "hi") OR if it is a general question about Onekey (e.g., "what integrations do you support?", "what model are you?"), you MUST return EXACTLY this string and nothing else:
SELECT 'general';

BUT, if the question requires querying the user's data (API keys, logs, users), create a syntactically correct PostgreSQL query to run.
Unless the user specifies a specific number of examples to obtain, query for at most 5 results using the LIMIT clause.
Never query for all columns from a table. You must query only the columns that are needed to answer the question.
Pay attention to use only the column names you can see in the schema description. Be careful to not query for columns that do not exist.
Pay attention to which column is in which table.

Only use the following tables:
{table_info}

IMPORTANT: Return ONLY the raw SQL query. Do NOT wrap it in ```sql ... ``` markdown blocks.
Do NOT include any explanations or conversational text before or after the query. Just the SQL string.

Question: {question}"""
    )

    # Step 1: NL → SQL
    def get_schema(_):
        return db.get_table_info()
        
    def strip_markdown(text: str) -> str:
        text = text.strip()
        # Find the first SELECT, WITH, INSERT, UPDATE, DELETE etc.
        # Fallback to simple removal if that fails.
        if "```sql" in text:
            text = text.split("```sql")[1]
        elif "```" in text:
            text = text.split("```")[1]
            
        if "```" in text:
            text = text.split("```")[0]
            
        return text.strip()

    sql_chain = (
        RunnablePassthrough.assign(table_info=get_schema)
        | sql_prompt
        | llm
        | StrOutputParser()
        | strip_markdown
    )

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
