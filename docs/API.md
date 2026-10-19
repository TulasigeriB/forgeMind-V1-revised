# API

Local base URL: `http://127.0.0.1:8000`. Interactive docs: `/docs`.

## Health

- `GET /health`: liveness.
- `GET /ready`: dependency readiness.

## Authentication

- `POST /auth/register`: create organization and initial owner. Password 12–128 chars; default currency is a three-letter uppercase code. Open registration is local-development only.
- `POST /auth/login`: email/password login; returns a one-hour bearer token.
- `GET /auth/me`: current profile, requires bearer token.

Frontend token is stored in `sessionStorage`, cleared on logout and on authenticated 401 responses. Do not expose this development app publicly; token storage is not a substitute for production identity/security controls.

## Customers

All customer endpoints require a bearer token and constrain access to the authenticated user's organization.

- `GET /customers?limit=50&offset=0`
- `POST /customers`
- `GET /customers/{customer_id}`
- `PATCH /customers/{customer_id}`
- `DELETE /customers/{customer_id}`

Customer fields: `name` (required), `contact_name`, `email`, `phone`, `address`, and `notes`. Customer names are unique per organization. Duplicate names return 409. Cross-organization records return 404.

## Frontend

Set `VITE_API_BASE_URL` in `frontend/.env.local` if needed. Default is `http://127.0.0.1:8000`. The API's default CORS origins include Vite on both localhost and loopback.

## RFQ management

All RFQ endpoints require a bearer token and are scoped to the authenticated organization. Each RFQ must reference a customer belonging to that same organization.

- `GET /rfqs?status=Received&limit=100&offset=0` — list RFQs, optionally filtered by status.
- `POST /rfqs` — create an RFQ.
- `GET /rfqs/{rfq_id}` — retrieve one RFQ.
- `PATCH /rfqs/{rfq_id}` — update an RFQ.
- `DELETE /rfqs/{rfq_id}` — delete an RFQ.

Fields: `customer_id`, `reference`, `title`, `quantity` are required; `description`, `due_date`, `status`, and `notes` are optional. Status values: `Draft`, `Received`, `Quoting`, `Submitted`, `Won`, `Lost`, `Cancelled`. Reference numbers are unique per organization. Migration `0003_rfqs` adds RFQ persistence. Customers linked to RFQs cannot be deleted until their RFQs are removed.

## Quotations and costing (Milestone 3)

- `GET /quotations` — list quotations belonging to the authenticated organization.
- `POST /quotations` — create a quotation linked to an organization-owned RFQ.
- `GET /quotations/{id}` — retrieve one organization-owned quotation.
- `PATCH /quotations/{id}` — update a quotation and recalculate cost and margin.
- `DELETE /quotations/{id}` — delete a quotation.

Quotation payloads contain `rfq_id`, `reference`, `revision`, `currency` (`INR`, `USD`, `EUR`, `GBP`), `status`, optional `valid_until`, `notes`, and one or more `line_items`. Each line item contains description, quantity, unit, material/labor/overhead unit costs, and unit selling price. The API calculates totals using decimal arithmetic and rounds currency amounts to two decimal places. Gross margin is `(selling price - total cost) / selling price * 100`; it is zero when selling price is zero. Reference and revision must be unique within an organization. Every record is organization-scoped and audit events are recorded.

Cost snapshots are persisted on each quotation revision. Creating a new revision should use a new revision number; the API does not silently generate revisions automatically. The current UI exposes one line item per quotation; the API supports multiple line items.

## Extraction engine

- `GET /extractions` — list uploaded extraction records for the signed-in organization.
- `POST /extractions` — multipart upload using field `file`; accepts PDF, DOCX, and XLSX up to 10 MB. Returns extracted text, source locations, candidate fields, warnings, and `needs_review` status.
- `GET /extractions/{document_id}` — fetch a source-linked extraction record within the current organization.
- `PATCH /extractions/{document_id}/review` — submit edited field values and per-field decisions (`needs_review`, `approved`, or `rejected`). The document becomes `reviewed` when every detected field has an explicit decision.
- `DELETE /extractions/{document_id}` — delete the document and its extracted data.

The initial extraction implementation is deterministic and label-based; it does not use an LLM or OCR. Supported candidate labels include part number, material, dimensions, tolerance, quantity, finish, and delivery requirement. Source references identify PDF pages, DOCX paragraphs/tables, or XLSX sheets/rows. Uploaded originals are stored in the database and isolated by organization. The upload limit is 10 MB, extracted text is capped at 2 million characters, and Office archive expansion is bounded. Scanned PDFs, CAD/drawing interpretation, automatic RFQ creation, and direct costing integration are not enabled in this milestone.
