from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ingestion.google_sheets import parse_sheet_source, read_sheet_as_dataframe, read_sheet_range_as_dataframe
from ingestion.meta_ads_transform import build_raw_block_record, transform_meta_ads_dw


DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1nr9X5IgwNPG-jn0xM-P5X7dH91B-rptcYiG4xJ5AsaE/edit?pli=1&gid=0#gid=0"

TABLE_SPECS = [
    {
        "table_name": "facebook",
        "channel": "facebook",
        "cell_range": "D5:M32",
        "header_row_indices": [0, 1],
    },
    {
        "table_name": "google",
        "channel": "google",
        "cell_range": "O4:X25",
        "header_row_indices": [1, 2],
    },
]

RAW_TABLE_INSERT_COLUMNS = [
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
]

DW_TABLE_INSERT_COLUMNS = [
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
]

DW_TABLE_CONFLICT_COLUMNS = [
    "spreadsheet_id",
    "worksheet_gid",
    "source_table_name",
    "channel",
    "event_date",
    "product_name",
    "campaign_name",
    "campaign_mapping",
]

DW_TABLE_UPDATE_COLUMNS = [
    "campaign_mapping",
    "budget",
    "spend",
    "revenue",
    "roas",
    "extracted_at",
    "loaded_at",
]


@dataclass(frozen=True)
class PreparedSheetData:
    spreadsheet_url: str
    spreadsheet_id: str
    worksheet_gid: int
    worksheet_name: str
    full_df: pd.DataFrame
    raw_df: pd.DataFrame
    dw_df: pd.DataFrame
    table_stats: list[dict]


def get_spreadsheet_id(spreadsheet_url: str) -> str:
    return spreadsheet_url.rstrip("/").split("/")[-1]


def resolve_usage_sheet_url(sheet_url: str | None = None) -> str:
    return sheet_url or DEFAULT_SHEET_URL


def read_usage_sheet_data(
    sheet_url: str | None = None,
    worksheet_gid: int | None = None,
    worksheet_name: str = "sheet1",
) -> PreparedSheetData:
    resolved_sheet_url = resolve_usage_sheet_url(sheet_url)
    source = parse_sheet_source(resolved_sheet_url)
    resolved_gid = worksheet_gid if worksheet_gid is not None else (source.worksheet_gid or 0)
    spreadsheet_id = get_spreadsheet_id(source.spreadsheet_url)

    full_df = read_sheet_as_dataframe(
        sheet_url=resolved_sheet_url,
        worksheet_gid=resolved_gid,
    )

    raw_records = []
    dw_frames = []
    table_stats = []

    for spec in TABLE_SPECS:
        table_df = read_sheet_range_as_dataframe(
            sheet_url=resolved_sheet_url,
            worksheet_gid=resolved_gid,
            cell_range=spec["cell_range"],
            header_row_indices=spec["header_row_indices"],
        )

        raw_records.append(
            build_raw_block_record(
                df=table_df,
                spreadsheet_id=spreadsheet_id,
                worksheet_gid=resolved_gid,
                worksheet_name=worksheet_name,
                table_name=spec["table_name"],
                cell_range=spec["cell_range"],
                channel=spec["channel"],
                header_row_index=spec["header_row_indices"][-1],
            )
        )
        dw_frames.append(
            transform_meta_ads_dw(
                df=table_df,
                spreadsheet_id=spreadsheet_id,
                worksheet_gid=resolved_gid,
                source_table_name=spec["table_name"],
                source_range=spec["cell_range"],
                channel=spec["channel"],
            )
        )
        table_stats.append(
            {
                "table_name": spec["table_name"],
                "channel": spec["channel"],
                "cell_range": spec["cell_range"],
                "header_row_index": spec["header_row_indices"][-1],
                "source_rows": len(table_df),
            }
        )

    raw_df = pd.DataFrame(raw_records)
    dw_df = pd.concat(dw_frames, ignore_index=True) if dw_frames else pd.DataFrame()

    return PreparedSheetData(
        spreadsheet_url=source.spreadsheet_url,
        spreadsheet_id=spreadsheet_id,
        worksheet_gid=resolved_gid,
        worksheet_name=worksheet_name,
        full_df=full_df,
        raw_df=raw_df,
        dw_df=dw_df,
        table_stats=table_stats,
    )


def build_usage_summary(prepared: PreparedSheetData) -> dict:
    return {
        "spreadsheet_url": prepared.spreadsheet_url,
        "spreadsheet_id": prepared.spreadsheet_id,
        "worksheet_gid": prepared.worksheet_gid,
        "worksheet_name": prepared.worksheet_name,
        "full_rows": len(prepared.full_df),
        "raw_rows": len(prepared.raw_df),
        "dw_rows": len(prepared.dw_df),
        "table_stats": prepared.table_stats,
    }


def main():
    prepared = read_usage_sheet_data()
    print("prepared >> ", prepared)
    summary = build_usage_summary(prepared)
    print(" summary >> ", summary)


if __name__ == "__main__":
    main()
