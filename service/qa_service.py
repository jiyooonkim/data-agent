from __future__ import annotations

import re

from db.postgres import run_query_with_columns
from llm.llm_client import generate_sql, repair_sql


FORBIDDEN_SQL_PATTERNS = [
    r"\binsert\b",
    r"\bupdate\b",
    r"\bdelete\b",
    r"\bdrop\b",
    r"\balter\b",
    r"\bcreate\b",
    r"\btruncate\b",
    r"\bgrant\b",
    r"\brevoke\b",
    r"\bcopy\b",
]

QUESTION_CANONICAL_REPLACEMENTS = {
    "구글": "google",
    "Google": "google",
    "페이스북": "facebook",
    "Facebook": "facebook",
}


def normalize_sql(sql_text: str) -> str:
    sql_text = sql_text.strip()
    sql_text = re.sub(r"^```sql\s*", "", sql_text, flags=re.IGNORECASE)
    sql_text = re.sub(r"^```\s*", "", sql_text)
    sql_text = re.sub(r"\s*```$", "", sql_text)
    return sql_text.strip().rstrip(";")


def validate_sql(sql_text: str) -> str:
    normalized = normalize_sql(sql_text)
    lowered = normalized.lower()

    if not lowered.startswith("select"):
        raise ValueError("Only SELECT queries are allowed.")

    if ";" in normalized:
        raise ValueError("Multiple SQL statements are not allowed.")

    for pattern in FORBIDDEN_SQL_PATTERNS:
        if re.search(pattern, lowered):
            raise ValueError("Blocked SQL keyword detected.")

    if "dw.meta_ads_daily" not in lowered:
        raise ValueError("Only dw.meta_ads_daily can be queried.")

    return normalized


def format_rows(columns: list[str], rows: list[tuple], max_rows: int = 20) -> str:
    if not rows:
        return "조회 결과가 없습니다."

    visible_rows = rows[:max_rows]
    header = " | ".join(columns)
    separator = " | ".join("---" for _ in columns)
    body = [" | ".join("" if value is None else str(value) for value in row) for row in visible_rows]
    lines = [header, separator, *body]

    if len(rows) > max_rows:
        lines.append(f"... ({len(rows) - max_rows} more rows)")

    return "\n".join(lines)


def normalize_question(question: str) -> str:
    normalized = question
    for source, target in QUESTION_CANONICAL_REPLACEMENTS.items():
        normalized = normalized.replace(source, target)
    return normalized


def ask(question: str) -> dict:
    normalized_question = normalize_question(question)
    sql_text = generate_sql(normalized_question)
    validated_sql = validate_sql(sql_text)
    try:
        columns, rows = run_query_with_columns(validated_sql)
    except Exception as exc:
        repaired_sql = repair_sql(normalized_question, validated_sql, str(exc))
        validated_sql = validate_sql(repaired_sql)
        columns, rows = run_query_with_columns(validated_sql)

    return {
        "question": question,
        "normalized_question": normalized_question,
        "sql": validated_sql,
        "columns": columns,
        "rows": rows,
        "answer_text": format_rows(columns, rows),
    }
