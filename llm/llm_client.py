from __future__ import annotations

import json
import logging

import requests

from config.settings import get_settings
from llm.prompt import SYSTEM_PROMPT, build_sql_prompt, build_sql_repair_prompt


logger = logging.getLogger(__name__)


def _call_groq(user_prompt: str) -> str:
    settings = get_settings()
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is not configured.")

    response = requests.post(
        f"{settings.groq_base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.groq_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    logger.info("Received SQL generation response from Groq model %s.", settings.groq_model)
    parsed = json.loads(content)
    sql_text = parsed.get("sql", "").strip()
    if not sql_text:
        raise ValueError("Groq response did not contain sql.")
    return sql_text


def generate_sql(question: str) -> str:
    settings = get_settings()
    return _call_groq(
        build_sql_prompt(
            question=question,
            default_limit=settings.qa_default_limit,
        )
    )


def repair_sql(question: str, sql_text: str, error_text: str) -> str:
    settings = get_settings()
    return _call_groq(
        build_sql_repair_prompt(
            question=question,
            sql_text=sql_text,
            error_text=error_text,
            default_limit=settings.qa_default_limit,
        )
    )
