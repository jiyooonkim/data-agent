from __future__ import annotations

"""
Usage
-----
구글 시트를 DataFrame으로 읽을 때는 `read_sheet_as_dataframe()`를 사용합니다.

기본 사용:

    from ingestion.google_sheets import read_sheet_as_dataframe

    df = read_sheet_as_dataframe(
        "https://docs.google.com/spreadsheets/d/1nr9X5IgwNPG-jn0xM-P5X7dH91B-rptcYiG4xJ5AsaE/edit?usp=sharing"
    )

gid를 명시해서 특정 워크시트 읽기:

    from ingestion.google_sheets import read_sheet_as_dataframe

    df = read_sheet_as_dataframe(
        sheet_url="https://docs.google.com/spreadsheets/d/1nr9X5IgwNPG-jn0xM-P5X7dH91B-rptcYiG4xJ5AsaE/edit?usp=sharing",
        worksheet_gid=0,
    )

예시:

    from ingestion.google_sheets import parse_sheet_source, read_sheet_as_dataframe

    sheet_url = "https://docs.google.com/spreadsheets/d/1nr9X5IgwNPG-jn0xM-P5X7dH91B-rptcYiG4xJ5AsaE/edit?usp=sharing"
    source = parse_sheet_source(sheet_url)
    df = read_sheet_as_dataframe(sheet_url=sheet_url, worksheet_gid=source.worksheet_gid)

    print(df.head())

공개 시트면 CSV export로 읽고, 비공개 시트면 `credentials.json`을 사용한 gspread로 fallback 합니다.
"""

from dataclasses import dataclass
from io import StringIO
from urllib.parse import parse_qs, urlparse

import gspread
import pandas as pd
import requests

from config.settings import get_settings


EMPTY_HEADER_PREFIX = "unnamed"
HTML_MARKER = "<!DOCTYPE html>"


@dataclass(frozen=True)
class SheetSource:
    spreadsheet_url: str
    worksheet_gid: int | None


def parse_sheet_source(sheet_url: str) -> SheetSource:
    parsed = urlparse(sheet_url)
    query = parse_qs(parsed.query)
    fragment_query = parse_qs(parsed.fragment)
    gid_value = query.get("gid", [None])[0] or fragment_query.get("gid", [None])[0]
    gid = int(str(gid_value)) if gid_value and str(gid_value).isdigit() else None
    return SheetSource(
        spreadsheet_url=f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
        worksheet_gid=gid,
    )


def get_gspread_client():
    settings = get_settings()
    return gspread.service_account(filename=settings.google_credentials_file)


def fetch_public_csv(sheet_url: str, worksheet_gid: int) -> pd.DataFrame | None:
    response = requests.get(f"{sheet_url}/export?format=csv&gid={worksheet_gid}", timeout=30)
    if response.status_code != 200 or HTML_MARKER in response.text:
        return None
    return pd.read_csv(StringIO(response.text))


def get_worksheet(sheet_url: str, worksheet_name: str = "", worksheet_gid: int | None = None):
    spreadsheet = get_gspread_client().open_by_url(sheet_url)
    if worksheet_name:
        return spreadsheet.worksheet(worksheet_name)
    if worksheet_gid is not None:
        return spreadsheet.get_worksheet_by_id(worksheet_gid)
    return spreadsheet.sheet1


def build_dataframe_from_values(values: list[list[str]]) -> pd.DataFrame:
    rows = [[str(cell).strip() for cell in row] for row in values]
    rows = [row for row in rows if any(cell for cell in row)]
    if not rows:
        return pd.DataFrame()

    header = [column or f"{EMPTY_HEADER_PREFIX}_{index}" for index, column in enumerate(rows[0], start=1)]
    body = [(row + [""] * len(header))[: len(header)] for row in rows[1:]]
    return pd.DataFrame(body, columns=header)


def read_sheet_as_dataframe(sheet_url: str, worksheet_name: str = "", worksheet_gid: int | None = None):
    source = parse_sheet_source(sheet_url)
    resolved_gid = worksheet_gid if worksheet_gid is not None else source.worksheet_gid

    if resolved_gid is not None:
        public_df = fetch_public_csv(source.spreadsheet_url, resolved_gid)
        if public_df is not None:
            return public_df

    worksheet = get_worksheet(
        sheet_url=source.spreadsheet_url,
        worksheet_name=worksheet_name,
        worksheet_gid=resolved_gid,
    )
    return build_dataframe_from_values(worksheet.get_all_values())
