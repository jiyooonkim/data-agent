from __future__ import annotations

from collections.abc import Iterable
import logging

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

from config.settings import get_settings
from db.table_specs import META_ADS_DAILY_INSERT_COLUMNS


logger = logging.getLogger(__name__)


def get_connection():
    settings = get_settings()
    logger.info("Opening PostgreSQL connection.")
    return psycopg2.connect(settings.database_url)


def resolve_table_name(table_name: str):
    if "." in table_name:
        return table_name.split(".", 1)
    return "public", table_name


def run_query(sql_text: str, params: Iterable | None = None):
    logger.info("Running query.")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_text, params or ())
            return cur.fetchall()


def ensure_table_exists(table_name: str, ddl_columns: list[str], primary_key_columns: list[str]):
    schema_name, table_only = resolve_table_name(table_name)
    logger.info("Ensuring table exists: %s.%s", schema_name, table_only)
    create_schema_sql = sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema_name))
    create_table_sql = sql.SQL(
        """
        CREATE TABLE IF NOT EXISTS {} (
            {},
            PRIMARY KEY ({})
        )
        """
    ).format(
        sql.Identifier(schema_name, table_only),
        sql.SQL(", ").join(sql.SQL(column) for column in ddl_columns),
        sql.SQL(", ").join(sql.Identifier(column) for column in primary_key_columns),
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_schema_sql)
            cur.execute(create_table_sql)
        conn.commit()
    logger.info("Table is ready: %s.%s", schema_name, table_only)


def insert_rows(df, table_name: str | None = None, columns: list[str] | None = None):
    if df.empty:
        logger.info("No rows to insert.")
        return 0

    settings = get_settings()
    schema_name, table_only = resolve_table_name(table_name or settings.mart_table_name)
    insert_columns = columns or META_ADS_DAILY_INSERT_COLUMNS
    values = [tuple(row[column] for column in insert_columns) for _, row in df[insert_columns].iterrows()]
    logger.info("Inserting rows into %s.%s: %s rows", schema_name, table_only, len(values))

    query = sql.SQL(
        """
        INSERT INTO {} ({})
        VALUES %s
        ON CONFLICT (date, channel, product, campaign) DO UPDATE
        SET spend = EXCLUDED.spend,
            revenue = EXCLUDED.revenue,
            roas = EXCLUDED.roas
        """
    ).format(
        sql.Identifier(schema_name, table_only),
        sql.SQL(", ").join(sql.Identifier(column) for column in insert_columns),
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(cur, query, values, page_size=500)
        conn.commit()

    logger.info("Insert completed for %s.%s: %s rows", schema_name, table_only, len(values))
    return len(values)
