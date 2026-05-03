from __future__ import annotations

from airflow.decorators import dag, task
from airflow.exceptions import AirflowFailException
from pendulum import datetime

from ingestion.sheet_to_postgres import load_sheet_to_postgres


@dag(
    dag_id="sheet_to_postgres",
    schedule="0 * * * *",
    start_date=datetime(2026, 5, 1, tz="Asia/Seoul"),
    catchup=False,
    tags=["google-sheet", "postgres", "dw"],
    default_args={"owner": "data-agent"},
)
def sheet_to_postgres():
    @task
    def load_sheet() -> dict:
        result = load_sheet_to_postgres()
        if result["dw_upserted"] <= 0:
            raise AirflowFailException("No DW rows were upserted.")
        return result

    load_sheet()


sheet_to_postgres()
