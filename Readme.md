# data-agent

Google Sheets 데이터를 읽어 PostgreSQL DW에 적재하고, 이후 사내 질의응답용 데이터 소스로 쓰기 위한 프로젝트입니다. 현재 실행 기준은 Airflow 3.2.0 입니다.

## 목적

- Google Sheets 범위 데이터를 표 단위로 읽기
- 원본 블록을 `raw` 스키마에 저장
- 정규화한 성과 데이터를 `dw` 스키마에 upsert
- Airflow DAG로 주기 실행

## 전체 아키텍처

```text
Google Sheet
    ↓
Python ingestion (Apache Airflow 3.2.0)
    ↓
Postgres (dw.meta_ads_daily)
    ↓
LLM (Groq)
    ↓
SQL 생성
    ↓
DB 실행
    ↓
Slack or CLI 응답
```

### 단계별 설명

1. `Google Sheet`
- 마케팅 성과 데이터를 운영자가 직접 관리하는 입력 소스입니다.
- 채널별 표 범위를 읽어 원본 블록과 정규화 데이터로 나눠 적재합니다.

2. `Python ingestion (Apache Airflow 3.2.0)`
- Airflow는 배치 오케스트레이션 전용입니다.
- Google Sheet 읽기, 전처리, DW 적재, 적재 검증을 스케줄 기반으로 실행합니다.
- 실시간 챗봇 처리 용도는 아닙니다.

3. `Postgres (dw.meta_ads_daily)`
- 챗봇이 자연어 질문을 SQL로 바꿔 바로 조회해야 하므로, 관계형 질의에 강한 저장소가 필요합니다.
- PostgreSQL을 선택한 이유:
  - SQL 집계, 필터, 정렬, 날짜 조건 처리에 강함
  - 운영 난이도가 낮고 Docker 로컬 개발이 쉬움
  - Airflow 및 Python 생태계와 연결이 단순함
  - Slack 챗봇의 질의응답 소스로 바로 쓰기 좋음
- 현재 질문 응답 대상 테이블은 `dw.meta_ads_daily` 입니다.

4. `LLM (Groq)`
- 사용자 질문을 받아 조회용 SQL을 생성합니다.
- 현재는 Groq의 OpenAI-compatible API를 사용합니다.
- 비용을 낮게 가져가면서 응답 속도를 확보하려는 선택입니다.

5. `SQL 생성`
- LLM이 자연어 질문을 `SELECT` 쿼리로 변환합니다.
- 현재 동작 방식:
  - 대상 테이블을 `dw.meta_ads_daily`로 고정
  - 허용 컬럼만 프롬프트에 명시
  - `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE` 같은 쓰기/DDL 쿼리는 금지
  - 결과가 과도하게 커질 수 있으면 기본 `LIMIT` 적용
  - 생성 후 애플리케이션에서 한 번 더 `SELECT only` 검증

6. `DB 실행`
- 검증을 통과한 SQL만 PostgreSQL에서 실행합니다.
- 결과는 컬럼명과 row 데이터를 함께 받아 Slack/CLI 응답 포맷으로 변환합니다.

7. `Slack or CLI 응답`
- 같은 QA 서비스 로직을 재사용합니다.
- CLI는 로컬 점검용, Slack은 실제 사용자 응답용입니다.
- 즉, `질문 처리 로직`은 하나로 두고 `입력/출력 채널`만 분리하는 구조입니다.

## 주요 구성

- [`ingestion/google_sheets.py`](/Users/jykim/Documents/private/data-agent/ingestion/google_sheets.py:1): 구글 시트 전체/범위 읽기
- [`ingestion/meta_ads_transform.py`](/Users/jykim/Documents/private/data-agent/ingestion/meta_ads_transform.py:1): 원본 블록, DW 적재용 전처리
- [`db/postgres.py`](/Users/jykim/Documents/private/data-agent/db/postgres.py:1): PostgreSQL 연결, SQL 실행, insert/upsert
- [`dags/google_sheet_dw_pipeline.py`](/Users/jykim/Documents/private/data-agent/dags/google_sheet_dw_pipeline.py:1): Airflow DAG
- [`sql/create_google_sheet_dw_tables.sql`](/Users/jykim/Documents/private/data-agent/sql/create_google_sheet_dw_tables.sql:1): `raw`, `dw` 스키마 및 테이블 생성

## 사전 준비

1. `.env` 생성
```bash
cp .env.example .env
```

2. 필요 값 확인
- `DATABASE_URL`
- `DATABASE_ADMIN_URL`
- `GOOGLE_SHEET_URL`
- `GOOGLE_WORKSHEET_NAME` 또는 `GOOGLE_WORKSHEET_GID`
- `GOOGLE_CREDENTIALS_FILE` (비공개 시트인 경우)

3. Python 버전
- 로컬 기준 `3.12`
- Airflow 컨테이너도 `3.12`

## 실행 순서

1. Airflow 및 Postgres 실행
```bash
docker compose up -d --build
```

2. Airflow UI 접속
- `http://localhost:8080`

3. DAG 확인
- DAG ID: `google_sheet_to_dw`

4. DAG 실행
- UI에서 unpause 후 trigger

또는 CLI:

```bash
docker compose exec airflow-api-server airflow dags unpause google_sheet_to_dw
docker compose exec airflow-api-server airflow dags trigger google_sheet_to_dw
```

## 적재 흐름

1. Google Sheet 읽기
2. 표 범위별 DataFrame 생성
3. `raw.google_sheet_table_blocks` 저장
4.  `dw.meta_ads_daily` upsert

## 로컬 확인용 예제

Airflow와 별개로 구조 확인용 예제 파일이 있습니다.

- [`ingestion/google_sheets_usage_example.py`](/Users/jykim/Documents/private/data-agent/ingestion/google_sheets_usage_example.py:1)

예시 실행:

```bash
.venv/bin/python ingestion/google_sheets_usage_example.py
```

## 테이블

- `raw.google_sheet_table_blocks`: 시트 표 블록 원본 저장
- `dw.meta_ads_daily`: 분석/질의용 일별 성과 테이블

## 참고

- 기존 문서는 [`README.legacy.md`](/Users/jykim/Documents/private/data-agent/README.legacy.md:1) 로 보존했습니다.
