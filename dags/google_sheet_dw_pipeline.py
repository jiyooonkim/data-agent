from __future__ import annotations

from airflow.decorators import dag, task
from airflow.exceptions import AirflowFailException
from pendulum import datetime

from config.settings import get_settings
from db.postgres import run_query
from ingestion.sheet_to_postgres import extract_dates, read_sheet_as_dataframe, run


@dag(
    dag_id="google_sheet_to_dw",
    schedule="0 * * * *",
    start_date=datetime(2026, 5, 1, tz="Asia/Seoul"),
    catchup=False,
    tags=["dw", "google-sheet", "postgres"],
    default_args={"owner": "data-agent"},
)
def google_sheet_to_dw():
    @task
    def check_source() -> dict:
        settings = get_settings()
        df = read_sheet_as_dataframe(
            sheet_url=settings.google_sheet_url,
            worksheet_name=settings.google_worksheet_name,
        )
        if df.empty:
            raise AirflowFailException("Source worksheet is empty.")

        return {
            "source_rows": len(df),
            "detected_dates": extract_dates(df.columns),
        }

    @task
    def load_dw() -> dict:
        result = run()
        if result["mart_rows"] == 0:
            raise AirflowFailException("No mart rows were generated from the sheet.")
        return result

    @task
    def verify_dw_load(load_result: dict) -> dict:
        count_sql = """
            SELECT COUNT(*)
            FROM public.mart_ads_daily
            WHERE channel = %s
        """
        row_count = run_query(count_sql, ("facebook",))[0][0]
        if row_count <= 0:
            raise AirflowFailException("DW table has no loaded rows for channel=facebook.")

        return {
            "loaded_rows": load_result["inserted_rows"],
            "dw_total_rows": row_count,
        }

    source_status = check_source()
    load_status = load_dw()
    source_status >> load_status
    verify_dw_load(load_status)


google_sheet_to_dw()
