# Team Share

## 1. 프로젝트 목적

이 프로젝트의 목적은 `Google Sheet 기반 광고 데이터`를 사내에서 바로 질의할 수 있는 `대화형 챗봇` 형태로 제공하는 것입니다.

핵심 목표는 아래와 같습니다.

- Google Sheet에 입력되는 광고 성과 데이터를 주기적으로 수집
- PostgreSQL DW에 정규화해서 적재
- Slack 또는 CLI에서 자연어로 질문
- 질문을 SQL로 바꿔 결과를 바로 응답

대상 사용자는 마케팅/운영 약 30명입니다.

즉, 이 프로젝트는 단순 적재가 아니라 아래 흐름 전체를 염두에 두고 만들었습니다.

```text
Google Sheet 기반 광고 데이터, 전사 대화형 챗봇
자연어 질의 -> SQL -> 결과 응답
```

---

## 2. 전체 아키텍처

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

---

## 3. 왜 이렇게 설계했는가

### Google Sheet

- 현재 운영 입력 소스가 Google Sheet입니다.
- 현업이 직접 수정하고 관리하기 쉬운 형태입니다.
- 다만 그대로는 질의 응답에 부적합합니다.
- 표가 여러 블록으로 나뉘어 있고, 날짜가 가로로 퍼져 있어 정규화가 필요합니다.

### Python ingestion + Airflow

- 이 단계는 `데이터 준비 & 적재`  역할 
- Airflow 역할 
  - 시트 읽기
  - 전처리
  - DW 적재
  - 적재, 결과 검증

### PostgreSQL

논리적으로는 `mart_ads_daily` 같은 마트 계층을 생각하고 있지만, 현재 구현 테이블은 `dw.meta_ads_daily` 입니다.

PostgreSQL을 선택한 이유는 명확합니다.

- 질문의 대부분이 정형 데이터 질의입니다.
  - 매출 합계
  - 채널별 비교
  - ROAS 순위
  - 캠페인별 성과
  - 기간 비교
- 이런 질문은 문서 검색보다 SQL 집계가 정확합니다.
- PostgreSQL은 다음 장점이 있습니다.
  - 집계, 정렬, 필터, 날짜 처리에 강함
  - 운영 난이도가 낮음
  - Airflow/Python 연동이 단순함
  - Slack 챗봇의 조회 소스로 바로 쓰기 좋음

### Ollama

- 현재 정형 데이터 SQL 생성 모델은 `Ollama qwen3:8b`를 사용합니다.
- 이유는 무료로 사용할 수 있고, 사내 데이터가 외부 API로 나가지 않게 하기 위해서입니다.
- 현재 구조는 `질문 -> Ollama -> SQL -> PostgreSQL 조회` 경로입니다.

### Slack or CLI

- 같은 QA 로직을 두 채널에서 재사용합니다.
- CLI는 개발/검증용입니다.
- Slack은 실제 사용자 인터페이스입니다.
- 즉, 질문 처리 엔진은 하나로 두고 입력 채널만 나눴습니다.

---

## 4. 현재 구현 범위

현재 구현된 것은 아래까지입니다.

### 적재

- Google Sheet 범위 읽기
- DataFrame 변환
- 원본 블록 저장
  - `raw.google_sheet_table_blocks`
- DW upsert
  - `dw.meta_ads_daily`
- Airflow DAG 실행
  - DAG ID: `sheet_to_postgres`

### 질의응답

- 자연어 질문 입력
- Ollama로 SQL 생성
- SQL 안전성 검증
- PostgreSQL 조회
- 결과를 Slack / CLI에 응답

### Slack

- Slack Socket Mode 기반 최소 구현 완료
- DM 질문 처리
- 채널 멘션 질문 처리

---

## 5. 현재 테이블 구조

### raw 계층

- `raw.google_sheet_table_blocks`
- Google Sheet 원본 표 블록을 저장합니다.
- 목적:
  - 원본 보존
  - 전처리 로직 변경 시 재적재 가능

### dw 계층

- `dw.meta_ads_daily`
- 현재 챗봇이 직접 조회하는 핵심 테이블입니다.

주요 컬럼:

- `channel`
- `event_date`
- `product_name`
- `campaign_name`
- `campaign_mapping`
- `budget`
- `spend`
- `revenue`
- `roas`

---

## 6. SQL 생성은 어떻게 동작하는가

현재 구조는 아래와 같습니다.

```text
사용자 질문
-> question normalize
-> Ollama 호출
-> SQL 생성
-> SQL validation
-> PostgreSQL 실행
-> 결과 포맷
-> Slack or CLI 응답
```

현재 의도는 다음과 같습니다.

1. SQL 대상 테이블을 제한합니다.
- `dw.meta_ads_daily`만 조회 가능

2. 쓰기 쿼리를 차단합니다.
- `INSERT`
- `UPDATE`
- `DELETE`
- `DROP`
- `ALTER`
- `CREATE`

3. 생성된 SQL을 애플리케이션에서 한 번 더 검증합니다.

4. 채널명 같은 자주 흔들리는 값은 canonical 형태로 보정합니다.
- `구글`, `Google` -> `google`
- `페이스북`, `Facebook` -> `facebook`

5. DB 에러가 나면 한 번 더 SQL repair를 시도합니다.

즉, LLM이 SQL을 바로 실행하는 구조가 아니라 `프롬프트 제한 + 실행 전 검증 + 에러 시 보정` 구조입니다.

---

## 7. 왜 raw / dw 로 나눴는가

이 분리는 의도적으로 넣었습니다.

### raw

- 원본 시트 구조를 보존
- 전처리 로직이 바뀌어도 재현 가능
- 디버깅이 쉬움

### dw

- 챗봇/분석용 조회 구조 제공
- 날짜, 채널, 상품, 캠페인 단위로 정규화
- SQL 질의가 쉬움

즉, `입력 원본 보존`과 `조회 최적화`를 분리한 것입니다.

---

## 8. Slack 앱 세팅 방법

현재 구조는 Socket Mode 기준입니다.

### 8.1 필요한 토큰

`.env`에 아래 값이 필요합니다.

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
```

### 8.2 `SLACK_BOT_TOKEN`

경로:

- Slack API App
- `OAuth & Permissions`
- `Bot User OAuth Token`

### 8.3 `SLACK_APP_TOKEN`

경로:

- Slack API App
- `Settings -> Basic Information`
- `App-Level Tokens`
- `Generate Token and Scopes`
- scope: `connections:write`

### 8.4 필요한 Bot Token Scopes

- `chat:write`
- `app_mentions:read`
- `im:history`

### 8.5 필요한 Event Subscriptions

Bot events:

- `app_mention`
- `message.im`

### 8.6 Socket Mode

- `Settings -> Socket Mode`
- Enable ON

### 8.7 App Home

- DM 사용을 위해 `Messages Tab` 사용 가능 상태 권장

### 8.8 설치/재설치

scope나 event를 바꾸면 반드시 `Install to Workspace` 또는 `Reinstall` 해야 합니다.

---

## 9. Slack 사용 방법

### DM

봇과 1:1 DM에서는 멘션 없이 질문하면 됩니다.

예:

```text
어제 구글 채널 매출 보여줘
최근 7일 채널별 ROAS 비교해줘
```

### 채널

채널에서는 먼저 봇을 초대해야 합니다.

```text
/invite @봇이름
```

그 다음 멘션해서 질문합니다.

```text
@봇이름 어제 페이스북 매출 합계 알려줘
@봇이름 구글 채널 캠페인별 매출 보여줘
```

---

## 10. 프로젝트 실행 방법

### 10.1 인프라 실행

```bash
docker compose up -d --build
```

실행 대상:

- PostgreSQL
- Airflow API server
- Airflow scheduler
- Airflow dag-processor
- Airflow triggerer

### 10.2 적재 DAG 실행

```bash
docker compose exec airflow-api-server airflow dags unpause sheet_to_postgres
docker compose exec airflow-api-server airflow dags trigger sheet_to_postgres
```

### 10.3 DB 적재 확인

```bash
./scripts/psql_connect.sh -c "select count(*) from dw.meta_ads_daily;"
./scripts/psql_connect.sh -c "select count(*) from raw.google_sheet_table_blocks;"
```

### 10.4 Slack 앱 실행

```bash
./.venv/bin/python slack_app.py
```

### 10.5 CLI 질의 테스트

```bash
./.venv/bin/python main.py ask --question "최근 7일 채널별 매출 합계 보여줘"
```

### 10.6 데모용 데이터 적재

실데이터가 적으면 QA 테스트가 어렵기 때문에 seed 경로도 추가해두었습니다.

```bash
env DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres \
./.venv/bin/python main.py seed-demo-data
```

현재 seed 데이터는 아래 규모입니다.

- `facebook`: 1000 rows
- `google`: 1000 rows

예상 질문 목록은 [`demo_questions.md`](/Users/jykim/Documents/private/data-agent/demo_questions.md:1) 에 정리했습니다.

---

## 11. 현재 구현 의도

이번 구현에서 의도한 것은 아래입니다.

### 1. raw & dw

- raw는 보존
- dw는 조회

### 3. LLM은 SQL 생성 역할로 제한

- 지금 단계에서는 문서 검색이 아니라 정형 데이터 질의가 주 목적입니다.
- 따라서 먼저 SQL path를 안정화하는 게 맞습니다.

### 4. Slack은 얇게 유지

- `slack_app.py`는 이벤트 수신과 응답만 담당
- 실제 질문 처리 로직은 `service/qa_service.py`

즉, 입력 채널이 Slack에서 다른 UI로 바뀌어도 QA 로직은 유지할 수 있습니다.

---

## 12. 현재 한계

현재 구조는 정형 데이터 질문에는 맞지만 아래는 아직 본격 대응하지 않습니다.

- 유사 문장/유사 캠페인 탐색
- 자유 텍스트 설명 기반 검색
- 회의록/가이드/위키 검색
- 정책 문서 QA

이 요구는 SQL만으로 해결되지 않습니다.

### 다음 단계: 멀티 모델 + Vector DB

이후에는 아래 구조로 확장할 계획입니다.

```text
사용자 질문
-> 질문 분류
   -> 정형 데이터 질문
      -> Ollama
      -> SQL 생성
      -> PostgreSQL 조회
   -> 문서/정책 질문
      -> Gemini
      -> Vector DB / RAG
      -> 문서 기반 답변
```

### 왜 이렇게 나누는가

정형 데이터 질문과 문서 질문은 성격이 다릅니다.

#### 정형 데이터 질문

예:

- 어제 채널별 매출 알려줘
- 캠페인별 ROAS 순위 보여줘
- 최근 7일 지출 합계 알려줘

이건 SQL 기반이 정확합니다.

#### 문서/정책 질문

예:

- 광고비 집행 기준이 뭐야
- 운영 가이드 문서 찾아줘
- 회의록에서 쿠팡 관련 내용 알려줘
- 정책상 예산 변경 기준 설명해줘

이건 문서 검색과 요약이 필요합니다.

### 모델 분리 방향

- 정형 데이터 질문 -> `Ollama`
- 문서/정책 질문 -> `Gemini`

즉, 한 모델로 모든 문제를 해결하기보다 질문 의도에 맞게 모델 역할을 나누는 방향입니다.

### Vector DB가 필요한 이유

문서/회의록/위키/가이드/정책 질의는 아래가 필요합니다.

- chunking
- embedding
- semantic retrieval
- 관련 문서 context 주입

즉 PostgreSQL 정형 질의만으로는 부족합니다.

Vector DB 후보는 다음 중 하나가 자연스럽습니다.

- `pgvector`
- `Qdrant`
- `Weaviate`
- `Pinecone`

현재 프로젝트는 PostgreSQL을 이미 사용 중이므로, 첫 확장 후보는 `pgvector`가 가장 자연스럽습니다.


### 예상 확장 구조

```text
service/
  qa_service.py
  router_service.py
  sql_qa_service.py
  doc_qa_service.py

llm/
  llm_client.py
  prompt.py
  ollama_client.py
  gemini_client.py

rag/
  embedder.py
  vector_store.py
  retriever.py
```

의도는 아래와 같습니다.

- `router_service.py`
  - 질문 의도를 `sql`, `doc`, `hybrid`로 분류
- `sql_qa_service.py`
  - Ollama + PostgreSQL
- `doc_qa_service.py`
  - Gemini + Vector DB
- `qa_service.py`
  - 최종 진입점

---

## 14. 정리

1차 poc

- Google Sheet -> PostgreSQL 적재
- 자연어 질문 -> SQL 생성 -> 결과 응답
- Slack DM / 채널 멘션 질의

2차 예정 

1. 정형 데이터 QA 안정화
2. Slack 운영 보강
3. 문서/정책 질문 경로 추가
4. Vector DB 도입
5. Ollama + Gemini 멀티 모델 분리

즉 지금은 `정형 데이터 챗봇의 기반`을 만든 단계이고, 이후에는 `문서형 RAG 챗봇`까지 통합하는 방향으로 확장예정
