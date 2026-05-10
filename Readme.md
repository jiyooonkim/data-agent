
# Data-Agent

A data pipeline and conversational analytics system that ingests Google Sheets-based ad performance data into PostgreSQL and enables natural language queries via Slack or CLI.

---

## Project Setup

### 1. Prepare environment file

```bash
cp .env.example .env
```

### 2. Start local services

```bash
./scripts/start_local_services.sh
```

This script simply:

- checks Docker Desktop
- runs `docker compose up -d`
- starts `Ollama` if needed
- pulls `qwen3:8b` if missing

### 3. Run ingestion DAG

```bash
docker compose exec airflow-api-server airflow dags unpause sheet_to_postgres
docker compose exec airflow-api-server airflow dags trigger sheet_to_postgres
```

### 4. Test structured-data QA in CLI

```bash
./.venv/bin/python main.py ask --question "최근 7일 채널별 매출 합계 보여줘"
```

### 5. Run Slack app

```bash
./.venv/bin/python slack_app.py
```

---

## Project Docs

- [`docs/followme.md`](/Users/jykim/Documents/private/data-agent/docs/followme.md:1)
- [`docs/ci-checks.md`](/Users/jykim/Documents/private/data-agent/docs/ci-checks.md:1)
- [`docs/notion-vector-setup.md`](/Users/jykim/Documents/private/data-agent/docs/notion-vector-setup.md:1)
- [`docs/notion-doc-questions.md`](/Users/jykim/Documents/private/data-agent/docs/notion-doc-questions.md:1)
- [`docs/demo-questions.md`](/Users/jykim/Documents/private/data-agent/docs/demo-questions.md:1)
- [`docs/readme-kor.md`](/Users/jykim/Documents/private/data-agent/docs/readme-kor.md:1)
- [`docs/ads-data-chatbot-architecture.md`](/Users/jykim/Documents/private/data-agent/docs/ads-data-chatbot-architecture.md:1)

---

## Overview

* Source: Google Sheets (manual ad data input)
* Processing: Python + Apache Airflow 3.2.0
* Storage: PostgreSQL (raw + DW layers)
* Query Engine: LLM (Ollama local model)
* Interface: Slack bot / CLI

```text
Google Sheet
    ↓
Airflow (Python ingestion)
    ↓
PostgreSQL (DW)
    ↓
LLM (SQL generation)
    ↓
Query execution
    ↓
Slack / CLI response
```

---

## Core Components

* `ingestion/` – Google Sheets → Postgres pipeline
* `db/` – database connection layer
* `service/qa_service.py` – NL → SQL → execution
* `llm/` – prompt + LLM client (Ollama default)
* `slack_app.py` – Slack interface
* `dags/` – Airflow DAGs

---

## Goals

* Ingest Google Sheets data into a structured data warehouse
* Separate **raw** and **analytics-ready (dw)** layers
* Enable **natural language → SQL → result** workflow
* Provide a Slack-based chatbot for marketing/ops teams

---

## Key Features

### Data Pipeline

* Extract table ranges from Google Sheets
* Transform into structured DataFrame
* Store raw blocks:
  * `raw.google_sheet_table_blocks`
* Upsert normalized data:
  * `dw.meta_ads_daily`
* Orchestrated via Airflow DAG

### Query System

* Input: natural language question
* LLM generates SQL (Ollama)
* SQL validation layer:
  * only `SELECT`
  * restricted to `dw.meta_ads_daily`
  * forbidden keywords blocked
* Auto-repair on query failure
* Execute query in PostgreSQL
* Return formatted result (Slack / CLI)

### Slack Integration

* Supports:
  * DM queries
  * Channel mentions
* Thin interface layer
* Reuses shared QA service (`qa_service.py`)

---

## Why PostgreSQL

* Most queries are **structured analytics**:
  * aggregations (SUM, AVG)
  * filtering
  * time-based analysis
  * ranking (ROAS, campaigns)
* SQL is more reliable than vector search for this use case
* Simple integration with Airflow and Python
* Easy local setup with Docker
* Future extension with vector search via `pgvector`

---

## Architecture Decisions

### Raw vs DW Separation

**raw**

* preserves original sheet structure
* enables reprocessing
* useful for debugging

**dw**

* normalized for analytics
* optimized for SQL queries
* directly used by chatbot

### LLM Role (Strictly Scoped)

* LLM is used **only for SQL generation**
* Not used for document QA (yet)
* Guardrails:
  * table restriction
  * query validation
  * retry with repair

### Why Ollama + qwen3:8b for Structured Data

For this project, the structured-data path uses `Ollama + qwen3:8b` for practical reasons:

* `Groq` is an external LLM API service, so prompts and business questions are sent outside the local environment.
* `Ollama` runs the model locally, so data stays inside the developer machine or internal server.
* This project handles internal ad-performance data, so data exposure risk mattered more than raw speed.
* `qwen3:8b` was chosen as the balance point:
  * better SQL quality than very small local models like `4b`
  * lighter and more realistic than larger local models like `14b`
  * suitable for `natural language -> SQL` generation on structured analytics questions

In short:

* `Groq` = easier and often faster, but external transmission exists
* `Ollama` = slower, but better for security-sensitive internal analytics

---

## Notion + Vector Setup

For semi-structured document ingestion and QA:

- [`docs/notion-vector-setup.md`](/Users/jykim/Documents/private/data-agent/docs/notion-vector-setup.md:1)

---

## Future Work

* Query routing (structured vs document questions)
* RAG pipeline for docs / policies / meeting notes
* Multi-model architecture:

  * SQL queries → Ollama
  * Document QA → Gemini
* Vector DB integration (likely `pgvector`)

---

## Summary

This project focuses on building a **structured data chatbot**:

* Reliable SQL-based analytics
* Natural language interface
* Production-ready ingestion pipeline

Next step: evolve into a **hybrid system (SQL + RAG)**.

---

## Ollama Setup

The current default SQL model path is:

- Runtime: `Ollama`
- Model: `qwen3:8b`

Required environment variables:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_SQL_MODEL=qwen3:8b
```

Local setup:

```bash
./scripts/start_local_services.sh
```

Fallback:

- if `qwen3:8b` is too slow on the local machine, use `qwen3:4b`
 
