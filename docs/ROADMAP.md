# Roadmap and Acceptance Gates

## Milestone 0 — Scope and architecture (planning finalized; awaiting approval)

Deliver: expanded MVP definition, personas/workflows, architecture, initial data model, dependency evaluation plan, STEP/PDF engineering strategy, rule-based process-planning scope, multi-currency costing requirements, security risks, test strategy, documentation skeleton, and decision log.

Gate: user explicitly approves the finalized plan. No application implementation is included in this milestone.

## Milestone 1 — Foundation

Deliver: repository skeleton, environment configuration, structured logging, PostgreSQL connection, first Alembic migration, health/readiness endpoints, test setup, frontend shell/navigation, and documentation updates.

Acceptance: clean setup from documented instructions; migration applies to an empty database; health checks distinguish service/database availability; baseline backend/frontend tests pass; no secrets committed.

## Milestone 2 — Customers, RFQs, projects, files

Deliver: CRUD APIs and UI, lifecycle validation, project relationships, secure file upload/download, metadata/versioning, audit/activity history.

Acceptance: integration tests cover validation, project-level authorization, upload type/size limits, versioning, and deletion/retention behavior.

## Milestone 3 — Analysis lifecycle and STEP extraction

Deliver: persisted analysis-run state machine and a narrow STEP geometry adapter for supported files.

Acceptance: known STEP fixtures produce expected units/bounds/volume/surface area within tolerances; invalid/unsupported files fail explicitly; repeat runs are traceable.

## Milestone 4 — Feature recognition and engineer review

Deliver: supported candidate features with source references and a review/correction/approval UI.

Acceptance: uncertain features remain candidates; corrections do not overwrite extraction provenance; reviewer and timestamps are recorded.

## Milestone 5 — 2D drawing extraction

Deliver: direct PDF text/vector extraction, structured dimensions/tolerances, and confidence/provenance records; OCR only if justified.

Acceptance: fixture suite documents extraction precision/recall and limitations; no dimension is silently assigned to a feature without evidence; engineer corrections are auditable.

## Milestone 6 — Process planning

Deliver: configurable rule-based operation candidates, sequencing/dependencies, machine/tooling/setup considerations.

Acceptance: rules are outside UI; recommendations include assumptions and are editable; infeasible/missing information is surfaced.

## Milestone 7 — Machining time and should-costing

Deliver: versioned deterministic cost engine and UI for rates/assumptions.

Acceptance: formula-level tests and reproducibility tests pass; missing required values produce incomplete estimates; no default values masquerade as verified shop rates.

## Milestone 8 — Quotations

Deliver: quote number, revisioning, approval states, immutable issued snapshots, PDF export.

Acceptance: quote references an exact estimate version; changes create a new revision; PDF matches persisted commercial data.

## Milestone 9 — Production feedback

Deliver: actual setup/cycle/material/cost/scrap/rework records and quoted-versus-actual comparison.

Acceptance: actuals link to project/part/operation/estimate as applicable; reports describe dataset size and limitations; no automatic-learning claim without evaluation.

## Milestone 10 — Hardening and release

Deliver: end-to-end tests, authorization review, resource limits, performance checks, deployment instructions, documentation audit.

Acceptance: documented critical workflows pass; security findings are triaged; restore/migration procedures are verified.

## Milestone 11 — CAM/NC feasibility (separate approval)

Deliver only after separate scope and validation plan: controller/machine-specific integration, simulation and qualified review workflow.

Acceptance: never generate production-ready code from guessed parameters; validated machine configuration, tooling, work coordinates, parameters, simulation, and approval are prerequisites.

## Priority order

P0: foundation, records/files, access control, traceable STEP analysis, engineer review, deterministic multi-currency costing, quotation snapshots.
P1 within the expanded MVP: supported PDF extraction/review, configurable process rules, production-feedback capture, and evaluation fixtures.
P2/future: advanced feature recognition, measured estimation improvements, cloud deployment hardening, and separately approved CAM/NC feasibility.


## Extraction engine initial slice

The first implementation supports text-based PDF, DOCX, and XLSX ingestion, source-linked candidate fields, and explicit human review. OCR, drawing understanding, and automatic conversion into RFQs/quotations are subsequent capabilities.
