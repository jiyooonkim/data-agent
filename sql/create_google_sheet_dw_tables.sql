CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS dw;
CREATE SCHEMA IF NOT EXISTS docs;

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

CREATE TABLE IF NOT EXISTS docs.document_chunks (
    chunk_id bigserial PRIMARY KEY,
    page_id text NOT NULL REFERENCES docs.notion_pages(page_id) ON DELETE CASCADE,
    chunk_order integer NOT NULL,
    chunk_text text NOT NULL,
    embedding vector NOT NULL,
    indexed_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS document_chunks_page_id_idx
    ON docs.document_chunks (page_id);
