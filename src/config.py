from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    ai_provider: str
    embedding_provider: str
    openai_api_key: str | None
    openai_model: str
    openai_embedding_model: str
    ollama_base_url: str
    ollama_chat_model: str
    ollama_embedding_model: str
    slack_bot_token: str
    slack_app_token: str
    slack_allowed_channel_ids: frozenset[str]
    max_result_rows: int


def get_settings() -> Settings:
    allowed_channel_ids = frozenset(
        channel_id.strip()
        for channel_id in os.getenv("SLACK_ALLOWED_CHANNEL_IDS", "").split(",")
        if channel_id.strip()
    )
    ai_provider = os.getenv("AI_PROVIDER", "ollama").lower()
    embedding_provider = os.getenv("EMBEDDING_PROVIDER", ai_provider).lower()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    slack_bot_token = os.getenv("SLACK_BOT_TOKEN", "")
    slack_app_token = os.getenv("SLACK_APP_TOKEN", "")

    if ai_provider not in {"ollama", "openai"}:
        raise RuntimeError("AI_PROVIDER must be one of: ollama, openai.")

    if embedding_provider not in {"ollama", "openai"}:
        raise RuntimeError("EMBEDDING_PROVIDER must be one of: ollama, openai.")

    if "openai" in {ai_provider, embedding_provider} and (
        not openai_api_key or openai_api_key in {"sk-...", "sk"} or not openai_api_key.startswith("sk-")
    ):
        raise RuntimeError("OPENAI_API_KEY must be a real OpenAI API key starting with sk-.")

    return Settings(
        database_url=os.environ["DATABASE_URL"],
        ai_provider=ai_provider,
        embedding_provider=embedding_provider,
        openai_api_key=openai_api_key,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        openai_embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        ollama_chat_model=os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:3b"),
        ollama_embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
        slack_bot_token=slack_bot_token,
        slack_app_token=slack_app_token,
        slack_allowed_channel_ids=allowed_channel_ids,
        max_result_rows=int(os.getenv("MAX_RESULT_ROWS", "50")),
    )
