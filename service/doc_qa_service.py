from __future__ import annotations

from config.settings import get_settings
from db.postgres import run_query_with_columns
from llm.llm_client import embed_texts, generate_doc_answer


def search_document_chunks(question: str, limit: int | None = None):
    settings = get_settings()
    embedding = embed_texts([question])[0]
    vector_literal = "[" + ",".join(f"{value:.12f}" for value in embedding) + "]"
    sql_text = """
        SELECT
            p.page_id,
            p.title,
            c.chunk_order,
            c.chunk_text,
            1 - (c.embedding <=> %s::vector) AS similarity
        FROM docs.document_chunks c
        JOIN docs.notion_pages p
            ON p.page_id = c.page_id
        ORDER BY c.embedding <=> %s::vector
        LIMIT %s
    """
    return run_query_with_columns(
        sql_text,
        (vector_literal, vector_literal, limit or settings.doc_answer_chunk_limit),
    )


def ask_doc(question: str) -> dict:
    columns, rows = search_document_chunks(question)
    contexts = [row[3] for row in rows]
    answer_text = generate_doc_answer(question, contexts) if contexts else "No indexed Notion content was found."

    return {
        "question": question,
        "columns": columns,
        "rows": rows,
        "answer_text": answer_text,
    }
