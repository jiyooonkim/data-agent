CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS dw;
CREATE SCHEMA IF NOT EXISTS docs;

COMMENT ON SCHEMA raw IS 'Raw ingestion layer for source table blocks loaded from Google Sheets.';
COMMENT ON SCHEMA dw IS 'Analytics warehouse layer for normalized advertising performance facts.';
COMMENT ON SCHEMA docs IS 'Document retrieval layer for Notion pages, chunks, and vector embeddings.';

CREATE TABLE IF NOT EXISTS raw.google_sheet_table_blocks (
    block_id bigserial PRIMARY KEY,
    spreadsheet_id text NOT NULL,
    worksheet_gid integer NOT NULL,
    worksheet_name text,
    table_name text NOT NULL,
    cell_range text NOT NULL,
    channel text NOT NULL,
    header_row_index integer NOT NULL DEFAULT 0,
    source_columns jsonb NOT NULL DEFAULT '[]'::jsonb,
    source_rows jsonb NOT NULL DEFAULT '[]'::jsonb,
    extracted_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE raw.google_sheet_table_blocks IS 'Raw table-block snapshots extracted from Google Sheets before normalization.';
COMMENT ON COLUMN raw.google_sheet_table_blocks.block_id IS 'Surrogate primary key for each extracted table block.';
COMMENT ON COLUMN raw.google_sheet_table_blocks.spreadsheet_id IS 'Google Spreadsheet identifier.';
COMMENT ON COLUMN raw.google_sheet_table_blocks.worksheet_gid IS 'Google worksheet gid within the spreadsheet.';
COMMENT ON COLUMN raw.google_sheet_table_blocks.worksheet_name IS 'Worksheet name when available.';
COMMENT ON COLUMN raw.google_sheet_table_blocks.table_name IS 'Logical table name assigned to the extracted range.';
COMMENT ON COLUMN raw.google_sheet_table_blocks.cell_range IS 'A1 notation range used for extraction.';
COMMENT ON COLUMN raw.google_sheet_table_blocks.channel IS 'Normalized marketing channel inferred for the table block.';
COMMENT ON COLUMN raw.google_sheet_table_blocks.header_row_index IS 'Zero-based header row offset inside the extracted range.';
COMMENT ON COLUMN raw.google_sheet_table_blocks.source_columns IS 'Original column names captured from the source block.';
COMMENT ON COLUMN raw.google_sheet_table_blocks.source_rows IS 'Original row values captured from the source block.';
COMMENT ON COLUMN raw.google_sheet_table_blocks.extracted_at IS 'Timestamp when the source block was extracted.';

CREATE INDEX IF NOT EXISTS google_sheet_table_blocks_sheet_idx
    ON raw.google_sheet_table_blocks (spreadsheet_id, worksheet_gid, table_name);

CREATE TABLE IF NOT EXISTS dw.meta_ads_daily (
    performance_id bigserial PRIMARY KEY,
    spreadsheet_id text NOT NULL,
    worksheet_gid integer NOT NULL,
    source_table_name text NOT NULL,
    source_range text NOT NULL,
    channel text NOT NULL,
    event_date date NOT NULL,
    product_name text NOT NULL,
    campaign_name text NOT NULL,
    campaign_mapping text NOT NULL DEFAULT '',
    budget numeric(18, 2) NOT NULL DEFAULT 0,
    spend numeric(18, 2) NOT NULL DEFAULT 0,
    revenue numeric(18, 2) NOT NULL DEFAULT 0,
    roas numeric(18, 2) NOT NULL DEFAULT 0,
    extracted_at timestamptz NOT NULL DEFAULT now(),
    loaded_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE dw.meta_ads_daily IS 'Normalized daily advertising performance fact table used for structured analytics QA.';
COMMENT ON COLUMN dw.meta_ads_daily.performance_id IS 'Surrogate primary key for each normalized performance row.';
COMMENT ON COLUMN dw.meta_ads_daily.spreadsheet_id IS 'Source Google Spreadsheet identifier.';
COMMENT ON COLUMN dw.meta_ads_daily.worksheet_gid IS 'Source worksheet gid within the spreadsheet.';
COMMENT ON COLUMN dw.meta_ads_daily.source_table_name IS 'Logical source table name derived from the sheet block.';
COMMENT ON COLUMN dw.meta_ads_daily.source_range IS 'Source A1 range used to build the performance row.';
COMMENT ON COLUMN dw.meta_ads_daily.channel IS 'Canonical marketing channel value.';
COMMENT ON COLUMN dw.meta_ads_daily.event_date IS 'Performance date represented by the row.';
COMMENT ON COLUMN dw.meta_ads_daily.product_name IS 'Product or SKU name from the source sheet.';
COMMENT ON COLUMN dw.meta_ads_daily.campaign_name IS 'Campaign name from the source sheet.';
COMMENT ON COLUMN dw.meta_ads_daily.campaign_mapping IS 'Optional normalized campaign mapping value.';
COMMENT ON COLUMN dw.meta_ads_daily.budget IS 'Configured campaign budget amount.';
COMMENT ON COLUMN dw.meta_ads_daily.spend IS 'Advertising spend amount.';
COMMENT ON COLUMN dw.meta_ads_daily.revenue IS 'Attributed revenue amount.';
COMMENT ON COLUMN dw.meta_ads_daily.roas IS 'Return on ad spend metric.';
COMMENT ON COLUMN dw.meta_ads_daily.extracted_at IS 'Timestamp when the source data was extracted.';
COMMENT ON COLUMN dw.meta_ads_daily.loaded_at IS 'Timestamp when the normalized row was loaded into the warehouse.';

ALTER TABLE dw.meta_ads_daily
    ALTER COLUMN campaign_mapping SET DEFAULT '';

UPDATE dw.meta_ads_daily
SET campaign_mapping = ''
WHERE campaign_mapping IS NULL;

ALTER TABLE dw.meta_ads_daily
    ALTER COLUMN campaign_mapping SET NOT NULL;

DO
$$
DECLARE
    unique_constraint_name text;
BEGIN
    SELECT con.conname
    INTO unique_constraint_name
    FROM pg_constraint con
    JOIN pg_class rel
        ON rel.oid = con.conrelid
    JOIN pg_namespace nsp
        ON nsp.oid = rel.relnamespace
    WHERE nsp.nspname = 'dw'
      AND rel.relname = 'meta_ads_daily'
      AND con.contype = 'u'
    LIMIT 1;

    IF unique_constraint_name IS NOT NULL THEN
        EXECUTE format(
            'ALTER TABLE dw.meta_ads_daily DROP CONSTRAINT %I',
            unique_constraint_name
        );
    END IF;
END
$$;

DO
$$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint con
        JOIN pg_class rel
            ON rel.oid = con.conrelid
        JOIN pg_namespace nsp
            ON nsp.oid = rel.relnamespace
        WHERE nsp.nspname = 'dw'
          AND rel.relname = 'meta_ads_daily'
          AND con.conname = 'meta_ads_daily_unique_key'
    ) THEN
        ALTER TABLE dw.meta_ads_daily
            DROP CONSTRAINT meta_ads_daily_unique_key;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class cls
        JOIN pg_namespace nsp
            ON nsp.oid = cls.relnamespace
        WHERE nsp.nspname = 'dw'
          AND cls.relname = 'meta_ads_daily_unique_key'
          AND cls.relkind = 'i'
    ) THEN
        DROP INDEX dw.meta_ads_daily_unique_key;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint con
        JOIN pg_class rel
            ON rel.oid = con.conrelid
        JOIN pg_namespace nsp
            ON nsp.oid = rel.relnamespace
        WHERE nsp.nspname = 'dw'
          AND rel.relname = 'meta_ads_daily'
          AND con.conname = 'meta_ads_daily_unique_key'
    ) THEN
        ALTER TABLE dw.meta_ads_daily
            ADD CONSTRAINT meta_ads_daily_unique_key
            UNIQUE (
                spreadsheet_id,
                worksheet_gid,
                source_table_name,
                channel,
                event_date,
                product_name,
                campaign_name,
                campaign_mapping
            );
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS meta_ads_daily_channel_date_idx
    ON dw.meta_ads_daily (channel, event_date);

CREATE INDEX IF NOT EXISTS meta_ads_daily_product_idx
    ON dw.meta_ads_daily (product_name);

CREATE INDEX IF NOT EXISTS meta_ads_daily_campaign_idx
    ON dw.meta_ads_daily (campaign_name);

CREATE TABLE IF NOT EXISTS docs.notion_pages (
    page_id text PRIMARY KEY,
    title text NOT NULL,
    url text NOT NULL,
    last_edited_time text,
    markdown_content text NOT NULL,
    indexed_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE docs.notion_pages IS 'Indexed Notion page metadata and flattened markdown-like page content.';
COMMENT ON COLUMN docs.notion_pages.page_id IS 'Notion page identifier.';
COMMENT ON COLUMN docs.notion_pages.title IS 'Notion page title.';
COMMENT ON COLUMN docs.notion_pages.url IS 'Original Notion page URL.';
COMMENT ON COLUMN docs.notion_pages.last_edited_time IS 'Last edited timestamp returned by Notion API.';
COMMENT ON COLUMN docs.notion_pages.markdown_content IS 'Flattened page content converted from Notion blocks into markdown-like text.';
COMMENT ON COLUMN docs.notion_pages.indexed_at IS 'Timestamp when the page was indexed into the local document store.';

CREATE TABLE IF NOT EXISTS docs.document_chunks (
    chunk_id bigserial PRIMARY KEY,
    page_id text NOT NULL REFERENCES docs.notion_pages(page_id) ON DELETE CASCADE,
    chunk_order integer NOT NULL,
    chunk_text text NOT NULL,
    embedding vector NOT NULL,
    indexed_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE docs.document_chunks IS 'Chunked Notion document segments with pgvector embeddings for semantic retrieval.';
COMMENT ON COLUMN docs.document_chunks.chunk_id IS 'Surrogate primary key for each indexed chunk.';
COMMENT ON COLUMN docs.document_chunks.page_id IS 'Parent Notion page identifier.';
COMMENT ON COLUMN docs.document_chunks.chunk_order IS 'Chunk order within the parent page.';
COMMENT ON COLUMN docs.document_chunks.chunk_text IS 'Chunk text stored for retrieval and answer generation.';
COMMENT ON COLUMN docs.document_chunks.embedding IS 'pgvector embedding for semantic similarity search.';
COMMENT ON COLUMN docs.document_chunks.indexed_at IS 'Timestamp when the chunk embedding was indexed.';

CREATE INDEX IF NOT EXISTS document_chunks_page_id_idx
    ON docs.document_chunks (page_id);
