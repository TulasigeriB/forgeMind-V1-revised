# Project Status

**As of:** 2026-10-14  
**Phase:** Milestone 0 — planning  
**Implementation status:** Not started; this package is documentation only.

## Verified completed

- Reviewed the supplied ForgeMind greenfield specification.
- Defined a proposed MVP boundary and milestone gates in this planning pack.
- Drafted initial architecture, data model, engineering-analysis, costing, security, and testing plans.

## Not implemented

- No application repository/code has been created by this artifact.
- No dependencies installed or compatibility tests run.
- No database or migrations created/applied.
- No API, UI, file storage, CAD/drawing processing, costing engine, or quotation generation implemented.
- No automated tests run.

## Confirmed planning decisions

- MVP scope: expanded first release; include the connected RFQ-to-quotation workflow, initial PDF drawing extraction/review, configurable rule-based process planning, and production-feedback data capture. Advanced CAM/NC generation remains excluded.
- Initial deployment: local development first.
- Authentication: application-managed authentication and roles, subject to security review before sensitive endpoints are exposed.
- Costing: multi-currency support is required in the design and MVP; exchange-rate behavior and commercial currency rules remain open.
- Greenfield implementation and modular monolith remain the baseline.

## Remaining open decisions before/during implementation

1. Supported development OS and exact Python/Node/PostgreSQL versions.
2. CAD kernel binding selection after a compatibility, STEP-fixture, packaging, and licensing spike.
3. Frontend component/styling system and frontend unit-test runner.
4. Company tenancy model and exact role/permission matrix.
5. Maximum upload sizes, retention/deletion policy, and local-storage interface details.
6. Supported currencies, quote currency versus cost-base currency, exchange-rate source/update policy, manual overrides, and whether historical rates are snapshotted per estimate.
7. Tax jurisdictions and whether tax is configured per customer/project/quote; tax-inclusive versus tax-exclusive display.
8. Currency precision, rounding mode, rounding stage, and margin/markup order of operations.
9. Minimum viable PDF fixture set and objective extraction evaluation thresholds.
10. Which process-planning rules and feedback fields are mandatory in the first expanded release.

## Immediate next step

Present this finalized Phase 0 plan for explicit user approval. Do not begin Milestone 1 until approval is given. Do not represent any planned feature as implemented.

## User-selected configuration

- Scope: expanded MVP.
- Deployment: local development first.
- Authentication: built-in/application-managed.
- Costing: multi-currency.

**Approval status:** Awaiting explicit approval of the finalized Phase 0 plan. Milestone 1 has not started.
