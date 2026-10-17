# Architecture (Proposed)

## Style

A modular monolith with clear Python package boundaries and a React frontend. PostgreSQL is the source of truth for relational records. File bytes live behind a storage interface; local filesystem storage is acceptable for development, with private object storage as a deployable adapter later.

## Stack

- Frontend: React, TypeScript, Vite; choose a single accessible component/styling approach during Milestone 1.
- API: Python, FastAPI, Pydantic, SQLAlchemy.
- Database/migrations: PostgreSQL, Alembic.
- Tests: Pytest plus a frontend unit-test runner; browser E2E only for critical workflows once the UI exists.
- CAD: evaluate Open CASCADE through a Python binding such as OCP/pythonocc-core. Select only after validating Python/platform compatibility, supported STEP behavior, packaging, and licensing.
- Currency: use explicit ISO 4217 codes and a conversion abstraction with recorded rate snapshots; do not make live FX calls a hidden dependency of deterministic costing.
- PDF: evaluate a library capable of direct text/vector extraction before adding OCR. OCR is a fallback, not the first path.
- Background jobs: defer until measured analysis duration or reliability needs justify a queue. Keep analysis behind a service boundary so it can move to a worker later.

## Backend boundaries

- `api`: routes, request/response schemas, auth dependencies, error mapping.
- `application`: use cases and transaction orchestration.
- `domain`: lifecycle rules, estimate model, quotation state transitions.
- `engineering`: STEP geometry adapters and future PDF extraction adapters.
- `manufacturing`: configurable operation rules and process-plan models.
- `costing`: deterministic formulas and versioned calculation logic.
- `persistence`: SQLAlchemy models/repositories and Alembic migrations.
- `storage`: private file-storage interface and adapters.
- `auth`: identity, role and project-level authorization.

Frontend modules mirror product workflows rather than duplicating business rules. Manufacturing rules and costing formulas must not live in UI components.

## Data flow

1. API validates upload and authorization.
2. Storage writes private bytes; DB stores metadata/version and an audit event.
3. An analysis run references an immutable file version and records pending/running/succeeded/partial/failed state.
4. Engineering adapter returns structured measurements plus provenance and warnings.
5. Review records preserve extracted values and create separate corrections/approval state.
6. Costing service validates explicit inputs and writes an immutable estimate version.
7. Quotation service snapshots customer/commercial terms and exact estimate version.

## Cross-cutting requirements

- Database transactions around lifecycle transitions and related writes.
- Foreign keys, uniqueness constraints, indexes on lookup/status/foreign-key fields.
- Idempotency or duplicate-submission protection for expensive analysis initiation.
- Structured logs with request/correlation IDs; never log file bytes, secrets, or full proprietary drawing text.
- Explicit limits/timeouts around parsing and geometry operations.
- No direct public URLs for uploaded files; authorize every download.

## Key trade-offs

- Start synchronous for ordinary CRUD and allow analysis execution to be replaced by background workers later.
- Prefer deterministic extraction and review over opaque AI interpretation.
- Avoid selecting a CAD dependency solely by popularity; prove it on representative fixtures and target deployment platforms first.
