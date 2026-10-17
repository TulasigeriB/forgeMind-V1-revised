# Project Status

**As of:** 2026-10-16  
**Current milestone:** Milestone 2 — Authentication and customer workflow  
**Git commits:** None created.

## Verified by the user

- Milestone 1 backend tests passed (4 tests).
- Milestone 1 frontend tests passed (2 tests).
- Frontend production build succeeded.
- PostgreSQL migrations `0001_foundation` and `0002_customers` applied; `alembic current` reported `0002_customers (head)`.
- `alembic check` reported no new upgrade operations.
- `/ready` returned `{"status":"ready","database":"ok"}`.
- After adding the first backend business slice, the user reported 8 backend tests passed on Windows/PostgreSQL.

## Implemented in the current source package (new frontend slice; local verification pending)

- Login and organization registration UI.
- Session-scoped bearer token storage.
- API client with typed auth/customer interfaces and readable API errors.
- Authenticated current-user bootstrap and logout.
- Customer list, create, edit, delete, loading, error, and empty states.
- Default CORS origins include both `localhost:5173` and `127.0.0.1:5173`.
- Frontend tests cover auth mode, login/customer listing, and customer creation.
- `frontend/.env.example` documents `VITE_API_BASE_URL`.

## Backend implementation already present

- PBKDF2-HMAC-SHA256 password hashing.
- HMAC-signed one-hour bearer tokens.
- Organization registration, login, and `/auth/me`.
- Organization-scoped customer CRUD and audit events.
- Customer migration `0002_customers`.
- Organization-scoped RFQ CRUD, customer linkage, status workflow, and audit events.
- RFQ migration `0003_rfqs`; backend RFQ isolation/CRUD test added.

## Remaining work

- Run updated frontend tests and production build on the user's machine.
- Run backend tests after merging/replacing with this source package.
- Verify actual browser-to-API CORS requests.
- Restrict open organization registration before any public deployment.
- Add rate limiting, password recovery, email verification, token revocation, and production secret management before production use.
- Implement project management and connect RFQs to downstream engineering, costing, and quotations.
- Secure engineering file storage and upload handling remains later work.

## Local run

Backend from `backend/`:

```powershell
python -m pytest -q
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend from `frontend/`:

```powershell
npm test
npm run build
npm run dev
```

Configure `VITE_API_BASE_URL` if the API is not at `http://127.0.0.1:8000`.
