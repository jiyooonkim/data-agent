Google Sheet 기반 광고 데이터를
자연어 질의 → SQL → 결과 응답 형태로 제공

대상: 마케팅/운영 30명


전체 아키텍처
Google Sheet
    ↓
Python ingestion (cron or Airflow)
    ↓
Postgres (mart_ads_daily)
    ↓
LLM (Groq 무료)
    ↓
SQL 생성
    ↓
DB 실행
    ↓
Slack or CLI 응답