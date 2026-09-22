"""
LLM Client Module
Handles all OpenRouter API interactions for SQL generation and reflection.
Uses a module-level httpx.AsyncClient for connection pooling.
"""

import logging
from typing import Optional

import httpx

from backend.schema_context import get_schema_context

logger = logging.getLogger(__name__)

# Module-level client for connection reuse — initialized/closed via FastAPI lifespan
_client: Optional[httpx.AsyncClient] = None


async def init_client() -> None:
    """Initialize the shared HTTP client. Call from FastAPI lifespan startup."""
    global _client
    _client = httpx.AsyncClient(timeout=15.0)
    logger.info("HTTP client initialized for OpenRouter API.")


async def close_client() -> None:
    """Close the shared HTTP client. Call from FastAPI lifespan shutdown."""
    global _client
    if _client:
        await _client.aclose()
        _client = None
        logger.info("HTTP client closed.")


def _get_client() -> httpx.AsyncClient:
    """Get the shared client, creating a fallback if lifespan hasn't run."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=15.0)
    return _client


def _build_headers(api_key: str) -> dict:
    """Build standard OpenRouter request headers."""
    return {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/aus-gov-data-explorer",
        "X-Title": "Aus Gov Data Explorer",
        "Content-Type": "application/json",
    }


async def generate_sql_with_openrouter(
    question: str, api_key: str, model: str
) -> Optional[str]:
    """Generates SQL query using OpenRouter chat completion."""
    from backend.query_service import extract_sql_from_text

    schema_ctx = get_schema_context()
    system_prompt = (
        f"{schema_ctx}\n\n"
        "Generate a single, syntactically correct SQLite query answering the user's question.\n"
        "Return ONLY the SQL code inside a ```sql ... ``` block. Do not provide prose explanations."
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        "temperature": 0.0,
        "max_tokens": 300,
    }

    try:
        client = _get_client()
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=_build_headers(api_key),
            json=payload,
        )
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return extract_sql_from_text(content)
        else:
            logger.warning("OpenRouter SQL generation failed: status=%d body=%s", resp.status_code, resp.text[:200])
    except Exception:
        logger.exception("OpenRouter SQL generation exception")

    return None


async def generate_sql_reflection_with_openrouter(
    question: str,
    failed_sql: str,
    error_message: str,
    api_key: str,
    model: str,
) -> Optional[str]:
    """Feeds SQL error back to LLM to self-heal the query."""
    from backend.query_service import extract_sql_from_text

    schema_ctx = get_schema_context()
    system_prompt = (
        f"{schema_ctx}\n\n"
        "You are an expert SQLite debugger. A previously generated SQL query failed to run "
        "or returned 0 rows unexpectedly.\n"
        "Analyze the error or warning, inspect the schema context, and provide a CORRECTED SQLite query.\n"
        "Return ONLY the corrected SQL inside a ```sql ... ``` code block. Do not provide prose explanations."
    )
    user_prompt = (
        f"Original User Question: {question}\n"
        f"Failed SQL: {failed_sql}\n"
        f"Execution Error / Issue: {error_message}\n\n"
        "Generate the corrected SQL query:"
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 350,
    }

    try:
        client = _get_client()
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=_build_headers(api_key),
            json=payload,
        )
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return extract_sql_from_text(content)
        else:
            logger.warning("OpenRouter reflection failed: status=%d", resp.status_code)
    except Exception:
        logger.exception("OpenRouter reflection exception")

    return None


async def generate_grounded_insight(
    question: str,
    stats: dict,
    api_key: str,
    model: str = "meta-llama/llama-3.3-70b-instruct:free",
) -> Optional[str]:
    """Prompts OpenRouter to articulate insight strictly using pre-computed stats."""
    import json

    system_prompt = (
        "You are an analytical narrator presenting official Australian Bureau of Statistics (ABS) labour data.\n"
        "You are given a user question and a STRICT JSON dictionary of PRE-COMPUTED statistics extracted directly from the database.\n\n"
        "STRICT GUARDRAILS:\n"
        "1. Formulate 1 to 2 clear, natural sentences answering the user's question.\n"
        "2. State ONLY figures, dates, and regions that explicitly exist in the COMPUTED_STATS JSON.\n"
        "3. You are FORBIDDEN from calculating, estimating, or introducing ANY other numbers.\n"
        "4. Never invent causes or assumptions. Stick purely to the supplied data."
    )

    user_prompt = (
        f"User Question: {question}\n\n"
        f"COMPUTED_STATS:\n{json.dumps(stats, indent=2)}\n\n"
        f"Generate the grounded insight sentence:"
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 150,
    }

    try:
        client = _get_client()
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=_build_headers(api_key),
            json=payload,
        )
        if resp.status_code == 200:
            data = resp.json()
            msg = data["choices"][0]["message"]
            content = (msg.get("content") or "").strip()
            if content:
                return content
        else:
            logger.warning("OpenRouter narration failed: status=%d", resp.status_code)
    except Exception:
        logger.exception("OpenRouter narration exception")

    return None
