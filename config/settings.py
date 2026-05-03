from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    database_admin_url: str | None
    slack_bot_token: str | None
    slack_app_token: str | None
    slack_max_reply_chars: int
    groq_api_key: str | None
    groq_model: str
    groq_base_url: str
    qa_default_limit: int
    openai_api_key: str | None
    openai_model: str
    openai_base_url: str | None
    google_credentials_file: str
    google_sheet_url: str
    google_worksheet_name: str
    google_worksheet_gid: int | None
    mart_table_name: str


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql://data_agent:data_agent@localhost:5432/postgres",
        ),
        database_admin_url=os.getenv("DATABASE_ADMIN_URL"),
        slack_bot_token=os.getenv("SLACK_BOT_TOKEN"),
        slack_app_token=os.getenv("SLACK_APP_TOKEN"),
        slack_max_reply_chars=int(os.getenv("SLACK_MAX_REPLY_CHARS", "3000")),
        groq_api_key=os.getenv("GROQ_API_KEY"),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        groq_base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        qa_default_limit=int(os.getenv("QA_DEFAULT_LIMIT", "200")),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        google_credentials_file=os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"),
        google_sheet_url=os.getenv(
            "GOOGLE_SHEET_URL",
            "https://docs.google.com/spreadsheets/d/1a1kgbwfJs1N_fwvxBcojHnKykvfBfeiRM7VJz4z00K0/edit?gid=1134925394#gid=1134925394",
        ),
        google_worksheet_name=os.getenv("GOOGLE_WORKSHEET_NAME", ""),
        google_worksheet_gid=int(os.getenv("GOOGLE_WORKSHEET_GID")) if os.getenv("GOOGLE_WORKSHEET_GID") else None,
        mart_table_name=os.getenv("MART_TABLE_NAME", "public.meta_ads_daily"),
    )
