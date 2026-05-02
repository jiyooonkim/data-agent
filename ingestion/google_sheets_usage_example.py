from ingestion.google_sheets import (
    parse_sheet_source,
    read_sheet_as_dataframe,
    read_sheet_range_as_dataframe,
)


SHEET_URL = "https://docs.google.com/spreadsheets/d/1nr9X5IgwNPG-jn0xM-P5X7dH91B-rptcYiG4xJ5AsaE/edit?pli=1&gid=0#gid=0"


def main():
    source = parse_sheet_source(SHEET_URL)
    full_df = read_sheet_as_dataframe(sheet_url=SHEET_URL, worksheet_gid=source.worksheet_gid)
    facebook_df = read_sheet_range_as_dataframe(
        sheet_url=SHEET_URL,
        worksheet_gid=source.worksheet_gid,
        cell_range="D5:M32",
        header_row_index=1,
    )
    google_df = read_sheet_range_as_dataframe(
        sheet_url=SHEET_URL,
        worksheet_gid=source.worksheet_gid,
        cell_range="O4:X25",
        header_row_index=2,
    )

    # print("spreadsheet_url:", source.spreadsheet_url)
    # print("worksheet_gid:", source.worksheet_gid)

    print("facebook_rows:", len(facebook_df))
    print("facebook_columns:", list(facebook_df.columns))
    # print(facebook_df.head())
    print("google_rows:", len(google_df))
    print("google_columns:", list(google_df.columns))
    print(google_df.head())


if __name__ == "__main__":
    main()
