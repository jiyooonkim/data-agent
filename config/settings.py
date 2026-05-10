from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    slack_bot_token: str | None
    slack_app_token: str | None
    slack_max_reply_chars: int
    ollama_base_url: str
    ollama_sql_model: str
    ollama_doc_model: str
    ollama_embedding_model: str
    qa_default_limit: int
    doc_answer_chunk_limit: int
    openai_api_key: str | None
    openai_model: str
    openai_base_url: str | None
    notion_access_token: str | None
    notion_version: str
    notion_page_ids: list[str]
    google_credentials_file: str
    google_sheet_url: str
    google_worksheet_name: str
    google_worksheet_gid: int | None
    mart_table_name: str


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/postgres",
        ),
        slack_bot_token=os.getenv("SLACK_BOT_TOKEN"),
        slack_app_token=os.getenv("SLACK_APP_TOKEN"),
        slack_max_reply_chars=int(os.getenv("SLACK_MAX_REPLY_CHARS", "3000")),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_sql_model=os.getenv("OLLAMA_SQL_MODEL", "qwen3:8b"),
        ollama_doc_model=os.getenv("OLLAMA_DOC_MODEL", "qwen3:8b"),
        ollama_embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", "embeddinggemma"),
        qa_default_limit=int(os.getenv("QA_DEFAULT_LIMIT", "200")),
        doc_answer_chunk_limit=int(os.getenv("DOC_ANSWER_CHUNK_LIMIT", "5")),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        notion_access_token=os.getenv("NOTION_ACCESS_TOKEN"),
        notion_version=os.getenv("NOTION_VERSION", "2026-03-11"),
        notion_page_ids=[page_id.strip() for page_id in os.getenv("NOTION_PAGE_IDS", "").split(",") if page_id.strip()],
        google_credentials_file=os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"),
        google_sheet_url=os.getenv(
            "GOOGLE_SHEET_URL",
            "https://docs.google.com/spreadsheets/d/1a1kgbwfJs1N_fwvxBcojHnKykvfBfeiRM7VJz4z00K0/edit?gid=1134925394#gid=1134925394",
        ),
        google_worksheet_name=os.getenv("GOOGLE_WORKSHEET_NAME", ""),
        google_worksheet_gid=int(os.getenv("GOOGLE_WORKSHEET_GID")) if os.getenv("GOOGLE_WORKSHEET_GID") else None,
        mart_table_name=os.getenv("MART_TABLE_NAME", "public.meta_ads_daily"),
    )
