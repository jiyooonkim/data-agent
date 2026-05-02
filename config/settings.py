from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    openai_api_key: str | None
    openai_model: str
    openai_base_url: str | None
    google_credentials_file: str
    google_sheet_url: str
    google_worksheet_name: str
    mart_table_name: str


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql://data_agent:data_agent@localhost:5432/postgres",
        ),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        google_credentials_file=os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"),
        google_sheet_url=os.getenv(
            "GOOGLE_SHEET_URL",
            "https://docs.google.com/spreadsheets/d/1a1kgbwfJs1N_fwvxBcojHnKykvfBfeiRM7VJz4z00K0/edit?usp=sharing",
        ),
        google_worksheet_name=os.getenv("GOOGLE_WORKSHEET_NAME", ""),
        mart_table_name=os.getenv("MART_TABLE_NAME", "mart_ads_daily"),
    )
