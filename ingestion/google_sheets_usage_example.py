from ingestion.google_sheets import parse_sheet_source, read_sheet_as_dataframe


SHEET_URL = "https://docs.google.com/spreadsheets/d/1nr9X5IgwNPG-jn0xM-P5X7dH91B-rptcYiG4xJ5AsaE/edit?pli=1&gid=0#gid=0"


def main():
    source = parse_sheet_source(SHEET_URL)
    df = read_sheet_as_dataframe(
        sheet_url=SHEET_URL,
        worksheet_gid=source.worksheet_gid,
    )

    print("spreadsheet_url:", source.spreadsheet_url)
    print("worksheet_gid:", source.worksheet_gid)
    print("rows:", len(df))
    print("columns:", list(df.columns))
    print(df.head())


if __name__ == "__main__":
    main()
