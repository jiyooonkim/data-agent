from __future__ import annotations

from collections.abc import Iterable

import psycopg2
from psycopg2.extras import execute_values

from config.settings import get_settings


def get_connection():
    settings = get_settings()
    return psycopg2.connect(settings.database_url)


def run_query(sql: str, params: Iterable | None = None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()


def insert_rows(df, table_name: str | None = None):
    if df.empty:
        return 0

    settings = get_settings()
    target_table = table_name or settings.mart_table_name
    columns = ["date", "channel", "product", "campaign", "spend", "revenue", "roas"]
    values = [tuple(row[column] for column in columns) for _, row in df[columns].iterrows()]

    query = f"""
        INSERT INTO {target_table}
        (date, channel, product, campaign, spend, revenue, roas)
        VALUES %s
        ON CONFLICT (date, channel, product, campaign) DO UPDATE
        SET spend = EXCLUDED.spend,
            revenue = EXCLUDED.revenue,
            roas = EXCLUDED.roas
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(cur, query, values, page_size=500)
        conn.commit()

    return len(values)
