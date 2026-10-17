# API Outline (Phase 0)

Exact schemas and routes will be specified as each vertical slice is implemented. Proposed REST API prefix: `/api/v1`.

## Initial resource groups

- `GET /health` and `GET /ready` — process health versus dependency readiness.
- `/customers` — list, create, retrieve, update, deactivate.
- `/rfqs` — list, create, retrieve, update status.
- `/projects` — list, create, retrieve, update lifecycle.
- `/projects/{project_id}/parts` — part management.
- `/projects/{project_id}/files` — upload/list file metadata.
- `/files/{file_id}/versions/{version}` — authorized metadata/download endpoint.
- `/files/{file_id}/analysis-runs` — create/list analysis runs.
- `/analysis-runs/{run_id}` — status/result/warnings.
- `/analysis-runs/{run_id}/review` — review/corrections/approval.
- `/process-plans`, `/cost-estimates`, `/quotations`, `/production-feedback` — added in later milestones.

## Contract rules

- Pydantic request/response schemas; never serialize ORM models indiscriminately.
- Consistent error envelope with stable machine-readable `code`, safe `message`, optional field errors, and request/correlation ID.
- Validate IDs, units, quantities, lifecycle transitions, file type/size, and authorization on the server.
- Pagination and stable ordering for list endpoints.
- Return `202 Accepted` only when work is actually queued; do not claim background processing when execution is synchronous.
- Downloads require authorization and should not expose permanent public storage URLs.
- Idempotency protection for expensive or duplicate analysis requests should be added with the analysis lifecycle.

## Authentication

Authentication provider and session/token strategy remain an approval-time decision. No sensitive endpoint should be exposed before authentication and project-level authorization are implemented and tested.
