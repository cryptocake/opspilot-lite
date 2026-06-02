# Adding connectors

OpsPilot Lite is designed so teams can add inbound and outbound integrations without rewriting the workflow core.

## Inbound connectors

An inbound connector should:
1. normalize external data into `sender`, `subject`, `body`, `source_type`, and `source_ref`
2. create or reuse a `RequestItem`
3. record a `request.ingested` audit event
4. avoid external side effects during ingestion

Examples:
- email inbox poller
- CRM webhook consumer
- Slack slash command bridge
- support platform webhook receiver

### Rules

- Keep duplicate detection deterministic with `source_type` + `source_ref`.
- Persist the raw business request before triage.
- Do not execute automations during ingestion.
- Keep connector credentials in `.env` or your deployment secret manager, never in code.

## Outbound connectors

The shipped executor supports:
- `dry_run` mode
- `webhook` mode

For many teams, `webhook` mode is enough: point `OPSPILOT_WEBHOOK_SINK_URL` at an internal service that translates normalized action envelopes into Slack, Jira, GitHub, Notion, or proprietary systems.

If you need direct integrations in-process, add a new executor implementation under `app/execution/` and route approved actions through it.

## Recommended extension path

### Option 1: keep the generic webhook executor
Use this when you want:
- one stable workflow UI
- one stable audit model
- downstream execution handled elsewhere

### Option 2: add domain-specific action handlers
Use this when you want OpsPilot Lite itself to call specific APIs.
Typical steps:
1. introduce a new `action_type`
2. add payload generation in `app/workflows/definitions.py`
3. route the new action in `app/workflows/router.py`
4. add executor logic for that action type
5. cover the new flow with tests

## Connector checklist

Before shipping a connector, verify:
- duplicate handling is deterministic
- malformed payloads fail loudly
- approval is still required before side effects
- action payloads are visible to operators
- failures produce `action.failed` audit events
- retries are operator-driven, not silent
