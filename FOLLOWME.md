### 다음 순서를 참고하여 프로젝트를 수행해 보세요!!

처음부터 거대한 플랫폼을 가기보다, "반복 적재", "오류 추적", "같은 데이터를 여러 번 넣어도 안전함" 이 세 가지를 중점으로 설계하였습니다.

## 1. 1차 목표 

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

여기서 규칙이 흔들리면 이후 챗봇 정확도가 계속 흔들립니다. 가장 먼저 해야 하는 일은 "시트 포맷 계약"을 문서화하고 함께 데이터 규약을 만들어나가는 것 

## 3. 적재 구조는 raw -> mart

1. `raw_google_sheet_rows`
2. `mart_ads_daily`

이유:
- 시트 원본이 바뀌었을 때 역추적 용아
- 변환 로직 버그가 나도 raw 기준으로 재적재 가능
- 담당자 100명 수준이면 "누가 어떤 값을 바꿨는지" 추적 요구 위함

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

## 6. 내부 데이터 흐름도 

1. 시트 읽기와 DB 적재 안정화
2. 스케줄러 배치 적용
3. 실패 알림 Slack 연동
4. raw/mart 분리
5. 메타데이터 사전 정의
6. LLM이 SQL 생성
7. 챗봇 응답 검증 및 권한 통제

이 순서를 생각한 이유는, 데이터 품질 고정 -> 챗봇 응답 품질 영향 있기 떄문

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

항상 떠 있어야 하는 서비스는 아래 스크립트 하나로 올릴 수 있습니다.

```bash
./scripts/start_local_services.sh
```

이 스크립트가 하는 일:

- Docker Desktop 실행 확인
- `docker compose up -d`
- Ollama 서버 실행 확인
- 기본 모델 `qwen3:8b` 다운로드 확인

수동으로 나눠서 올릴 경우 먼저 아래를 실행 

```bash
docker compose up -d
cp .env.example .env
```

이 구성을 쓰면 아래 계정이 자동 생성 

- host: `localhost`
- port: `5432`
- database: `postgres`
- user: `postgres`
- password: `postgres`

Python에서는 JDBC URL이 아니라 아래 형식을 사용합니다.

```text
postgresql://postgres:postgres@localhost:5432/postgres
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

## 8. Airflow 3.2.0 파이프라인

이 저장소에는 Apache Airflow `3.2.0` 기준 Docker 구성이 포함되어 있습니다.

구성 파일:

- `docker-compose.yml`
- `Dockerfile.airflow`
- `dags/google_sheet_dw_pipeline.py`

구성 내용:

- `postgres`: DW 적재 대상 Postgres
- `airflow-mysql`: Airflow 메타데이터 DB
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

- `sheet_to_postgres`

작업 단계:

1. 소스 시트 접근 확인
2. 시트 데이터를 DW 형태로 변환
3. `dw.meta_ads_daily` 로 upsert
4. 적재 후 DW row count 검증

## 10. 자연어 질의 모델 실행 방식

현재 프로젝트의 자연어 질의 기본 경로는 `Ollama` 입니다.

- provider: `Ollama`
- model: `qwen3:8b`
- 목적: 정형 데이터 질의를 SQL로 변환

현재 흐름:

```text
사용자 질문
-> Ollama(qwen3:8b)
-> SQL 생성
-> PostgreSQL 조회
-> Slack / CLI 응답
```

## 11. Ollama + QA 실행 순서
### 11.1 최초 1회만 필요한 작업

Ollama 모델 다운로드:

```bash
./scripts/start_local_services.sh
```

이 스크립트가 최초 1회에는 모델 다운로드까지 같이 처리합니다.

### 11.2 Ollama 서버 실행

Ollama 서버가 꺼져 있을 때만 실행:

```bash
./scripts/start_local_services.sh
```

서버가 이미 떠 있으면 다시 실행해도 문제 없습니다.

### 11.3 상태 확인

모델이 받아져 있는지 확인:

```bash
ollama list
```

서버가 살아있는지 확인:

```bash
curl http://localhost:11434/api/tags
```

즉 지금은 `11.1`, `11.2`를 따로 하기보다 `start_local_services.sh` 한 번 실행하고 `11.3`으로 확인하는 방식이 가장 단순합니다.

### 11.4 CLI 질의 실행

평소 반복해서 실행하는 질의:

```bash
./.venv/bin/python main.py ask --question "최근 7일 채널별 매출 합계 보여줘"
```

정리:

- `ollama pull qwen3:8b` 는 최초 1회
- `ollama serve` 는 서버가 꺼져 있을 때만
- `ollama list`, `curl /api/tags` 는 확인용
- 실제 질의는 `main.py ask` 만 반복 실행

## 12. Slack 실행 순서

Slack은 CLI 질의가 먼저 정상 동작한 뒤 실행하는 것이 맞습니다.

권장 순서:

1. `./scripts/start_local_services.sh`
2. `main.py ask` 로 CLI 질의 성공 확인
3. `slack_app.py` 실행
4. Slack DM 또는 채널 멘션 테스트

Slack 앱 실행:

```bash
./.venv/bin/python slack_app.py
```

Slack에서 사용:

- DM: 멘션 없이 질문
- 채널: `/invite @봇이름` 후 `@봇이름 질문`

즉, `12번`은 `11번`이 먼저 끝난 뒤 수행하는 것이 맞습니다.

## 13. 실행 순서 요약

처음 세팅할 때:

```bash
./scripts/start_local_services.sh
ollama list
curl http://localhost:11434/api/tags
./.venv/bin/python main.py ask --question "최근 7일 채널별 매출 합계 보여줘"
./.venv/bin/python slack_app.py
```

이후 평소 사용:

```bash
./scripts/start_local_services.sh
./.venv/bin/python main.py ask --question "최근 7일 채널별 매출 합계 보여줘"
./.venv/bin/python slack_app.py
```

즉 질문한 내용 기준으로 답하면:

- `12번`, `13번`은 순서가 있습니다.
- 먼저 `11번`
- 그 다음 `12번`
- `13번`은 전체 요약입니다.

## 14. 현재 질의 대상 테이블

현재 챗봇이 직접 조회하는 테이블은 아래입니다.

- `dw.meta_ads_daily`

원본 블록 저장 테이블:

- `raw.google_sheet_table_blocks`

즉, 챗봇은 `raw`를 직접 읽지 않고 `dw`만 읽습니다.
