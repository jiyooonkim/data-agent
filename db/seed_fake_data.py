from __future__ import annotations

import logging
from pathlib import Path

from db.postgres import execute_sql_file
from db.postgres import run_query


logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
DDL_SQL_PATH = ROOT_DIR / "sql" / "create_google_sheet_dw_tables.sql"
SEED_SQL_PATH = ROOT_DIR / "sql" / "seed_demo_meta_ads_daily.sql"


def seed_demo_data() -> dict:
    logger.info("Ensuring DW tables exist.")
    execute_sql_file(str(DDL_SQL_PATH))

    logger.info("Seeding demo data into PostgreSQL.")
    execute_sql_file(str(SEED_SQL_PATH))

    channel_counts = run_query(
        """
        SELECT channel, COUNT(*)::int AS row_count
        FROM dw.meta_ads_daily
        WHERE spreadsheet_id = 'demo_slack_seed'
        GROUP BY channel
        ORDER BY channel
        """
    )
    total_count = run_query(
        """
        SELECT COUNT(*)::int
        FROM dw.meta_ads_daily
        WHERE spreadsheet_id = 'demo_slack_seed'
        """
    )[0][0]

    summary = {
        "seed_spreadsheet_id": "demo_slack_seed",
        "total_rows": total_count,
        "channel_counts": [{"channel": channel, "row_count": row_count} for channel, row_count in channel_counts],
    }
    logger.info("Demo seed completed: %s", summary)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(seed_demo_data())
