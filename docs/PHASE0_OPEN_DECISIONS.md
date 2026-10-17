# Phase 0 — Open Decision Register

These items do not block documenting the plan, but must be resolved before the affected behavior is implemented or exposed.

| ID | Decision | Proposed handling | Needed by |
|---|---|---|---|
| OD-01 | Supported OS and exact Python/Node/PostgreSQL versions | Select one reproducible local development baseline | Milestone 1 |
| OD-02 | CAD kernel binding and license | Compare candidate bindings using representative STEP fixtures and packaging tests | Milestone 3 |
| OD-03 | Frontend component system and test runner | Choose a maintained, accessible system with minimal dependencies | Milestone 1 |
| OD-04 | Company tenancy and permission matrix | Decide single-company versus multi-company data ownership; define roles and project access | Before protected APIs |
| OD-05 | Authentication/session implementation | Select secure password hashing, session/token lifecycle, reset and recovery behavior | Milestone 1 |
| OD-06 | Upload limits and retention | Set per-file/request limits, deletion semantics, retention period, and local storage layout | Milestone 2 |
| OD-07 | Supported currencies and base currency | Define ISO currency allowlist and whether a company base currency is mandatory | Milestone 7 |
| OD-08 | FX source and rate policy | Decide provider/source, update cadence, manual overrides, approval, and stale-rate handling | Milestone 7 |
| OD-09 | Conversion snapshot semantics | Preserve the exact conversion rate and source metadata used by each estimate/quote | Milestone 7 |
| OD-10 | Tax behavior | Define jurisdiction, tax-inclusive/exclusive behavior, and customer/project/quote-level configuration | Milestone 7–8 |
| OD-11 | Currency precision and rounding | Specify decimal precision, rounding mode, calculation stage, and display behavior | Milestone 7 |
| OD-12 | Margin/markup policy | Define whether margin/markup is applied per line or at subtotal and its ordering relative to overhead/tax | Milestone 7 |
| OD-13 | PDF extraction acceptance threshold | Establish representative fixtures and measurable extraction criteria before claiming capability | Milestone 5 |
| OD-14 | Process-planning rule coverage | Select initial operation candidates and required inputs by supported part/material/machine scenarios | Milestone 6 |
| OD-15 | Feedback capture scope | Confirm mandatory actuals and who can record/approve them | Milestone 9 |

## Guardrails pending decisions

- Do not silently convert currencies or use unrecorded exchange rates.
- Do not treat extracted PDF dimensions as authoritative without source linkage and engineering review.
- Do not expose sensitive records/files until authentication and authorization are implemented and tested.
- Do not claim CAD/PDF coverage beyond validated fixtures.
