# Google Sheet -> PostgreSQL 개발 순서

30명 안팎이 사용하는 사내 챗봇을 기준으로 하면, 처음부터 거대한 플랫폼으로 갈 필요는 없습니다. 대신 "반복 적재", "오류 추적", "같은 데이터를 여러 번 넣어도 안전함" 이 세 가지를 먼저 확보하는걸 우선으로 하였습니다.

## 1. 1차 목표 먼저 고정

첫 단계 목표:

- Google Sheet 데이터를 읽는다.
- 정해진 컬럼 규칙으로 mart 형태로 변환한다.
- PostgreSQL에 upsert 한다.
- 같은 배치를 다시 돌려도 중복 적재되지 않는다.

이 단계에서는 아직 LLM, Slack, 승인 플로우보다 ingestion 안정화가 우선입니다.

## 2. 시트 입력 규칙부터 정리

운영자가 시트에 어떤 형식으로 넣어야 하는지 먼저 고정해야 합니다.

- 식별 컬럼: `상품명`, `캠페인`
- 날짜별 성과 컬럼: `YYYY-MM-DD_지출금액`, `YYYY-MM-DD_매출액`, `YYYY-MM-DD_ROAS`
- 제외 행 규칙: `총계`, `SUMMARY`

여기서 규칙이 흔들리면 이후 챗봇 정확도가 계속 흔들립니다. 가장 먼저 해야 하는 일은 "시트 포맷 계약"을 문서화하는 것입니다.

## 3. 적재 구조는 raw -> mart 2단계로 가는 게 좋음

지금 코드처럼 곧바로 mart에 넣는 방식으로 시작은 가능하지만, 운영이 붙으면 raw 적재 테이블을 하나 두는 편이 낫습니다.

추천 순서:

1. `raw_google_sheet_rows`
2. `mart_ads_daily`

이유:

- 시트 원본이 바뀌었을 때 역추적이 쉽습니다.
- 변환 로직 버그가 나도 raw 기준으로 다시 적재할 수 있습니다.
- 담당자 30명 수준이면 "누가 어떤 값을 바꿨는지" 추적 요구가 금방 생깁니다.

## 4. 배치 실행 방식
- 일배치 또는 1시간 1회 배치
- Apache Airflow 3.2.0 을 사용하였습니다.

## 5. DB 설계에서 먼저 넣어야 하는 것

`mart_ads_daily` 기준 최소 키:

- `date`
- `channel`
- `product`
- `campaign`

여기에 unique constraint를 두고 upsert 해야 합니다. 그래야 같은 날짜 데이터를 다시 읽어와도 중복이 안 생깁니다.

## 6. 챗봇 실행 순서

1. 시트 읽기와 DB 적재 안정화
2. 스케줄러 배치 적용
3. 실패 알림 Slack 연동
4. raw/mart 분리
5. 메타데이터 사전 정의
6. LLM이 SQL 생성
7. 챗봇 응답 검증 및 권한 통제

이 순서를 생각한 이유는, 데이터 품질이 먼저 고정되지 않으면 챗봇 품질도 고정되지 않기 때문입니다.

## 7. 개발 환경 & 프로젝트 실행 방법 

현재 코드에서는 아래 값이 필요합니다.

- `GOOGLE_CREDENTIALS_FILE`
- `GOOGLE_SHEET_URL`
- `GOOGLE_WORKSHEET_NAME`
- `DATABASE_URL`
- `MART_TABLE_NAME` 
 

```bash
python3.12 --version
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

DB를 Docker로 올릴 경우 먼저 아래를 실행 

```bash
docker compose up -d
cp .env.example .env
```

이 구성을 쓰면 아래 계정이 자동 생성 됩니다. 

- host: `localhost`
- port: `5432`
- database: `postgres`
- user: `data_agent`
- password: `data_agent`

Python에서는 JDBC URL이 아니라 아래 형식을 사용합니다.

```text
postgresql://data_agent:data_agent@localhost:5432/postgres
```

```bash
python3.12 ingestion/sheet_to_postgres.py
```

또는 코드에서:

```python
from ingestion.sheet_to_postgres import run

result = run()
print(result)
```

## 8. 구글 시트 링크를 읽는 방식

현재 링크:

`https://docs.google.com/spreadsheets/d/1a1kgbwfJs1N_fwvxBcojHnKykvfBfeiRM7VJz4z00K0/edit?usp=sharing`

이 링크는 현재 공개 export가 막혀 있어서 브라우저 없는 서버에서는 익명 CSV 다운로드가 되지 않습니다. 따라서 운영 방식은 아래가 맞습니다.

1. Google Cloud 서비스 계정 생성
2. `credentials.json` 발급
3. 해당 서비스 계정 이메일을 시트 공유 대상에 추가
4. 코드에서 `gspread.service_account(...).open_by_url(...)` 사용

이 방식이 private sheet 운영에 가장 안정적입니다.

## 9. Airflow 3.2.0 파이프라인

이 저장소에는 Airflow `3.2.0` 기준 Docker 구성이 포함되어 있습니다.

구성 파일:

- `docker-compose.yml`
- `Dockerfile.airflow`
- `dags/google_sheet_dw_pipeline.py`

구성 내용:

- `postgres`: DW 적재 대상 Postgres
- `airflow-postgres`: Airflow 메타데이터 DB
- `airflow-init`: Airflow DB 초기화 및 admin 계정 생성
- `airflow-api-server`: Airflow UI/API
- `airflow-scheduler`
- `airflow-dag-processor`
- `airflow-triggerer`

실행 순서:

```bash
cp .env.example .env
docker compose up -d --build
```

접속:

- Airflow UI: `http://localhost:8080`
- 로컬 개발용 설정에서는 인증을 비활성화하고 모든 사용자를 admin으로 허용

DAG:

- `google_sheet_to_dw`

작업 단계:

1. 소스 시트 접근 확인
2. 시트 데이터를 mart 형태로 변환
3. `public.mart_ads_daily` 로 upsert
4. 적재 후 DW row count 검증
