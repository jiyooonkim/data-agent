import re

import gspread
import pandas as pd

from config.settings import get_settings
from db.postgres import insert_rows


DATE_COLUMN_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})_(.+)$")


def get_gspread_client(credentials_file: str):
    return gspread.service_account(filename=credentials_file)


def get_worksheet(sheet_url: str, worksheet_name: str = ""):
    settings = get_settings()
    client = get_gspread_client(settings.google_credentials_file)
    spreadsheet = client.open_by_url(sheet_url)
    if worksheet_name:
        return spreadsheet.worksheet(worksheet_name)
    return spreadsheet.sheet1


def read_sheet_as_dataframe(sheet_url: str, worksheet_name: str = ""):
    worksheet = get_worksheet(sheet_url=sheet_url, worksheet_name=worksheet_name)
    records = worksheet.get_all_records()
    return pd.DataFrame(records)


def clean_number(x):
    if pd.isna(x):
        return 0
    x = str(x).replace(",", "").replace("%", "")
    return float(x)


def extract_dates(columns):
    dates = set()
    for column in columns:
        match = DATE_COLUMN_PATTERN.match(str(column))
        if match:
            dates.add(match.group(1))
    return sorted(dates)


def transform(df):
    records = []
    dates = extract_dates(df.columns)

    for _, row in df.iterrows():
        campaign = row.get("캠페인")

        if not campaign or "SUMMARY" in str(campaign) or campaign == "총계":
            continue

        for date in dates:
            records.append(
                {
                    "date": date,
                    "channel": "facebook",
                    "product": row.get("상품명"),
                    "campaign": campaign,
                    "spend": clean_number(row.get(f"{date}_지출금액")),
                    "revenue": clean_number(row.get(f"{date}_매출액")),
                    "roas": clean_number(row.get(f"{date}_ROAS")),
                }
            )

    return pd.DataFrame(records)


def load_sheet_to_postgres(sheet_url: str, worksheet_name: str = ""):
    df = read_sheet_as_dataframe(sheet_url=sheet_url, worksheet_name=worksheet_name)
    mart_df = transform(df)
    inserted_count = insert_rows(mart_df)
    return {
        "source_rows": len(df),
        "mart_rows": len(mart_df),
        "inserted_rows": inserted_count,
    }


def run():
    settings = get_settings()
    return load_sheet_to_postgres(
        sheet_url=settings.google_sheet_url,
        worksheet_name=settings.google_worksheet_name,
    )


if __name__ == "__main__":
    print(run())
