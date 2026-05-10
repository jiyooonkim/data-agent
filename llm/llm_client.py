from __future__ import annotations

import json
import logging

import requests

from config.settings import get_settings
from llm.prompt import DOC_SYSTEM_PROMPT, SYSTEM_PROMPT, build_doc_answer_prompt, build_sql_prompt, build_sql_repair_prompt


logger = logging.getLogger(__name__)

SQL_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "sql": {"type": "string"},
    },
    "required": ["sql"],
}


def _parse_sql_json(content: str, provider_name: str, model_name: str) -> str:
    parsed = json.loads(content)
    sql_text = parsed.get("sql", "").strip()
    if not sql_text:
        raise ValueError(f"{provider_name} response from {model_name} did not contain sql.")
    return sql_text


def _extract_ollama_text(payload: dict) -> str:
    return payload.get("response") or payload.get("thinking") or ""


def _call_ollama(user_prompt: str) -> str:
    settings = get_settings()
    response = requests.post(
        f"{settings.ollama_base_url}/api/generate",
        headers={"Content-Type": "application/json"},
        json={
            "model": settings.ollama_sql_model,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1},
            "prompt": f"{SYSTEM_PROMPT}\n\n{user_prompt}",
        },
        timeout=180,
    )
    response.raise_for_status()

    payload = response.json()
    content = _extract_ollama_text(payload)
    logger.info("Received SQL generation response from Ollama model %s.", settings.ollama_sql_model)
    return _parse_sql_json(content, "Ollama", settings.ollama_sql_model)


def _call_ollama_text(user_prompt: str) -> str:
    settings = get_settings()
    response = requests.post(
        f"{settings.ollama_base_url}/api/generate",
        headers={"Content-Type": "application/json"},
        json={
            "model": settings.ollama_doc_model,
            "stream": False,
            "options": {"temperature": 0.1},
            "prompt": f"{DOC_SYSTEM_PROMPT}\n\n{user_prompt}",
        },
        timeout=180,
    )
    response.raise_for_status()

    payload = response.json()
    content = _extract_ollama_text(payload).strip()
    if not content:
        raise ValueError(f"Ollama response from {settings.ollama_doc_model} was empty.")
    logger.info("Received document answer response from Ollama model %s.", settings.ollama_doc_model)
    return content


def embed_texts(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    payload = None

    for endpoint, request_json in [
        (
            "/api/embed",
            {
                "model": settings.ollama_embedding_model,
                "input": texts,
            },
        ),
        (
            "/api/embeddings",
            {
                "model": settings.ollama_embedding_model,
                "prompt": texts[0] if len(texts) == 1 else "\n\n".join(texts),
            },
        ),
    ]:
        response = requests.post(
            f"{settings.ollama_base_url}{endpoint}",
            headers={"Content-Type": "application/json"},
            json=request_json,
            timeout=180,
        )
        if response.status_code == 404:
            continue
        response.raise_for_status()
        payload = response.json()
        break

    if payload is None:
        raise ValueError("No supported Ollama embedding endpoint was available.")

    embeddings = payload.get("embeddings", [])
    if not embeddings and "embedding" in payload:
        embeddings = [payload["embedding"]]
    if len(embeddings) != len(texts):
        raise ValueError("Ollama embedding response count did not match input count.")
    logger.info(
        "Received %s embeddings from Ollama model %s.",
        len(embeddings),
        settings.ollama_embedding_model,
    )
    return embeddings

def generate_sql(question: str) -> str:
    settings = get_settings()
    return _call_ollama(
        build_sql_prompt(
            question=question,
            default_limit=settings.qa_default_limit,
        )
    )


def repair_sql(question: str, sql_text: str, error_text: str) -> str:
    settings = get_settings()
    return _call_ollama(
        build_sql_repair_prompt(
            question=question,
            sql_text=sql_text,
            error_text=error_text,
            default_limit=settings.qa_default_limit,
        )
    )


def generate_doc_answer(question: str, contexts: list[str]) -> str:
    return _call_ollama_text(build_doc_answer_prompt(question, contexts))
