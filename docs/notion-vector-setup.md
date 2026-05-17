# Notion Vector Setup

## Goal

This project supports a second QA path for semi-structured and document-based questions:

```text
Notion
-> fetch page content by API
-> chunk text
-> Ollama embeddings
-> pgvector in PostgreSQL
-> similarity search
-> Ollama document answer
```

Structured-data questions still use:

```text
Google Sheet -> PostgreSQL -> Ollama SQL generation
```

Document questions use:

```text
Notion -> pgvector -> Ollama document answer
```

---

## What You Need To Create In Notion

### 1. Create an internal connection

Open the Notion Creator dashboard and create an **Internal connection**.

You need:

- connection name
- target workspace

### 2. Copy the installation access token

After the connection is created:

- open the **Configuration** tab
- copy the **Installation access token**

This becomes:

```env
NOTION_ACCESS_TOKEN=secret_xxx
```

### 3. Enable read capability

The connection must be able to read content.

At minimum, enable:

- `Read content`

### 4. Grant content access

The connection does not automatically see your pages.

You must explicitly share the pages or parent page with the connection.

You can do this in either place:

- Creator dashboard -> `Content access`
- Notion page UI -> `...` -> `Connections` -> `Add connection`

### 5. Copy the page IDs or database IDs you want to index

Example page URL:

```text
https://www.notion.so/workspace/Page-Title-0123456789abcdef0123456789abcdef
```

The page or database ID is the 32-character ID at the end.

You can register multiple targets:

```env
NOTION_PAGE_IDS=page_or_database_id_1,page_or_database_id_2,page_or_database_id_3
```

---

## Required Environment Variables

Add these to `.env`:

```env
NOTION_ACCESS_TOKEN=secret_xxx
NOTION_VERSION=2026-03-11
NOTION_PAGE_IDS=page_or_database_id_1,page_or_database_id_2
OLLAMA_DOC_MODEL=qwen3:8b
OLLAMA_EMBEDDING_MODEL=embeddinggemma
DOC_ANSWER_CHUNK_LIMIT=5
```

Notes:

- `NOTION_VERSION` should match the API version header.
- `OLLAMA_DOC_MODEL` is used to answer document questions.
- `OLLAMA_EMBEDDING_MODEL` is used to generate vector embeddings.
- `NOTION_PAGE_IDS` can contain:
  - normal page IDs
  - database IDs
  - data source IDs
- when a parent page ID is provided, child pages under that page are indexed recursively

---

## PostgreSQL Vector DB

This project uses PostgreSQL + pgvector.

The schema is created in:

- [`sql/create_google_sheet_dw_tables.sql`](./sql/create_google_sheet_dw_tables.sql)

Relevant tables:

- `docs.notion_pages`
- `docs.document_chunks`

---

## How To Run

### 1. Start local services

```bash
./scripts/start_local_services.sh
```

### 2. Recreate containers if pgvector is not active yet

```bash
docker compose down
docker compose up -d --build
```

### 3. Ingest Notion pages or databases

```bash
./.venv/bin/python main.py ingest-notion
```

### 4. Ask a document question

```bash
./.venv/bin/python main.py ask-doc --question "예산 변경 정책이 뭐야?"
```

---

## What The API Does

### `ingestion/notion_client.py`

- calls Notion API
- fetches page metadata
- fetches block children recursively
- recursively follows `child_page` blocks when a parent page ID is ingested
- falls back to database/data source APIs when page retrieval returns 404
- converts page content and row properties into markdown-like plain text

### `ingestion/notion_to_vector.py`

- chunks page or row text
- calls Ollama embedding API
- stores page documents and chunk embeddings in PostgreSQL

### `service/doc_qa_service.py`

- embeds the user question
- searches similar chunks in pgvector
- sends retrieved context to the document answer model

---

## Short Setup Checklist

```markdown
### Notion setup

1. Create Internal connection
2. Copy Installation access token
3. Enable Read content capability
4. Share target pages with the connection
5. Put page, database, or data source IDs into NOTION_PAGE_IDS

### Local setup

1. Start Docker and Ollama
2. Run `main.py ingest-notion`
3. Run `main.py ask-doc --question "..."`
```
