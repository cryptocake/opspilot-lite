# OpsPilot Lite

OpsPilot Lite is an open-source framework for building human-approved AI workflow systems.

It receives inbound business requests, classifies them into structured data, proposes machine-actionable next steps, keeps a human approval gate in front of side effects, and records a complete audit trail from intake to execution.

The project is intentionally small:
- FastAPI for HTTP and UI
- SQLModel + SQLite for persistence
- Pydantic for validated AI outputs
- Jinja + HTMX for an operator-facing workspace
- pluggable execution with safe dry-run defaults

## What it is for

OpsPilot Lite is a starting point for teams that need a framework they can fork and extend for:
- support intake
- sales and automation inquiries
- internal task routing
- meeting follow-up workflows
- approval-gated automations
- webhook-first operations tooling

It is not a full SaaS product. It does not include multi-tenant auth, RBAC, billing, or admin suites.
It gives you the workflow core so your team can connect real systems and customize the business logic.

## Core capabilities

- Ingest requests from a local folder or webhook
- Normalize inbound data into `RequestItem` records
- Classify requests into a strict `TriageOutput` schema
- Route each request into reviewable `ProposedAction` payloads
- Approve, edit, reject, or retry actions in a web workspace or API
- Execute actions through:
  - `dry_run` mode for safe demos and local development
  - `webhook` mode for delivery into downstream tools
- Record audit events for every important transition
- Ship with deterministic demo data and tests

## Architecture

```text
incoming source ──► ingestion ──► triage ──► workflow routing ──► approval ──► execution
       │                │             │              │                 │            │
       └────────────────┴─────────────┴──────────────┴─────────────────┴────────────┘
                                      persisted in SQLite with audit events
```

### Data model

- `RequestItem` — normalized inbound request
- `TriageResult` — validated AI interpretation
- `ProposedAction` — reviewable action payload
- `AuditEvent` — immutable event log entry

### Execution model

The framework separates planning from side effects:
1. AI proposes actions.
2. A human reviews the exact JSON payload.
3. The system executes only approved actions.
4. The audit trail records the result.

That separation is the main design contract of the project.

## Quickstart

### Local Python

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
python -m uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000
```

### Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Open:

```text
http://localhost:8080
```

## Default demo flow

1. Open the home page.
2. Click `Load demo workflows`.
3. Open the workspace.
4. Review generated actions.
5. Edit one payload.
6. Approve or reject actions.
7. Execute an approved action.
8. Inspect the audit trail.

The shipped demo data lives in `examples/inbox/` and `examples/webhook_payloads/`.

## Configuration

Copy `.env.example` to `.env` and set the values you need.

| Variable | Purpose | Default |
|---|---|---|
| `OPSPILOT_DATABASE_URL` | SQLAlchemy/SQLModel database URL | `sqlite:///./opspilot.db` |
| `OPSPILOT_LLM_PROVIDER` | `fake`, `openai`, or `openai-compatible` | `fake` |
| `OPSPILOT_OPENAI_BASE_URL` | Base URL for OpenAI-compatible providers | empty |
| `OPSPILOT_OPENAI_API_KEY` | API key for OpenAI-compatible providers | empty |
| `OPSPILOT_MODEL` | Model identifier | empty |
| `OPSPILOT_INBOX_PATH` | Folder used by demo ingestion | `examples/inbox` |
| `OPSPILOT_EXECUTION_MODE` | `dry_run` or `webhook` | `dry_run` |
| `OPSPILOT_WEBHOOK_SINK_URL` | Downstream execution endpoint for `webhook` mode | empty |
| `OPSPILOT_WEBHOOK_TIMEOUT_SECONDS` | HTTP timeout for webhook execution | `10` |

### LLM providers

`fake` is the default and is recommended for local development, CI, and recorded demos.
It returns deterministic structured outputs with no external dependency.

To use a real provider, set:
- `OPSPILOT_LLM_PROVIDER=openai-compatible`
- `OPSPILOT_OPENAI_BASE_URL=...`
- `OPSPILOT_OPENAI_API_KEY=...`
- `OPSPILOT_MODEL=...`

Any local or hosted model that exposes an OpenAI-compatible API can be plugged in this way.

### Execution modes

#### `dry_run`
The framework records what would have been executed and stores the payload in the audit trail.
No external side effects occur.

#### `webhook`
The framework POSTs a normalized execution envelope to `OPSPILOT_WEBHOOK_SINK_URL`:

```json
{
  "request_id": 3,
  "action_id": 7,
  "action_type": "create_task",
  "title": "Create support follow-up task",
  "payload": {
    "title": "Follow up on API key rotation",
    "priority": "High"
  }
}
```

This is the main production extension point. Your team can point it at an internal service, queue bridge, iPaaS endpoint, or custom automation adapter.

## API surface

Key endpoints:
- `POST /api/ingest/folder`
- `POST /api/process`
- `POST /api/webhook/request`
- `GET /api/requests`
- `GET /api/requests/{id}`
- `GET /api/actions/pending`
- `POST /api/actions/{id}/approve`
- `POST /api/actions/{id}/edit`
- `POST /api/actions/{id}/reject`
- `POST /api/actions/{id}/execute`
- `GET /api/audit`

Interactive OpenAPI docs are available at `/docs`.

## Extension points

Teams usually extend OpsPilot Lite in three places:

### 1. Inbound connectors
Add new ingestion modules that create `RequestItem` rows and emit `request.ingested` audit events.
Examples:
- email polling
- helpdesk webhooks
- CRM form submissions
- internal queue consumers

### 2. Workflow routing
Update `app/workflows/router.py` and `app/workflows/definitions.py` to map categories into actions your business actually performs.
Examples:
- create Jira tickets
- push customer replies into a review queue
- create CRM follow-up tasks
- emit finance review packets

### 3. Execution adapters
Keep `dry_run` for safe local use, or replace/extend the webhook executor for:
- Slack
- Notion
- GitHub
- Jira
- internal orchestration services
- queue-based worker systems

## Safety guarantees

The framework is built around a few hard rules:
- no execution without approval
- dry-run is the default
- the AI output is validated before routing
- the exact action payload is visible before execution
- invalid action transitions are rejected
- every important state change is logged
- duplicate webhook requests are deduplicated by source reference

## Development commands

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
```

## Repository guide

- `app/` — application code
- `tests/` — unit and integration tests
- `examples/` — demo input payloads
- `docs/architecture.md` — system design notes
- `docs/adding-connectors.md` — extension guidance for inbound/outbound integrations
- `AGENTS.md` — repository map, commands, and contributor/agent guidance

## What to build on top of it

Common next steps for a team forking this repo:
- connect a real LLM provider
- point execution at an internal webhook bridge
- add domain-specific categories and action definitions
- add SSO, user management, or RBAC if needed
- move from SQLite to PostgreSQL
- add background workers for high-volume ingestion or execution

## License

MIT
