from __future__ import annotations

import logging
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


logger = logging.getLogger(__name__)


def load_sheet_to_postgres(
    sheet_url: str | None = None,
    worksheet_name: str = "sheet1",
    worksheet_gid: int | None = None,
):
    logger.info(
        "Starting sheet to PostgreSQL load. sheet_url=%s worksheet_name=%s worksheet_gid=%s",
        sheet_url,
        worksheet_name,
        worksheet_gid,
    )
    prepared = read_usage_sheet_data(
        sheet_url=sheet_url,
        worksheet_gid=worksheet_gid,
        worksheet_name=worksheet_name,
    )
    logger.info(
        "Prepared sheet data. spreadsheet_id=%s worksheet_gid=%s full_rows=%s raw_rows=%s dw_rows=%s",
        prepared.spreadsheet_id,
        prepared.worksheet_gid,
        len(prepared.full_df),
        len(prepared.raw_df),
        len(prepared.dw_df),
    )
    logger.info("Table stats: %s", prepared.table_stats)

    logger.info("Executing DDL SQL file: %s", DDL_SQL_PATH)
    execute_sql_file(str(DDL_SQL_PATH))
    logger.info("DDL execution completed.")

    logger.info("Inserting raw rows into %s", RAW_TABLE_NAME)
    raw_inserted = insert_many(
        prepared.raw_df,
        table_name=RAW_TABLE_NAME,
        columns=RAW_TABLE_INSERT_COLUMNS,
    )
    logger.info("Raw insert completed. inserted_rows=%s", raw_inserted)

    logger.info("Upserting DW rows into %s", DW_TABLE_NAME)
    dw_upserted = upsert_many(
        prepared.dw_df,
        table_name=DW_TABLE_NAME,
        columns=DW_TABLE_INSERT_COLUMNS,
        conflict_columns=DW_TABLE_CONFLICT_COLUMNS,
        update_columns=DW_TABLE_UPDATE_COLUMNS,
    )
    logger.info("DW upsert completed. upserted_rows=%s", dw_upserted)

    summary = build_usage_summary(prepared)
    summary.update(
        {
            "raw_table_name": RAW_TABLE_NAME,
            "dw_table_name": DW_TABLE_NAME,
            "raw_inserted": raw_inserted,
            "dw_upserted": dw_upserted,
        }
    )
    logger.info("Sheet to PostgreSQL load finished. summary=%s", summary)
    return summary


def run():
    settings = get_settings()
    logger.info(
        "Running sheet_to_postgres with settings. google_sheet_url=%s worksheet_name=%s worksheet_gid=%s",
        settings.google_sheet_url,
        settings.google_worksheet_name,
        settings.google_worksheet_gid,
    )
    return load_sheet_to_postgres(
        sheet_url=settings.google_sheet_url,
        worksheet_name=settings.google_worksheet_name or "sheet1",
        worksheet_gid=settings.google_worksheet_gid,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(load_sheet_to_postgres())
