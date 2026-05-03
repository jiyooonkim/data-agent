
# data-agent

A data pipeline and conversational analytics system that ingests Google Sheets-based ad performance data into PostgreSQL and enables natural language queries via Slack or CLI.

---

## Overview

* Source: Google Sheets (manual ad data input)
* Processing: Python + Apache Airflow 3.2.0
* Storage: PostgreSQL (raw + DW layers)
* Query Engine: LLM (Groq, OpenAI-compatible)
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

---

### Query System

* Input: natural language question
* LLM generates SQL (Groq)
* SQL validation layer:

  * only `SELECT`
  * restricted to `dw.meta_ads_daily`
  * forbidden keywords blocked
* Auto-repair on query failure
* Execute query in PostgreSQL
* Return formatted result (Slack / CLI)

---

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

---

### LLM Role (Strictly Scoped)

* LLM is used **only for SQL generation**
* Not used for document QA (yet)
* Guardrails:

  * table restriction
  * query validation
  * retry with repair

---

## Getting Started

### 1. Setup environment

```bash
cp .env.example .env
```

### 2. Run infrastructure

```bash
docker compose up -d --build
```

### 3. Run ingestion DAG

```bash
docker compose exec airflow-api-server airflow dags unpause sheet_to_postgres
docker compose exec airflow-api-server airflow dags trigger sheet_to_postgres
```

### 4. Run Slack app

```bash
./.venv/bin/python slack_app.py
```

---

## Core Components

* `ingestion/` – Google Sheets → Postgres pipeline
* `db/` – database connection layer
* `service/qa_service.py` – NL → SQL → execution
* `llm/` – prompt + LLM client (Groq)
* `slack_app.py` – Slack interface
* `dags/` – Airflow DAGs

---

## Future Work

* Query routing (structured vs document questions)
* RAG pipeline for docs / policies / meeting notes
* Multi-model architecture:

  * SQL queries → Groq
  * Document QA → Gemini
* Vector DB integration (likely `pgvector`)

---

## Summary

This project focuses on building a **structured data chatbot**:

* Reliable SQL-based analytics
* Natural language interface
* Production-ready ingestion pipeline

Next step: evolve into a **hybrid system (SQL + RAG)**.
 