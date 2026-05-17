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
    indexed_at = now();
