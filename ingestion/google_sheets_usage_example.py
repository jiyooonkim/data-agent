from __future__ import annotations

from pathlib import Path
import logging

import pandas as pd

from db.postgres import execute_sql_file, insert_many, upsert_many
from ingestion.google_sheets import parse_sheet_source, read_sheet_as_dataframe, read_sheet_range_as_dataframe
from ingestion.meta_ads_transform import build_raw_block_record, transform_meta_ads_dw


logging.basicConfig(level=logging.INFO)


SHEET_URL = "https://docs.google.com/spreadsheets/d/1nr9X5IgwNPG-jn0xM-P5X7dH91B-rptcYiG4xJ5AsaE/edit?pli=1&gid=0#gid=0"
DDL_SQL_PATH = Path(__file__).resolve().parent.parent / "sql" / "create_google_sheet_dw_tables.sql"
RAW_TABLE_NAME = "raw.google_sheet_table_blocks"
DW_TABLE_NAME = "dw.meta_ads_daily"


def get_spreadsheet_id(spreadsheet_url: str) -> str:
    return spreadsheet_url.rstrip("/").split("/")[-1]


def build_raw_dataframe(spreadsheet_id: str, worksheet_gid: int, facebook_df: pd.DataFrame, google_df: pd.DataFrame):
    return pd.DataFrame(
        [
            build_raw_block_record(
                df=facebook_df,
                spreadsheet_id=spreadsheet_id,
                worksheet_gid=worksheet_gid,
                worksheet_name="sheet1",
                table_name="facebook",
                cell_range="D5:M32",
                channel="facebook",
                header_row_index=1,
            ),
            build_raw_block_record(
                df=google_df,
                spreadsheet_id=spreadsheet_id,
                worksheet_gid=worksheet_gid,
                worksheet_name="sheet1",
                table_name="google",
                cell_range="O4:X25",
                channel="google",
                header_row_index=2,
            ),
        ]
    )


def build_dw_dataframe(spreadsheet_id: str, worksheet_gid: int, facebook_df: pd.DataFrame, google_df: pd.DataFrame):
    facebook_dw_df = transform_meta_ads_dw(
        df=facebook_df,
        spreadsheet_id=spreadsheet_id,
        worksheet_gid=worksheet_gid,
        source_table_name="facebook",
        source_range="D5:M32",
        channel="facebook",
    )
    google_dw_df = transform_meta_ads_dw(
        df=google_df,
        spreadsheet_id=spreadsheet_id,
        worksheet_gid=worksheet_gid,
        source_table_name="google",
        source_range="O4:X25",
        channel="google",
    )
    return pd.concat([facebook_dw_df, google_dw_df], ignore_index=True)


def main():
    source = parse_sheet_source(SHEET_URL)
    worksheet_gid = source.worksheet_gid or 0
    spreadsheet_id = get_spreadsheet_id(source.spreadsheet_url)

    full_df = read_sheet_as_dataframe(sheet_url=SHEET_URL, worksheet_gid=worksheet_gid)
    facebook_df = read_sheet_range_as_dataframe(
        sheet_url=SHEET_URL,
        worksheet_gid=worksheet_gid,
        cell_range="D5:M32",
        header_row_index=1,
    )
    google_df = read_sheet_range_as_dataframe(
        sheet_url=SHEET_URL,
        worksheet_gid=worksheet_gid,
        cell_range="O4:X25",
        header_row_index=2,
    )

    execute_sql_file(str(DDL_SQL_PATH))

    raw_df = build_raw_dataframe(spreadsheet_id, worksheet_gid, facebook_df, google_df)
    raw_inserted = insert_many(
        raw_df,
        table_name=RAW_TABLE_NAME,
        columns=[
            "spreadsheet_id",
            "worksheet_gid",
            "worksheet_name",
            "table_name",
            "cell_range",
            "channel",
            "header_row_index",
            "source_columns",
            "source_rows",
            "extracted_at",
        ],
    )

    dw_df = build_dw_dataframe(spreadsheet_id, worksheet_gid, facebook_df, google_df)
    dw_upserted = upsert_many(
        dw_df,
        table_name=DW_TABLE_NAME,
        columns=[
            "spreadsheet_id",
            "worksheet_gid",
            "source_table_name",
            "source_range",
            "channel",
            "event_date",
            "product_name",
            "campaign_name",
            "campaign_mapping",
            "budget",
            "spend",
            "revenue",
            "roas",
            "extracted_at",
            "loaded_at",
        ],
        conflict_columns=[
            "spreadsheet_id",
            "worksheet_gid",
            "source_table_name",
            "channel",
            "event_date",
            "product_name",
            "campaign_name",
        ],
        update_columns=[
            "campaign_mapping",
            "budget",
            "spend",
            "revenue",
            "roas",
            "extracted_at",
            "loaded_at",
        ],
    )

    print("spreadsheet_url:", source.spreadsheet_url)
    print("worksheet_gid:", worksheet_gid)
    print("full_rows:", len(full_df))
    print("facebook_rows:", len(facebook_df))
    print("google_rows:", len(google_df))
    print("raw_inserted:", raw_inserted)
    print("dw_upserted:", dw_upserted)


if __name__ == "__main__":
    main()
