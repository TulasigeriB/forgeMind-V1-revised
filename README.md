# ForgeMind

ForgeMind is a manufacturing intelligence platform for CNC/VMC businesses. It is designed to connect RFQs and engineering files to reviewed engineering records, reproducible multi-currency cost estimates, and revision-controlled quotations.

## Current state

**Milestone 1 — foundation in progress.** The repository skeleton, FastAPI application, database models and initial Alembic migration, liveness/readiness endpoints, structured logging, React/Vite navigation shell, and focused tests are present. See `docs/PROJECT_STATUS.md` for verified results and environment blockers. No customer, CAD, costing, quotation, or authentication workflow is implemented yet.

## Stack and local baseline

- Python 3.13 (supported range in project metadata: `>=3.12,<3.14`)
- Node.js 22
- React 19, TypeScript 5.8, Vite 7
- FastAPI, Pydantic 2, SQLAlchemy 2, Alembic
- PostgreSQL 17 via Docker Compose
- Pytest for API tests; Vitest and Testing Library for frontend tests

Exact installed frontend versions and lockfile are not yet verified because package installation could not reach the package registry in the build environment. Run `npm install` from `frontend/` in a network-enabled environment and retain the generated `package-lock.json` for reproducible installs. No Git commit has been created.

## Prerequisites

- Python 3.12 or 3.13
- Node.js 22 and npm
- Docker Compose v2 with the ability to pull PostgreSQL 17, or a local PostgreSQL 17 instance
- Network access to install Python and npm dependencies on first setup

## Setup

1. Copy `.env.example` to `.env`; replace the local database password if desired. The example credentials are for local development only.
2. Start PostgreSQL: `docker compose up -d postgres`.
3. Create a backend virtual environment and install dependencies:

   ```bash
   cd backend
   python -m venv .venv
   # Linux/macOS
   . .venv/bin/activate
   python -m pip install -r requirements.txt
   ```

4. Export `DATABASE_URL` from the root `.env` (or set it directly in your shell). The backend intentionally does not auto-load `.env` files.
5. Apply the database migration:

   ```bash
   cd backend
   alembic upgrade head
   ```

6. Start the API from `backend/`: `uvicorn app.main:app --reload --port 8000`.
7. In a second terminal, set up and start the frontend:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

8. Visit `http://127.0.0.1:5173`. API liveness: `http://127.0.0.1:8000/health`; database readiness: `http://127.0.0.1:8000/ready`; OpenAPI docs: `http://127.0.0.1:8000/docs`.

## Tests

- Backend: `cd backend && python -m pytest -q`
- Migration smoke test against disposable SQLite: `cd backend && DATABASE_URL=sqlite:////tmp/forgemind-migration-test.db alembic upgrade head`
- Frontend: `cd frontend && npm test`
- Frontend production build: `cd frontend && npm run build`

SQLite migration smoke tests validate basic migration structure only; they do **not** replace a PostgreSQL migration/integration test. Do not expose the application or uploaded files to a network until authentication and authorization are implemented and tested.

## Architecture and boundaries

Start with a modular monolith. PostgreSQL is the application record source of truth; file bytes will be held behind a private storage abstraction. Keep API, application services, domain rules, engineering adapters, manufacturing rules, costing, persistence, storage, and authentication concerns separate. See `docs/ARCHITECTURE.md`.

## Security notes

- Never commit `.env`, credentials, customer documents, or proprietary CAD files.
- Current frontend is a navigation shell; the avatar is not a login feature.
- Authentication, role enforcement, upload limits, file authorization, and audit integration are not yet implemented. Do not treat the current build as production-ready.
- Health responses intentionally avoid exposing database URLs or raw driver exceptions.

## Documentation

- `docs/PRODUCT_SPECIFICATION.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/PROJECT_STATUS.md`
- `docs/DATABASE.md`
- `docs/API.md`
- `docs/ENGINEERING_ANALYSIS.md`
- `docs/COSTING_RULES.md`
- `docs/TESTING.md`
- `docs/ForgeMind_Learning_and_Build_Reference.md`
- `docs/DECISIONS.md`
- `docs/PHASE0_OPEN_DECISIONS.md`
