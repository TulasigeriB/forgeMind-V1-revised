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
