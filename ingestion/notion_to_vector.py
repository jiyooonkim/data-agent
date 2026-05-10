from __future__ import annotations

import logging
from pathlib import Path

from psycopg2.extras import execute_values

from config.settings import get_settings
from db.postgres import execute_sql_file, get_connection
from ingestion.notion_client import NotionPageDocument, fetch_notion_documents
from llm.llm_client import embed_texts


logger = logging.getLogger(__name__)

DDL_SQL_PATH = Path(__file__).resolve().parent.parent / "sql" / "create_google_sheet_dw_tables.sql"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list[str]:
    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not normalized:
        return []

    paragraphs = [part.strip() for part in normalized.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)

        if len(paragraph) <= chunk_size:
            current = paragraph
            continue

        start = 0
        while start < len(paragraph):
            end = start + chunk_size
            piece = paragraph[start:end].strip()
            if piece:
                chunks.append(piece)
            if end >= len(paragraph):
                current = ""
                break
            start = max(end - chunk_overlap, start + 1)
        else:
            current = ""

    if current:
        chunks.append(current)

    return chunks


def to_vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(f"{value:.12f}" for value in embedding) + "]"


def upsert_notion_page(document: NotionPageDocument) -> None:
    query = """
        INSERT INTO docs.notion_pages (
            page_id,
            title,
            url,
            last_edited_time,
            markdown_content,
            indexed_at
        )
        VALUES (%s, %s, %s, %s, %s, now())
        ON CONFLICT (page_id) DO UPDATE
        SET title = EXCLUDED.title,
            url = EXCLUDED.url,
            last_edited_time = EXCLUDED.last_edited_time,
            markdown_content = EXCLUDED.markdown_content,
            indexed_at = now()
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    document.page_id,
                    document.title,
                    document.url,
                    document.last_edited_time,
                    document.markdown_content,
                ),
            )
        conn.commit()


def replace_document_chunks(page_id: str, chunks: list[str], embeddings: list[list[float]]) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM docs.document_chunks WHERE page_id = %s", (page_id,))
            if chunks:
                values = [
                    (
                        page_id,
                        index,
                        chunk_text,
                        to_vector_literal(embedding),
                    )
                    for index, (chunk_text, embedding) in enumerate(zip(chunks, embeddings), start=1)
                ]
                execute_values(
                    cur,
                    """
                    INSERT INTO docs.document_chunks (
                        page_id,
                        chunk_order,
                        chunk_text,
                        embedding,
                        indexed_at
                    )
                    VALUES %s
                    """,
                    values,
                    template="(%s, %s, %s, %s::vector, now())",
                    page_size=200,
                )
        conn.commit()

    return len(chunks)


def ingest_notion_target(target_id: str) -> dict:
    documents = fetch_notion_documents(target_id)
    document_summaries = []

    for document in documents:
        chunks = chunk_text(document.markdown_content)
        embeddings = embed_texts(chunks) if chunks else []

        upsert_notion_page(document)
        chunk_count = replace_document_chunks(document.page_id, chunks, embeddings)

        summary = {
            "page_id": document.page_id,
            "title": document.title,
            "chunk_count": chunk_count,
        }
        logger.info("Indexed Notion document: %s", summary)
        document_summaries.append(summary)

    return {
        "target_id": target_id,
        "document_count": len(document_summaries),
        "documents": document_summaries,
    }


def ingest_notion_to_vector() -> dict:
    settings = get_settings()
    if not settings.notion_page_ids:
        raise ValueError("NOTION_PAGE_IDS is not configured.")

    execute_sql_file(str(DDL_SQL_PATH))

    target_summaries = [ingest_notion_target(page_id) for page_id in settings.notion_page_ids]
    return {
        "target_count": len(target_summaries),
        "targets": target_summaries,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(ingest_notion_to_vector())
