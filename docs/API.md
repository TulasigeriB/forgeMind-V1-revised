# API Specification

Base path: `/api/v1`.

JWT authentication is required when `AUTH_DISABLED_FOR_TESTING` is false. Set it to `true` only for isolated local testing.

## Customer-to-quotation workflow

| Step | Method | Endpoint | Notes |
| --- | --- | --- | --- |
| Create customer | `POST` | `/customers` | Duplicate email returns `409`. |
| Find customer | `GET` | `/customers/by-email?email=...` | Returns `404` when not found. |
| Create RFQ | `POST` | `/rfqs` | Includes order quantity and priority. |
| Create project | `POST` | `/projects` | Associates the project with an RFQ. |
| Upload drawing | `POST` | `/upload?project_id=...` | PDF only; unsupported file types return `415`. |
| List drawings | `GET` | `/projects/{project_id}/files` | Lists project drawings. |
| Read drawing | `GET` | `/files/{file_id}/content` | Serves the uploaded PDF for inspection. |
| Start analysis | `POST` | `/projects/{project_id}/analyze` | Queues extraction through Celery. |
| Get analysis state | `GET` | `/projects/{project_id}/analysis` | Returns analysis, engineer-review state, and route-review state. |
| Save analysis review | `PUT` | `/projects/{project_id}/analysis/review` | Every extracted target must be decided before approval. |
| Generate route | `POST` | `/projects/{project_id}/routes` | Requires engineer-approved analysis. |
| Review route | `PUT` | `/projects/{project_id}/routes/review` | Persists operation edits and approval or change requests. |
| Create quote | `POST` | `/projects/{project_id}/quote` | Requires approved analysis and route. |
| Get latest quote | `GET` | `/projects/{project_id}/quote` | Returns the persisted estimate. |

Additional endpoints include `GET /projects`, `GET /projects/{project_id}`, feature and operation listings, `POST /templates`, and `GET /health`.

## Analysis and quote contract

The analysis response contains `project_id`, `status`, nullable `analysis`, nullable `review`, `process_plan_status`, and nullable `route_review`. The analysis object includes `part_identifier`, `units`, `manufacturing_operations.turning`, `manufacturing_operations.milling`, `precision_fits`, `geometric_tolerances`, `form_features`, `critical_operations`, `inspection_checklist`, `quality_document_templates`, `metadata_and_notes`, and `review_flags`. Dimensions preserve their source callout, location, confidence, review requirement, and semantic source. Inferred feature roles remain marked for engineer confirmation.

The inspection checklist and FAI/PPAP structures are drafts only; they are not validated quality records or certification. Route planning for general features requires matching cost templates created through `POST /templates`; missing rates return `409` instead of an invented estimate. Quotes are estimates based on the approved route multiplied by the RFQ quantity. Material, labor, overhead, scrap, tax, and shipping are excluded unless included in route estimates. STEP analysis is not currently supported.
