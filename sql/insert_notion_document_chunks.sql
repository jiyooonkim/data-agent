INSERT INTO docs.document_chunks (
    page_id,
    chunk_order,
    chunk_text,
    embedding,
    indexed_at
)
VALUES %s
