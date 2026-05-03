CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS dw;

GRANT USAGE ON SCHEMA raw TO data_agent;
GRANT USAGE ON SCHEMA dw TO data_agent;

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
    campaign_mapping text,
    budget numeric(18, 2) NOT NULL DEFAULT 0,
    spend numeric(18, 2) NOT NULL DEFAULT 0,
    revenue numeric(18, 2) NOT NULL DEFAULT 0,
    roas numeric(18, 2) NOT NULL DEFAULT 0,
    extracted_at timestamptz NOT NULL DEFAULT now(),
    loaded_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (spreadsheet_id, worksheet_gid, source_table_name, channel, event_date, product_name, campaign_name)
);

CREATE INDEX IF NOT EXISTS meta_ads_daily_channel_date_idx
    ON dw.meta_ads_daily (channel, event_date);

CREATE INDEX IF NOT EXISTS meta_ads_daily_product_idx
    ON dw.meta_ads_daily (product_name);

CREATE INDEX IF NOT EXISTS meta_ads_daily_campaign_idx
    ON dw.meta_ads_daily (campaign_name);

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE dw.meta_ads_daily TO data_agent;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE raw.google_sheet_table_blocks_block_id_seq TO data_agent;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE dw.meta_ads_daily_performance_id_seq TO data_agent;
