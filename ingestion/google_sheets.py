"""
Usage
-----
구글 시트를 DataFrame으로 읽을 때는 `read_sheet_as_dataframe()`를 사용합니다.
이 프로젝트는 Python 3.12 기준으로 실행합니다.

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

범위를 지정해서 표 단위로 읽기:

    from ingestion.google_sheets import read_sheet_range_as_dataframe

    df = read_sheet_range_as_dataframe(
        sheet_url="https://docs.google.com/spreadsheets/d/1nr9X5IgwNPG-jn0xM-P5X7dH91B-rptcYiG4xJ5AsaE/edit?pli=1&gid=0#gid=0",
        worksheet_gid=0,
        cell_range="D5:M32",
    )

예시:

    from ingestion.google_sheets import parse_sheet_source, read_sheet_as_dataframe

    sheet_url = "https://docs.google.com/spreadsheets/d/1nr9X5IgwNPG-jn0xM-P5X7dH91B-rptcYiG4xJ5AsaE/edit?usp=sharing"
    source = parse_sheet_source(sheet_url)
    df = read_sheet_as_dataframe(sheet_url=sheet_url, worksheet_gid=source.worksheet_gid)

    print(df.head())

공개 시트면 CSV export로 읽고, 비공개 시트면 `credentials.json`을 사용한 gspread로 fallback 합니다.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse

import gspread
import pandas as pd
import requests

from config.settings import get_settings


EMPTY_HEADER_PREFIX = "unnamed"
HTML_MARKER = "<!DOCTYPE html>"
CELL_RANGE_PATTERN = re.compile(r"^([A-Z]+)(\d+):([A-Z]+)(\d+)$")
DATE_TEXT_PATTERN = re.compile(r"^\d{4}\.\s*\d{1,2}\.\s*\d{1,2}$")


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
    spreadsheet_path = parsed.path.split("/edit", 1)[0]
    return SheetSource(
        spreadsheet_url=f"{parsed.scheme}://{parsed.netloc}{spreadsheet_path}",
        worksheet_gid=gid,
    )


def get_gspread_client():
    settings = get_settings()
    credentials_path = Path(settings.google_credentials_file)
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Google service account credentials not found: {settings.google_credentials_file}"
        )
    return gspread.service_account(filename=settings.google_credentials_file)


def fetch_public_csv(sheet_url: str, worksheet_gid: int) -> pd.DataFrame | None:
    response = requests.get(f"{sheet_url}/export?format=csv&gid={worksheet_gid}", timeout=30)
    if response.status_code != 200 or HTML_MARKER in response.text:
        return None
    return pd.read_csv(BytesIO(response.content), encoding="utf-8-sig")


def fetch_public_csv_values(sheet_url: str, worksheet_gid: int) -> list[list[str]] | None:
    response = requests.get(f"{sheet_url}/export?format=csv&gid={worksheet_gid}", timeout=30)
    if response.status_code != 200 or HTML_MARKER in response.text:
        return None
    decoded_text = response.content.decode("utf-8-sig")
    return [row for row in csv.reader(StringIO(decoded_text))]


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


def build_dataframe_from_range(values: list[list[str]], header_row_index: int = 0) -> pd.DataFrame:
    rows = [[str(cell).strip() for cell in row] for row in values]
    rows = [row for row in rows if any(cell for cell in row)]
    if not rows:
        return pd.DataFrame()

    if header_row_index >= len(rows):
        raise ValueError("header_row_index is out of range for the selected cells.")

    header_row = rows[header_row_index]
    header = [column or f"{EMPTY_HEADER_PREFIX}_{index}" for index, column in enumerate(header_row, start=1)]
    body_rows = rows[header_row_index + 1 :]
    body = [(row + [""] * len(header))[: len(header)] for row in body_rows]
    return pd.DataFrame(body, columns=header)


def normalize_date_header(value: str) -> str:
    if not DATE_TEXT_PATTERN.match(value.strip()):
        return value.strip()

    parts = [part.strip() for part in value.split(".") if part.strip()]
    if len(parts) != 3:
        return value.strip()

    year, month, day = parts
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def build_dataframe_from_multirow_range(values: list[list[str]], header_row_indices: list[int]) -> pd.DataFrame:
    rows = [[str(cell).strip() for cell in row] for row in values]
    rows = [row for row in rows if any(cell for cell in row)]
    if not rows:
        return pd.DataFrame()

    if not header_row_indices:
        raise ValueError("header_row_indices must not be empty.")
    if max(header_row_indices) >= len(rows):
        raise ValueError("header_row_indices is out of range for the selected cells.")

    width = max(len(row) for row in rows)
    normalized_rows = [(row + [""] * width)[:width] for row in rows]
    header_rows = [normalized_rows[index] for index in header_row_indices]

    # Forward-fill the first header row so date groups span metric columns.
    first_header = header_rows[0][:]
    current_value = ""
    for index, value in enumerate(first_header):
        if value:
            current_value = normalize_date_header(value)
        elif current_value:
            first_header[index] = current_value

    combined_header = []
    for column_index in range(width):
        parts = []
        for header_row_index, header_row in enumerate(header_rows):
            value = header_row[column_index].strip()
            if header_row_index == 0 and not value:
                value = first_header[column_index].strip()
            value = normalize_date_header(value)
            if value:
                parts.append(value)

        if not parts:
            combined_header.append(f"{EMPTY_HEADER_PREFIX}_{column_index + 1}")
            continue

        if len(parts) >= 2 and DATE_TEXT_PATTERN.match(parts[0].replace("-", ". ").replace("-", ". ")):
            combined_header.append(f"{parts[0]}_{parts[-1]}")
        elif len(parts) >= 2 and re.match(r"^\d{4}-\d{2}-\d{2}$", parts[0]):
            combined_header.append(f"{parts[0]}_{parts[-1]}")
        else:
            combined_header.append(parts[-1] if len(set(parts)) == 1 else "_".join(parts))

    body_start = max(header_row_indices) + 1
    body_rows = normalized_rows[body_start:]
    return pd.DataFrame(body_rows, columns=combined_header)


def column_letter_to_index(column_letters: str) -> int:
    index = 0
    for char in column_letters:
        index = index * 26 + (ord(char.upper()) - ord("A") + 1)
    return index - 1


def slice_values_by_range(values: list[list[str]], cell_range: str) -> list[list[str]]:
    match = CELL_RANGE_PATTERN.match(cell_range.upper())
    if not match:
        raise ValueError(f"Unsupported cell range format: {cell_range}")

    start_col, start_row, end_col, end_row = match.groups()
    start_col_index = column_letter_to_index(start_col)
    end_col_index = column_letter_to_index(end_col)
    start_row_index = int(start_row) - 1
    end_row_index = int(end_row) - 1

    sliced_rows = values[start_row_index : end_row_index + 1]
    return [
        (row + [""] * (end_col_index + 1))[start_col_index : end_col_index + 1]
        for row in sliced_rows
    ]


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


def read_sheet_range_as_dataframe(
    sheet_url: str,
    cell_range: str,
    worksheet_name: str = "",
    worksheet_gid: int | None = None,
    header_row_index: int = 0,
    header_row_indices: list[int] | None = None,
):
    source = parse_sheet_source(sheet_url)
    resolved_gid = worksheet_gid if worksheet_gid is not None else source.worksheet_gid

    if resolved_gid is not None:
        public_values = fetch_public_csv_values(source.spreadsheet_url, resolved_gid)
        if public_values is not None:
            sliced_values = slice_values_by_range(public_values, cell_range)
            if header_row_indices is not None:
                return build_dataframe_from_multirow_range(
                    sliced_values,
                    header_row_indices=header_row_indices,
                )
            return build_dataframe_from_range(
                sliced_values,
                header_row_index=header_row_index,
            )

    worksheet = get_worksheet(
        sheet_url=source.spreadsheet_url,
        worksheet_name=worksheet_name,
        worksheet_gid=resolved_gid,
    )
    range_values = worksheet.get(cell_range)
    if header_row_indices is not None:
        return build_dataframe_from_multirow_range(
            range_values,
            header_row_indices=header_row_indices,
        )
    return build_dataframe_from_range(range_values, header_row_index=header_row_index)
