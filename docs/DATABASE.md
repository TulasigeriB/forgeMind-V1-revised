# Database Outline (Proposed)

## Core entities and relationships

- `users`: identity, active state, timestamps.
- `roles` / `user_roles`: role assignments; exact permission model to be finalized before exposing records.
- `customers`: business/contact details and status.
- `rfqs`: customer FK, external reference, received/due dates, status, notes.
- `projects`: customer FK, optional RFQ FK, project code, status, dates, notes.
- `parts`: project FK, part number/name/description, quantity, material/specification, required delivery date.
- `engineering_files`: project FK and optional part FK; logical file identity, original filename, media type, size, checksum, storage key, uploader, retention/deletion state.
- `engineering_file_versions`: file FK, immutable version number, storage key/checksum/size, uploaded timestamp, validation result.
- `analysis_runs`: file-version FK, analysis type, pipeline/software version, status, timestamps, warnings/error code, structured result reference/payload.
- `engineering_observations`: analysis-run FK, observation type/value/unit, source entity/reference, provenance, confidence/limitations where applicable.
- `engineering_reviews`: analysis-run FK, reviewer FK, status, notes, reviewed timestamp.
- `engineering_corrections`: observation FK, original value preserved, corrected value/unit, reason, author, approval state.
- `manufacturing_rate_sets`: named/versioned set of company-configured rates and effective dates, with currency metadata for monetary rates.
- `exchange_rate_snapshots` (proposed): source/target ISO currency codes, rate, source/provider or manual entry, effective timestamp, retrieval/approval metadata, and immutable reference used by an estimate/quotation.
- `process_plans`: part/project FK, revision, status, source analysis/review reference.
- `process_operations`: plan FK, sequence/dependencies, operation type, machine/tooling/setup assumptions, estimated times.
- `cost_estimates`: part/project FK, revision, costing-engine version, rate-set FK, status, currency, inputs/assumptions, totals, created by.
- `cost_lines`: estimate FK, category, quantity, unit, rate, formula/version, amount, provenance.
- `quotations`: project/RFQ/customer references, quote number, revision, state, validity, commercial terms, exact estimate FK/version, immutable issued snapshot.
- `production_feedback`: project/part/operation/quote or estimate links where applicable, actual times/material/cost/scrap/rework, recorder and timestamps.
- `activity_events`: actor, object type/id, action, timestamp, safe metadata.

## Integrity and indexing

Use foreign keys for ownership and provenance. Unique constraints: customer-scoped/project codes where agreed; `(engineering_file_id, version_number)`; `(quotation_number, revision)`; estimate revision within its defined scope. Index foreign keys, status/date queries, checksums, and commonly filtered project/customer IDs. Add check constraints for nonnegative quantities/times/cost inputs where domain-appropriate.

## Design cautions

- Do not put raw file bytes in relational tables by default; store private storage keys and checksums.
- Store normalized numeric values with explicit units; preserve original displayed values where relevant.
- Store currency as an ISO 4217 code on each monetary record/line; do not treat currency symbols as unique identifiers.
- Link converted estimates to an immutable exchange-rate snapshot or explicitly recorded manual conversion assumption.
- JSON may hold versioned calculation inputs/results, but queryable lifecycle and relationships remain relational.
- Immutable versions are required for source files, analysis results, estimates, and issued quotations.
- Avoid premature tenant abstractions until company/user ownership requirements are confirmed; authorization must still be designed before sensitive endpoints are exposed.

## Migration workflow

Create migrations with Alembic, review generated DDL, apply against a clean development database, and test upgrade paths. Never rely on automatic schema creation in production. Backup and rollback strategy must be documented before release.
