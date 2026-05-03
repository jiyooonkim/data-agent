CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS dw;

GRANT USAGE ON SCHEMA raw TO data_agent;
GRANT USAGE ON SCHEMA dw TO data_agent;
GRANT SELECT ON ALL TABLES IN SCHEMA raw TO data_agent;
GRANT SELECT ON ALL TABLES IN SCHEMA dw TO data_agent;

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

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE raw.google_sheet_table_blocks TO data_agent;

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

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE dw.meta_ads_daily TO data_agent;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA raw TO data_agent;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA dw TO data_agent;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO data_agent;
ALTER DEFAULT PRIVILEGES IN SCHEMA dw GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO data_agent;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO data_agent;
ALTER DEFAULT PRIVILEGES IN SCHEMA dw GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO data_agent;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE raw.google_sheet_table_blocks_block_id_seq TO data_agent;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE dw.meta_ads_daily_performance_id_seq TO data_agent;
