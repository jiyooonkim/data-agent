# CI Checks

## Purpose

This project uses GitHub Actions as a **portfolio-level CI** layer.

The goal is not deployment automation.
The goal is to make sure the repository is still in a valid state after each push:

- Python environment can be created
- dependencies can be installed
- source code has no obvious static issues
- core application logic still passes basic tests

Current workflow file:

- [`.github/workflows/python-app.yml`](./.github/workflows/python-app.yml)

---

## Current CI Flow

```text
push / pull request
-> install dependencies
-> lint with Ruff
-> test with Pytest
```

Trigger:

- push to `main`
- pull request targeting `main`

Runtime:

- `ubuntu-latest`
- Python `3.12`

---

## Why CI Exists In This Project

This repository is a personal portfolio project, not a team production system.

So CI is intentionally lightweight.

Reasons:

1. Show that the project is not just uploaded code, but is automatically verified
2. Catch obvious breakage before the repository looks unstable
3. Leave a simple quality signal for reviewers
4. Keep the pipeline small enough to understand and maintain

This project does **not** currently use CD.

That means:

- no automatic deploy
- no automatic Slack app deploy
- no automatic Airflow deploy
- no Docker image publish step

---

## Check 1: Dependency Installation

### What it does

CI creates a clean Python environment and installs:

- `requirements.txt`
- CI tools:
  - `ruff`
  - `pytest`

### Why it is applied

This verifies that:

- the project can still be installed from scratch
- required packages are not missing
- the repository is not only working on one local machine

### What failure usually means

- broken package name
- missing dependency
- incompatible environment
- Python version mismatch

---

## Check 2: Lint With Ruff

### What it does

CI runs:

```bash
ruff check .
```

This statically checks Python files across the repository.

Typical issues Ruff catches:

- syntax problems
- undefined names
- bad imports
- module-level structural issues
- unused imports

### Why Ruff was chosen

This project previously used `flake8`, but it was removed.

Reasons for using `ruff` instead:

1. Faster
2. Simpler modern default
3. Good fit for small portfolio repositories
4. Replaces basic `flake8` usage cleanly

### Why lint is needed in this project

This repository has several entry points and folders:

- `ingestion/`
- `db/`
- `llm/`
- `service/`
- `main.py`
- `slack_app.py`

Because of that, simple import mistakes or misplaced top-level code can break the project without immediately being noticed.

Lint helps catch those issues early.

### Important note

Lint is **not runtime testing**.

It checks code structure, not business behavior.

Example:

- Ruff can catch a bad import
- Ruff cannot tell whether generated SQL is logically correct

---

## Check 3: Test With Pytest

### What it does

CI runs:

```bash
pytest
```

This executes test files under `tests/`.

### What pytest is doing here

Pytest does **not** automatically validate every Python file in the project.

It only runs the tests we explicitly wrote.

Current test intent:

- confirm structured-data settings load correctly
- confirm question normalization works
- confirm SQL validation logic blocks unsafe queries

### Why tests are needed in this project

The most important logic in this project is not UI.
It is backend decision logic, especially:

- natural language normalization
- SQL validation
- query safety rules

Those are easy to break with small changes.

So tests are used to protect the core behavior.

### Important distinction

```text
Ruff   = checks source code quality across files
Pytest = checks expected behavior through test cases
```

### Example

`service/qa_service.py`

- Ruff checks whether the module is structurally valid
- Pytest checks whether:
  - `normalize_question()` maps values correctly
  - `validate_sql()` blocks invalid SQL correctly

---

## Why We Added Tests Recently

Originally, CI failed with:

```text
collected 0 items
exit code 5
```

Reason:

- `pytest` was configured
- but there were no test files yet

So basic tests were added to make CI meaningful and stable.

Current tests:

- [`tests/test_settings.py`](./tests/test_settings.py)
- [`tests/test_qa_service.py`](./tests/test_qa_service.py)

---

## Why This CI Scope Is Intentionally Small

This project already has multiple moving parts:

- Google Sheets ingestion
- PostgreSQL DW
- Airflow DAG
- Ollama local model
- Slack bot

If CI tries to fully execute all external integrations on every push, it becomes:

- slower
- harder to maintain
- less reproducible in GitHub-hosted runners

So the current CI scope is intentionally limited to:

- code quality check
- basic logic verification

This is the right tradeoff for the current stage of the project.

---

## What Is Not In CI Right Now

The following are not part of current CI:

- real PostgreSQL integration test
- real Airflow DAG execution test
- real Ollama model inference test
- real Slack API integration test
- real Google Sheets fetch test

Reason:

- those require external/local runtime dependencies
- they are better handled as manual verification or later-stage integration tests

---

## Current CI File Summary

Workflow:

- [`.github/workflows/python-app.yml`](./.github/workflows/python-app.yml)

Lint config:

- [`pyproject.toml`](./pyproject.toml)

Tests:

- [`tests/test_settings.py`](./tests/test_settings.py)
- [`tests/test_qa_service.py`](./tests/test_qa_service.py)
