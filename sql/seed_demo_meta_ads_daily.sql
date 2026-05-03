DELETE FROM raw.google_sheet_table_blocks
WHERE spreadsheet_id = 'demo_slack_seed';

DELETE FROM dw.meta_ads_daily
WHERE spreadsheet_id = 'demo_slack_seed';

INSERT INTO raw.google_sheet_table_blocks (
    spreadsheet_id,
    worksheet_gid,
    worksheet_name,
    table_name,
    cell_range,
    channel,
    header_row_index,
    source_columns,
    source_rows
)
VALUES
    (
        'demo_slack_seed',
        0,
        'demo_sheet',
        'facebook',
        'D5:M32',
        'facebook',
        1,
        '["상품명", "캠페인", "캠페인 매칭", "설정예산", "2026-05-01_지출금액", "2026-05-01_매출액", "2026-05-01_ROAS"]'::jsonb,
        '[]'::jsonb
    ),
    (
        'demo_slack_seed',
        0,
        'demo_sheet',
        'google',
        'O4:X25',
        'google',
        2,
        '["상품명", "캠페인", "캠페인 매칭", "설정예산", "2026-05-01_지출금액", "2026-05-01_매출액", "2026-05-01_ROAS"]'::jsonb,
        '[]'::jsonb
    );

WITH
channels AS (
    SELECT unnest(ARRAY['facebook', 'google']) AS channel
),
products AS (
    SELECT *
    FROM (
        VALUES
            (1, '아이백패치'),
            (2, '슬림컷'),
            (3, '콜라겐부스터'),
            (4, '수분앰플'),
            (5, '프로틴쉐이크'),
            (6, '이너뷰티'),
            (7, '리프팅크림'),
            (8, '비타민샷'),
            (9, '다이어트티'),
            (10, '시카세럼')
    ) AS t(product_idx, product_name)
),
campaigns AS (
    SELECT *
    FROM (
        VALUES
            (1, '브랜드검색', 'brand_search'),
            (2, '리타겟팅', 'retargeting'),
            (3, '전환최적화', 'conversion'),
            (4, '어드벤티지쇼핑', 'advantage_shopping'),
            (5, '신규고객확장', 'new_user_expansion'),
            (6, '장바구니복귀', 'cart_return'),
            (7, '프로모션집행', 'promotion_push'),
            (8, '영상조회유도', 'video_view'),
            (9, '구매관심사', 'purchase_interest'),
            (10, '브로드타겟', 'broad_target')
    ) AS t(campaign_idx, campaign_name, campaign_mapping)
),
days AS (
    SELECT generate_series(0, 9) AS day_offset
),
seed_rows AS (
    SELECT
        'demo_slack_seed'::text AS spreadsheet_id,
        0::integer AS worksheet_gid,
        ch.channel AS source_table_name,
        'DEMO_SEED'::text AS source_range,
        ch.channel,
        (DATE '2026-05-01' + d.day_offset) AS event_date,
        p.product_name,
        c.campaign_name,
        c.campaign_mapping,
        round((120000 + p.product_idx * 15000 + c.campaign_idx * 9000 + d.day_offset * 2500)::numeric, 2) AS budget,
        round(
            (
                25000
                + p.product_idx * 3200
                + c.campaign_idx * 1900
                + d.day_offset * 1300
                + CASE WHEN ch.channel = 'google' THEN 8500 ELSE 4200 END
            )::numeric,
            2
        ) AS spend
    FROM channels ch
    CROSS JOIN products p
    CROSS JOIN campaigns c
    CROSS JOIN days d
)
INSERT INTO dw.meta_ads_daily (
    spreadsheet_id,
    worksheet_gid,
    source_table_name,
    source_range,
    channel,
    event_date,
    product_name,
    campaign_name,
    campaign_mapping,
    budget,
    spend,
    revenue,
    roas
)
SELECT
    spreadsheet_id,
    worksheet_gid,
    source_table_name,
    source_range,
    channel,
    event_date,
    product_name,
    campaign_name,
    campaign_mapping,
    budget,
    spend,
    round(
        spend
        * (
            CASE
                WHEN channel = 'google' THEN 2.35
                ELSE 1.92
            END
            + (length(product_name) % 4) * 0.08
            + (length(campaign_name) % 5) * 0.04
        ),
        2
    ) AS revenue,
    round(
        (
            round(
                spend
                * (
                    CASE
                        WHEN channel = 'google' THEN 2.35
                        ELSE 1.92
                    END
                    + (length(product_name) % 4) * 0.08
                    + (length(campaign_name) % 5) * 0.04
                ),
                2
            ) / NULLIF(spend, 0)
        ) * 100,
        2
    ) AS roas
FROM seed_rows
ON CONFLICT (
    spreadsheet_id,
    worksheet_gid,
    source_table_name,
    channel,
    event_date,
    product_name,
    campaign_name,
    campaign_mapping
) DO UPDATE
SET budget = EXCLUDED.budget,
    spend = EXCLUDED.spend,
    revenue = EXCLUDED.revenue,
    roas = EXCLUDED.roas,
    loaded_at = now();
