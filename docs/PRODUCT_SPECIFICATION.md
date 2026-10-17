# Product Specification (Phase 0)

## Product goals

- Reduce repetitive RFQ-to-quotation work for CNC/VMC manufacturers.
- Make engineering interpretations reviewable and linked to their source files.
- Make cost estimates reproducible from recorded inputs, formulas, and versioned rules.
- Preserve quoted-versus-actual feedback for future evaluation.

## Primary personas

1. **Estimator / sales engineer** — creates RFQs and projects, gathers requirements, prepares quotations, and tracks status.
2. **Manufacturing engineer** — reviews geometry/drawing interpretations and defines feasible operation plans and assumptions.
3. **Costing / production manager** — configures rates, reviews estimates and commercial margins, approves quotations, and compares actuals.
4. **Administrator** — manages users, roles, company settings, retention, and access.

## Primary workflow

Customer/RFQ → Project/part → Secure file upload → Analysis run → Engineer review → Process plan and explicit assumptions → Versioned cost estimate → Quotation review/issue → Acceptance/rejection → Production feedback.

## Expanded MVP functional requirements

- Customer, RFQ, project, part, quantity, material requirement, due date, notes, and status records.
- Upload and version STEP/STP and PDF files with size/type checks and private access.
- Persist analysis runs and their status; record errors and supported extracted geometry properties.
- Preserve source file/version, units, extraction method, software version, and entity references where available.
- Initial 2D PDF text/vector extraction, dimension/tolerance parsing where supported, uncertainty reporting, and engineer correction/approval. OCR is fallback-only when direct extraction is insufficient.
- Keep extracted, corrected, and approved values distinct; do not silently associate a dimension with a feature.
- Configurable rule-based process-plan candidates, sequencing/dependencies, and explicit setup, machine, tooling, and material assumptions.
- Capture process operations, setup/cycle-time assumptions, material and machine rates, labor, tooling, outside processing, inspection, overhead, scrap/risk, margin, and taxes as applicable.
- Multi-currency estimate and quotation data with recorded currency and any conversion-rate/source/timestamp assumptions. Exact conversion policy remains an open decision.
- Calculate estimates deterministically; save formula/version, inputs, units, assumptions, and outputs. Missing required values produce an incomplete estimate.
- Create revision-controlled quotations from reviewed estimates; issued quotations are immutable snapshots.
- Capture production feedback (actual setup/cycle time, material usage, scrap/rework, and actual cost) for traceability and later measured evaluation. No automatic-learning claims.
- Record project activity and important state transitions.

## Nonfunctional requirements

- No public-by-default engineering file access.
- Traceability for analysis, estimate, and quotation versions.
- Consistent validation and error responses.
- Explicit units and conversion rules; no silent unit assumptions.
- Useful logs without document contents or secrets.
- Responsive, accessible UI with real loading, empty, validation, and error states.
- Modular monolith first; no microservices without measured justification.

## Explicit exclusions from MVP

- Guaranteed interpretation of all drawings or all STEP variants.
- Unreviewed automatic dimension-to-feature association as authoritative data.
- Invented material pricing, feeds/speeds, cycle times, exchange rates, or machine rates.
- Automatic model training or claims of self-learning.
- Production-ready G-code generation, autonomous CAM, or machine-ready NC programs.
- Non-STEP/PDF file types before their processing paths are tested.
- Automatic live currency conversion without a documented, auditable rate policy.

## Acceptance criteria for MVP

- A user can create an RFQ/project/part and upload a validated STEP file and PDF drawing.
- Files are private and access is checked against project permissions.
- A supported STEP fixture produces deterministic geometry properties within documented tolerances; unsupported or invalid files yield explicit failure states.
- An engineer can review and approve/correct analysis records while retaining the original extracted values.
- An estimate cannot be marked complete if required inputs are missing; missing inputs are named.
- The same saved inputs and costing version reproduce the same result.
- A quotation references an exact estimate version and subsequent estimate changes do not mutate an issued quotation.
- Automated tests cover core validation, authorization, analysis lifecycle, costing, and quotation versioning.
- Setup, migrations, test commands, limitations, and known gaps are documented.
