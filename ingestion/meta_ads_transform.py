from __future__ import annotations

from datetime import datetime
import re

import pandas as pd


DATE_COLUMN_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})_(.+)$")


def clean_number(value):
    if pd.isna(value) or value == "":
        return 0.0
    text = str(value).replace(",", "").replace("%", "").strip()
    if text.upper() in {"", "-", "--", "#N/A", "N/A", "NA", "NULL"}:
        return 0.0
    return float(text)


def extract_dates(columns) -> list[str]:
    dates = set()
    for column in columns:
        match = DATE_COLUMN_PATTERN.match(str(column))
        if match:
            dates.add(match.group(1))
    return sorted(dates)


def is_summary_row(campaign_value) -> bool:
    if campaign_value is None:
        return True
    text = str(campaign_value).strip()
    if not text:
        return True
    return text in {"총계", "합계"} or "SUMMARY" in text.upper()


def build_record(row, date: str, channel: str) -> dict:
    product = row.get("상품명") or row.get("광고세트") or row.get("상품") or ""
    return {
        "date": date,
        "channel": channel,
        "product": str(product).strip(),
        "campaign": str(row.get("캠페인", "")).strip(),
        "spend": clean_number(row.get(f"{date}_지출금액")),
        "revenue": clean_number(row.get(f"{date}_매출액")),
        "roas": clean_number(row.get(f"{date}_ROAS")),
    }


def transform_meta_ads_sheet(df: pd.DataFrame, channel: str = "facebook") -> pd.DataFrame:
    records = []
    dates = extract_dates(df.columns)

    for _, row in df.iterrows():
        if is_summary_row(row.get("캠페인")):
            continue
        for date in dates:
            records.append(build_record(row, date, channel))

    mart_df = pd.DataFrame(records)
    if mart_df.empty:
        return mart_df

    mart_df["date"] = pd.to_datetime(mart_df["date"]).dt.date
    mart_df["product"] = mart_df["product"].fillna("").astype(str)
    mart_df["campaign"] = mart_df["campaign"].fillna("").astype(str)
    return mart_df


def build_raw_block_record(
    df: pd.DataFrame,
    spreadsheet_id: str,
    worksheet_gid: int,
    worksheet_name: str,
    table_name: str,
    cell_range: str,
    channel: str,
    header_row_index: int,
) -> dict:
    normalized_df = df.fillna("")
    return {
        "spreadsheet_id": spreadsheet_id,
        "worksheet_gid": worksheet_gid,
        "worksheet_name": worksheet_name,
        "table_name": table_name,
        "cell_range": cell_range,
        "channel": channel,
        "header_row_index": header_row_index,
        "source_columns": list(df.columns),
        "source_rows": normalized_df.astype(str).values.tolist(),
        "extracted_at": datetime.utcnow(),
    }


def transform_meta_ads_dw(
    df: pd.DataFrame,
    spreadsheet_id: str,
    worksheet_gid: int,
    source_table_name: str,
    source_range: str,
    channel: str,
) -> pd.DataFrame:
    dates = extract_dates(df.columns)
    records = []

    for _, row in df.iterrows():
        if is_summary_row(row.get("캠페인")):
            continue

        product_name = str(row.get("상품명") or row.get("광고세트") or row.get("상품") or "").strip()
        campaign_name = str(row.get("캠페인") or "").strip()
        campaign_mapping = str(row.get("캠페인 매칭") or "").strip()
        budget = clean_number(row.get("설정예산"))

        for event_date in dates:
            records.append(
                {
                    "spreadsheet_id": spreadsheet_id,
                    "worksheet_gid": worksheet_gid,
                    "source_table_name": source_table_name,
                    "source_range": source_range,
                    "channel": channel,
                    "event_date": pd.to_datetime(event_date).date(),
                    "product_name": product_name,
                    "campaign_name": campaign_name,
                    "campaign_mapping": campaign_mapping,
                    "budget": budget,
                    "spend": clean_number(row.get(f"{event_date}_지출금액")),
                    "revenue": clean_number(row.get(f"{event_date}_매출액")),
                    "roas": clean_number(row.get(f"{event_date}_ROAS")),
                    "extracted_at": datetime.utcnow(),
                    "loaded_at": datetime.utcnow(),
                }
            )

    return pd.DataFrame(records)
