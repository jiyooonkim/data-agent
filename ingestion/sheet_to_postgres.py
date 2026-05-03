from __future__ import annotations

from pathlib import Path

from config.settings import get_settings
from db.postgres import execute_sql_file, insert_many, upsert_many
from ingestion.google_sheets_usage_example import (
    DW_TABLE_CONFLICT_COLUMNS,
    DW_TABLE_INSERT_COLUMNS,
    DW_TABLE_UPDATE_COLUMNS,
    RAW_TABLE_INSERT_COLUMNS,
    build_usage_summary,
    read_usage_sheet_data,
)


DDL_SQL_PATH = Path(__file__).resolve().parent.parent / "sql" / "create_google_sheet_dw_tables.sql"
RAW_TABLE_NAME = "raw.google_sheet_table_blocks"
DW_TABLE_NAME = "dw.meta_ads_daily"


def load_sheet_to_postgres(
    sheet_url: str | None = None,
    worksheet_name: str = "sheet1",
    worksheet_gid: int | None = None,
):
    prepared = read_usage_sheet_data(
        sheet_url=sheet_url,
        worksheet_gid=worksheet_gid,
        worksheet_name=worksheet_name,
    )

    print("prepared >> ", prepared)

    execute_sql_file(str(DDL_SQL_PATH))

    raw_inserted = insert_many(
        prepared.raw_df,
        table_name=RAW_TABLE_NAME,
        columns=RAW_TABLE_INSERT_COLUMNS,
    )
    dw_upserted = upsert_many(
        prepared.dw_df,
        table_name=DW_TABLE_NAME,
        columns=DW_TABLE_INSERT_COLUMNS,
        conflict_columns=DW_TABLE_CONFLICT_COLUMNS,
        update_columns=DW_TABLE_UPDATE_COLUMNS,
    )

    summary = build_usage_summary(prepared)
    summary.update(
        {
            "raw_table_name": RAW_TABLE_NAME,
            "dw_table_name": DW_TABLE_NAME,
            "raw_inserted": raw_inserted,
            "dw_upserted": dw_upserted,
        }
    )
    return summary


def run():
    settings = get_settings()
    print("settings >> ", settings)
    return load_sheet_to_postgres(
        sheet_url=settings.google_sheet_url,
        worksheet_name=settings.google_worksheet_name or "sheet1",
        worksheet_gid=settings.google_worksheet_gid,
    )


if __name__ == "__main__":
    print(run())
