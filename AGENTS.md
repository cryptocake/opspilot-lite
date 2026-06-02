# AGENTS.md

This file is for engineers and coding agents working in the repository.

## Project summary

OpsPilot Lite is a FastAPI-based framework for building human-approved AI workflow systems.

Core flow:
1. ingest inbound work into `RequestItem`
2. triage it into validated `TriageResult`
3. route it into reviewable `ProposedAction` payloads
4. approve, edit, reject, or retry actions
5. execute through `dry_run` or `webhook` mode
6. record `AuditEvent` entries at every important transition

## Key directories

- `app/` — application code
- `app/ai/` — provider adapters and triage logic
- `app/ingestion/` — inbound connectors
- `app/workflows/` — payload builders and routing rules
- `app/approvals/` — action state transitions
- `app/execution/` — execution adapters
- `app/web/` — Jinja/HTMX operator UI
- `tests/` — automated tests
- `examples/` — demo payloads
- `docs/` — architecture and extension docs

## Local commands

Set up:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
```

Run tests:

```bash
.venv/bin/python -m pytest -q
```

Run lint:

```bash
.venv/bin/ruff check .
```

Run the app:

```bash
.venv/bin/python -m uvicorn app.main:app --reload
```

## Configuration

Important environment variables:
- `OPSPILOT_DATABASE_URL`
- `OPSPILOT_LLM_PROVIDER`
- `OPSPILOT_OPENAI_BASE_URL`
- `OPSPILOT_OPENAI_API_KEY`
- `OPSPILOT_MODEL`
- `OPSPILOT_INBOX_PATH`
- `OPSPILOT_EXECUTION_MODE`
- `OPSPILOT_WEBHOOK_SINK_URL`
- `OPSPILOT_WEBHOOK_TIMEOUT_SECONDS`

## Extension rules

### New inbound connector
- normalize external input into `sender`, `subject`, `body`, `source_type`, `source_ref`
- create or reuse a `RequestItem`
- emit `request.ingested`
- keep duplicate detection deterministic
- do not execute side effects during ingestion

### New workflow action
- add payload generation in `app/workflows/definitions.py`
- route the action in `app/workflows/router.py`
- keep payloads understandable in the UI
- add tests for the payload shape and route selection

### New executor
- add the executor under `app/execution/`
- require approved actions before execution
- record failures as `action.failed`
- preserve auditability of the outgoing payload
- cover success and failure paths with tests

## Safety invariants

Do not break these:
- no execution without approval
- AI output must be validated before routing
- operators must be able to inspect payload JSON before execution
- invalid state transitions must fail loudly
- every important state change must create an audit event
- `fake` provider and `dry_run` mode should remain safe defaults for local use
