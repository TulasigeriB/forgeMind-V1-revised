# Decision Log

## D-001 — Greenfield implementation

**Status:** Accepted from project brief.  
**Decision:** Treat ForgeMind as a new application; do not depend on any prior project implementation.  
**Rationale:** Keeps the baseline explicit and reproducible.

## D-002 — Modular monolith first

**Status:** Proposed.  
**Decision:** Begin with a modular monolith rather than microservices.  
**Rationale:** Fewer operational dependencies and clearer end-to-end ownership while the domain is being validated. Split services only when measured needs justify it.

## D-003 — Deterministic costing with explicit inputs

**Status:** Proposed.  
**Decision:** Store formulas, inputs, units, assumptions, calculation version, and outputs for each estimate. Missing inputs produce incomplete estimates.  
**Rationale:** Cost decisions must be explainable and reproducible; guessed rates are unacceptable.

## D-004 — Human review for uncertain engineering results

**Status:** Proposed.  
**Decision:** Keep extracted, corrected, and approved engineering values distinct.  
**Rationale:** Geometry/drawing ambiguity must not be hidden behind automation.

## D-005 — STEP/PDF only for initial file scope

**Status:** Proposed.  
**Decision:** Validate STEP/STP and PDF upload paths before adding more formats.  
**Rationale:** Every advertised format needs a tested processing path.

## D-006 — CAD dependency selection requires a technical spike

**Status:** Open.  
**Decision:** Evaluate Open CASCADE Python bindings and alternatives against deployment compatibility, STEP fixtures, packaging, and licensing before locking the dependency.  
**Rationale:** Native CAD bindings can have significant platform and packaging constraints.

## D-007 — Issued quotations are immutable snapshots

**Status:** Proposed.  
**Decision:** Estimate changes create new estimate/quotation revisions rather than silently changing an issued quote.  
**Rationale:** Commercial records require traceability.


## D-008 — Expanded MVP scope

**Status:** Accepted for planning.
**Decision:** The first release targets a connected RFQ-to-quotation workflow and includes initial PDF drawing extraction/review, configurable rule-based process planning, and production-feedback capture alongside core records, STEP analysis, costing, and quotation revisioning. Advanced CAM/NC generation remains out of scope.
**Rationale:** The user selected an expanded first release while retaining a staged, testable implementation.

## D-009 — Local development first

**Status:** Accepted for planning.
**Decision:** Optimize the first setup for reproducible local development; keep storage and configuration boundaries compatible with a later deployment adapter.
**Rationale:** Validate the workflow before introducing cloud operations.

## D-010 — Application-managed authentication

**Status:** Accepted for planning; implementation details open.
**Decision:** Plan for built-in authentication and role-based authorization. Final password/session/token handling and role permissions must be reviewed before sensitive records are exposed.
**Rationale:** Keeps the initial deployment self-contained without waiving security requirements.

## D-011 — Multi-currency costing

**Status:** Accepted for planning; commercial rules open.
**Decision:** Model currency explicitly in estimates, cost lines, rate sets, and quotations. Preserve currency and conversion assumptions/rate snapshots so historical estimates remain reproducible. Do not convert using an unrecorded or silently changing rate.
**Rationale:** Cross-currency comparisons must be auditable and historical values stable.
