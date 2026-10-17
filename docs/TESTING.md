# Testing Strategy

## Backend

- Pytest unit tests for domain lifecycle transitions, validation, units, costing formulas, rounding, and quotation snapshots.
- API integration tests against a disposable PostgreSQL database for constraints, transactions, auth, upload behavior, and error contracts.
- CAD adapter tests using deterministic fixture models with known values and documented tolerances.
- Security tests for cross-project access, unauthorized downloads, oversized/invalid uploads, path/key manipulation, and parser failures.

## Frontend

- Unit/component tests for forms, validation feedback, state transitions, loading/empty/error states, and access-denied behavior.
- End-to-end tests for critical workflow: create project → upload → review → estimate → quotation. Add once stable APIs and UI exist.

## Reliability and reproducibility

- Test duplicate requests and retry behavior for analysis runs.
- Test failed/partial processing and recovery without corrupting lifecycle state.
- Test that corrected values do not mutate extraction records.
- Test that estimate revisions and issued quotation snapshots are immutable.
- Test migrations from an empty database and upgrade from the previous schema.

## Quality gates

No milestone is complete unless focused tests run and results are recorded. If a test cannot run, record the exact environment or dependency reason. Never report unrun tests as passing.

## Current results

No tests have been run because this phase contains planning documents only; there is no application code or test environment yet.
