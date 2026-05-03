 Raw block insert target
 INSERT INTO raw.google_sheet_table_blocks
 (spreadsheet_id, worksheet_gid, worksheet_name, table_name, cell_range, channel, header_row_index, source_columns, source_rows, extracted_at)
 VALUES (...);

 DW upsert target
 INSERT INTO dw.meta_ads_daily
 (spreadsheet_id, worksheet_gid, source_table_name, source_range, channel, event_date, product_name, campaign_name, campaign_mapping, budget, spend, revenue, roas, extracted_at, loaded_at)
 VALUES (...)
 ON CONFLICT (spreadsheet_id, worksheet_gid, source_table_name, channel, event_date, product_name, campaign_name)
 DO UPDATE
 SET campaign_mapping = EXCLUDED.campaign_mapping,
     budget = EXCLUDED.budget,
     spend = EXCLUDED.spend,
     revenue = EXCLUDED.revenue,
     roas = EXCLUDED.roas,
     extracted_at = EXCLUDED.extracted_at,
     loaded_at = EXCLUDED.loaded_at;
