from __future__ import annotations

from config.settings import get_settings
from db.postgres import ensure_table_exists, insert_rows
from db.table_specs import META_ADS_DAILY_COLUMNS, META_ADS_DAILY_PRIMARY_KEY
from ingestion.google_sheets import parse_sheet_source, read_sheet_as_dataframe
from ingestion.meta_ads_transform import extract_dates, transform_meta_ads_sheet


def ensure_target_table(table_name: str):
    ensure_table_exists(
        table_name=table_name,
        ddl_columns=META_ADS_DAILY_COLUMNS,
        primary_key_columns=META_ADS_DAILY_PRIMARY_KEY,
    )


def load_sheet_to_postgres(
    sheet_url: str,
    worksheet_name: str = "",
    worksheet_gid: int | None = None,
    table_name: str | None = None,
    channel: str = "facebook",
):
    settings = get_settings()
    target_table = table_name or settings.mart_table_name
    source = parse_sheet_source(sheet_url)
    resolved_gid = worksheet_gid if worksheet_gid is not None else source.worksheet_gid

    source_df = read_sheet_as_dataframe(
        sheet_url=sheet_url,
        worksheet_name=worksheet_name,
        worksheet_gid=resolved_gid,
    )
    mart_df = transform_meta_ads_sheet(source_df, channel=channel)

    ensure_target_table(target_table)
    inserted_count = insert_rows(mart_df, table_name=target_table)

    return {
        "sheet_url": sheet_url,
        "worksheet_name": worksheet_name,
        "worksheet_gid": resolved_gid,
        "table_name": target_table,
        "source_rows": len(source_df),
        "mart_rows": len(mart_df),
        "inserted_rows": inserted_count,
        "detected_dates": extract_dates(source_df.columns),
    }


def run():
    settings = get_settings()
    source = parse_sheet_source(settings.google_sheet_url)
    resolved_gid = settings.google_worksheet_gid or source.worksheet_gid
    return load_sheet_to_postgres(
        sheet_url=settings.google_sheet_url,
        worksheet_name=settings.google_worksheet_name,
        worksheet_gid=resolved_gid,
        table_name=settings.mart_table_name,
        channel="facebook",
    )


if __name__ == "__main__":
    print(run())
