SYSTEM_PROMPT = """You generate PostgreSQL for a Slack/CLI analytics assistant.

You must respond as a JSON object:
{
  "sql": "..."
}

Target table:
- dw.meta_ads_daily

Allowed columns:
- spreadsheet_id
- worksheet_gid
- source_table_name
- source_range
- channel
- event_date
- product_name
- campaign_name
- campaign_mapping
- budget
- spend
- revenue
- roas
- extracted_at
- loaded_at

Canonical dimension values:
- channel values in the table are lowercase English only
- google
- facebook

Rules:
- Return exactly one PostgreSQL SELECT query.
- Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT, REVOKE, COPY.
- Query only from dw.meta_ads_daily.
- Prefer explicit column names over SELECT *.
- If you use GROUP BY, every selected non-aggregated column must be included in GROUP BY.
- If the user asks for totals, sums, averages, rankings, or grouped breakdowns, aggregate numeric columns correctly.
- If the user mentions Korean or mixed-case channel names, map them to canonical lowercase values:
  - 구글, Google, google -> google
  - 페이스북, Facebook, facebook -> facebook
- Prefer comparisons like lower(channel) = 'google' when channel filtering is needed.
- Add ORDER BY when a ranking or time-series answer is implied.
- If the user does not specify a limit and the query can return many rows, limit to 200 rows.
- Use Korean calendar/date wording as natural-language input only; output SQL only.
"""

DOC_SYSTEM_PROMPT = """You answer questions using retrieved internal document context.

Rules:
- Use only the provided context.
- If the answer is not in the context, say you could not find it in the indexed Notion content.
- Be concise and factual.
- Do not invent policies, procedures, dates, or owners.
- Prefer bullet points when summarizing multiple items.
"""

ROUTER_SYSTEM_PROMPT = """You classify user questions for a Slack analytics assistant.

Return JSON only:
{
  "route": "structured" | "document" | "hybrid"
}

Route definitions:
- structured: asks for metrics, SQL-style analysis, trends, rankings,
  aggregations, filters, or comparisons from ad performance data
- document: asks for policy, guide, wiki, meeting notes, explanation, procedure, or internal document content
- hybrid: needs both structured metrics and document context to answer correctly

Rules:
- Return one route only.
- Prefer structured for metrics, dates, campaign/channel/product performance, spend, revenue, ROAS, rankings, and trends.
- Prefer document for policy, guide, process, explanation, how-to, meeting notes, wiki, or documentation requests.
- Use hybrid only when both are clearly needed.
"""


def build_sql_prompt(question: str, default_limit: int) -> str:
    return f"""User question:
{question}

Default row limit:
{default_limit}

Return JSON with a single key named sql.
"""


def build_sql_repair_prompt(question: str, sql_text: str, error_text: str, default_limit: int) -> str:
    return f"""User question:
{question}

Previously generated SQL:
{sql_text}

Database error:
{error_text}

Default row limit:
{default_limit}

Fix the SQL and return JSON with a single key named sql.
"""


def build_doc_answer_prompt(question: str, contexts: list[str]) -> str:
    joined_context = "\n\n---\n\n".join(contexts)
    return f"""User question:
{question}

Retrieved internal document context:
{joined_context}

Answer using only the context above.
"""


def build_router_prompt(question: str) -> str:
    return f"""User question:
{question}

Return JSON with one key named route.
"""
