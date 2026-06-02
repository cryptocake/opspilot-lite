# OpsPilot Lite Architecture

OpsPilot Lite is a small workflow framework with one core idea:

> AI can propose work, but humans stay in control of side effects.

## Runtime flow

1. **Ingestion**
   - folder input or webhook input becomes a normalized `RequestItem`
   - each inbound request gets a stable `source_type` + `source_ref`
   - ingestion records a `request.ingested` audit event

2. **Triage**
   - the AI layer returns strict JSON validated against `TriageOutput`
   - the validated result is persisted as `TriageResult`
   - triage records a `request.triaged` audit event

3. **Workflow routing**
   - the router converts a triage category into one or more `ProposedAction` records
   - each action has a visible JSON payload for operator review
   - proposed actions record `action.proposed` audit events

4. **Approval**
   - operators can approve, edit, reject, or retry actions
   - invalid transitions are rejected at the service layer, not just hidden in the UI
   - request status is recalculated from child action state

5. **Execution**
   - `dry_run` mode simulates execution without side effects
   - `webhook` mode delivers normalized action envelopes to a downstream service
   - execution records `action.executed` or `action.failed`

6. **Audit**
   - audit history is queryable through the API and visible in the UI
   - the audit trail is the system of record for operational trust

## Data model

### `RequestItem`
The canonical inbound business request.

### `TriageResult`
The validated AI interpretation of the request.

### `ProposedAction`
A concrete action payload that a human can inspect before execution.

### `AuditEvent`
An append-only event describing what happened and why.

## Design choices

### Request state is derived from action state
A request is:
- `new` before triage
- `triaged` if understood but no actions exist
- `pending_approval` while open actions remain
- `completed` when all actions are either executed or intentionally rejected
- `rejected` when every proposed action is rejected
- `failed` when any child action fails execution

### The executor is a boundary
The executor layer is deliberately simple so teams can swap in:
- internal webhook bridges
- queue publishers
- direct SaaS integrations
- background workers

### Demo mode and production mode share the same workflow
The demo does not bypass the real workflow path.
It uses the same ingestion, triage, routing, approval, execution, and audit chain as a live deployment, with safer defaults.
