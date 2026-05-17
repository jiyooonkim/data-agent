# Data-Agent

Google Sheet 기반 광고 데이터를 PostgreSQL DW에 적재하고, Slack/CLI에서 자연어 질의를 SQL로 변환해 답변하는 프로젝트입니다. 현재 배치 적재는 Airflow 3.2.0 기준입니다.

## 목적

- Google Sheet 표 범위 데이터를 읽어 DW에 적재
- 광고 성과 데이터를 `raw`와 `dw` 계층으로 분리 저장
- 자연어 질의 -> SQL -> 결과 응답 구조 제공
- 마케팅/운영 사용자용 Slack 챗봇의 데이터 소스 제공

## 전체 아키텍처

```text
Google Sheet
    ↓
Python ingestion (Apache Airflow 3.2.0)
    ↓
Postgres (logical mart: mart_ads_daily / current table: dw.meta_ads_daily)
    ↓
LLM (Ollama local model)
    ↓
SQL 생성
    ↓
DB 실행
    ↓
Slack or CLI 응답
```

## 구현 요약

1. Google Sheet 표 범위를 읽어 DataFrame으로 정리합니다.
2. 원본 블록은 `raw.google_sheet_table_blocks`에 저장합니다.
3. 정규화된 성과 데이터는 `dw.meta_ads_daily`에 upsert 합니다.
4. `service/qa_service.py`가 자연어 질문을 받아 SQL 생성, 검증, DB 조회까지 처리합니다.
5. `slack_app.py`가 Slack DM / 채널 멘션을 받아 같은 QA 서비스를 호출합니다.
6. Notion 문서는 API로 읽어 chunk와 embedding으로 변환한 뒤 `docs.notion_pages`, `docs.document_chunks`에 저장합니다.

## PostgreSQL을 선택한 이유

- 질문의 대부분이 집계, 필터, 정렬, 기간 비교 같은 정형 질의입니다.
- 이런 유형은 벡터 검색보다 SQL 엔진이 정확하고 단순합니다.
- Airflow, Python, Slack QA 로직과 연결이 쉽습니다.
- Docker 로컬 개발과 운영 환경 재현이 단순합니다.
- 향후 `pgvector`를 붙이면 정형 질의와 문서 검색을 같은 저장소 계열에서 확장할 수 있습니다.

## SQL 생성 방식

- 현재 대상 테이블은 `dw.meta_ads_daily`로 제한합니다.
- 정형 데이터 SQL 생성 모델은 `Ollama qwen3:8b`를 사용합니다.
- LLM은 `SELECT` 쿼리만 생성합니다.
- 애플리케이션에서 한 번 더 금지 키워드와 대상 테이블을 검증합니다.
- DB 에러가 나면 한 번 더 SQL repair를 시도합니다.
- 채널명은 `google`, `facebook` canonical 값으로 정규화합니다.

## 왜 정형 데이터는 Ollama + qwen3:8b 인가

이 프로젝트의 정형 데이터 경로는 `Ollama + qwen3:8b`를 사용합니다.

이유는 아래와 같습니다.

- `Groq`는 외부 LLM API 서비스이기 때문에 질문과 데이터 맥락이 외부로 전송됩니다.
- `Ollama`는 로컬에서 모델을 실행하므로 데이터가 로컬 또는 내부 서버 안에 머뭅니다.
- 이 프로젝트는 사내 광고 성과 데이터를 다루기 때문에 속도보다 데이터 보안이 더 중요했습니다.
- `qwen3:8b`는 현재 로컬 모델 중에서 정형 데이터 SQL 생성 용도로 균형이 좋습니다.
  - `4b`보다 SQL 품질이 더 안정적이고
  - `14b`보다 로컬 실행 부담이 작으며
  - 자연어 -> SQL 변환 용도에 현실적인 선택입니다

정리:

- `Groq` = 빠르고 편하지만 외부 전송 있음
- `Ollama` = 느릴 수 있지만 보안상 유리함
- 그래서 정형 데이터 SQL 생성은 `Ollama + qwen3:8b`로 고정했습니다.

## 빠른 시작

1. `.env` 준비

```bash
cp .env.example .env
```

2. 인프라 실행

```bash
./scripts/start_local_services.sh
```

3. 적재 DAG 실행

```bash
docker compose exec airflow-api-server airflow dags unpause sheet_to_postgres
docker compose exec airflow-api-server airflow dags trigger sheet_to_postgres
```

4. 정형 데이터 질의 테스트

```bash
./.venv/bin/python main.py ask --question "최근 7일 채널별 매출 합계 보여줘"
```

5. Notion 문서 적재

먼저 `.env`에 아래 값을 설정합니다.

```env
NOTION_ACCESS_TOKEN=secret_xxx
NOTION_VERSION=2026-03-11
NOTION_PAGE_IDS=page_or_database_id_1,page_or_database_id_2
OLLAMA_DOC_MODEL=qwen3:8b
OLLAMA_EMBEDDING_MODEL=embeddinggemma
DOC_ANSWER_CHUNK_LIMIT=5
```

그 다음 적재를 실행합니다.

```bash
./.venv/bin/python main.py ingest-notion
```

이 명령은 다음 순서로 동작합니다.

- `NOTION_PAGE_IDS`에 있는 대상 ID를 순회합니다.
- Notion API에서 페이지 내용을 읽습니다.
- 상위 페이지를 넣으면 그 아래 child page도 재귀적으로 함께 수집합니다.
- 페이지가 아니면 database 또는 data source API로 fallback 합니다.
- 문서를 chunk로 나눕니다.
- Ollama 임베딩 모델로 벡터를 생성합니다.
- PostgreSQL `docs.notion_pages`, `docs.document_chunks`에 저장합니다.

6. Notion 문서 질의 테스트

```bash
./.venv/bin/python main.py ask-doc --question "예산 변경 정책이 뭐야?"
```

7. Slack 앱 실행

```bash
./.venv/bin/python slack_app.py
```

## Notion 문서 적재와 질의

이 프로젝트는 정형 데이터 SQL 질의 외에 Notion 기반 문서 질의 경로도 지원합니다.

실행 흐름은 아래와 같습니다.

```text
Notion API
    ↓
main.py ingest-notion
    ↓
chunk + embedding
    ↓
PostgreSQL / pgvector
    ↓
main.py ask-doc
```

사전 조건:

- Notion에서 Internal integration 생성
- integration에 `Read content` 권한 부여
- 읽을 페이지 또는 상위 페이지를 integration에 공유
- 대상 ID를 `NOTION_PAGE_IDS`에 등록

`NOTION_PAGE_IDS`에는 아래 중 하나를 넣을 수 있습니다.

- page ID
- database ID
- data source ID

상위 page ID를 넣으면 그 페이지 아래의 child page들도 재귀적으로 함께 적재합니다.

대표 실행 명령:

```bash
./scripts/start_local_services.sh
./.venv/bin/python main.py ingest-notion
./.venv/bin/python main.py ask-doc --question "예산 변경 정책이 뭐야?"
```

상세 설정은 [docs/notion-vector-setup.md](/Users/jykim/Documents/private/data-agent/docs/notion-vector-setup.md:1)를 보면 됩니다.
