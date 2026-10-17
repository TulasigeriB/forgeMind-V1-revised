# ForgeMind Learning and Build Reference

## Milestone 0 — Planning

### What was done

Defined a narrow initial workflow from RFQ/project creation through secure file upload, deterministic STEP extraction, engineer review, transparent should-costing, and revision-controlled quotation.

### Why

A narrow vertical slice is easier to validate commercially and technically than a broad dashboard with disconnected modules. CAD/drawing interpretation and costing can create expensive business errors, so provenance, explicit assumptions, and human review are foundational.

### Important concepts

- **Modular monolith:** one deployable backend with internal boundaries, simpler than microservices at this stage.
- **Provenance:** a value must point back to its source file, extraction method, version, and any human correction.
- **Immutable revision:** historical estimates and issued quotes must remain reproducible after future changes.
- **Deterministic costing:** identical inputs and calculation version should yield the same result.
- **Candidate feature:** geometry-derived suggestion that still may require engineering review.

### Files changed

Planning package only: README and initial documents under `docs/`.

### Commands/tests

No application commands or tests run; no code exists in this milestone.

### Decisions and open questions

See `DECISIONS.md`, `ARCHITECTURE.md`, and `PROJECT_STATUS.md`. Stack and MVP are proposals pending approval and dependency validation.

### Next steps

Get approval, then create the application skeleton and verify the first database migration, health endpoints, logging, and baseline tests in Milestone 1.
