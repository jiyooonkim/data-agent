# Governed Enterprise Analytics Agent

A lightweight LLM-powered data assistant that enables natural language querying over structured mart tables with SQL-based execution and metadata-driven validation.

## POC Goal

Slack에서 비즈니스 사용자가 자연어로 질문하면, 챗봇이 metric dictionary와 mart table metadata를 검색하고, 안전한 SQL을 생성/검증한 뒤 Postgres에서 계산된 결과를 요약해 응답합니다.

## Stack

- Postgres + pgvector
- Python 3.12
- Slack Bolt
- OpenAI API
- Docker Compose / Colima

## Flow

```text
Google Sheet / CSV
  -> Python ingestion
  -> Postgres mart table
  -> Slack question
  -> Python Slack Bot
  -> pgvector metadata search
  -> LLM SQL generation
  -> SQL safety validation
  -> Postgres SQL execution
  -> Slack response with basis
```

## Setup

설치와 실행 순서는 [docs/enterprise-chatbot-setup.md](docs/enterprise-chatbot-setup.md)를 기준으로 진행합니다.
