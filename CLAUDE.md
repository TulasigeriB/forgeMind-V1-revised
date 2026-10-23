# ForgeMind Development Guide

## Project Overview
CNC Job Shop Quoting System. Modular Monolith.
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL, Alembic.
- **Frontend**: React, Vite, Tailwind CSS.

## Technical Standards
- **Naming**: 
    - Variables/Functions: `snake_case`
    - Classes: `PascalCase`
    - API Endpoints: `kebab-case` or `snake_case` (consistent)
- **Backend Patterns**:
    - Use Pydantic schemas for all request/response bodies.
    - Keep business logic in `services/` and DB access in `db/` or `models/`.
    - Use Alembic for all schema changes.
- **Frontend Patterns**:
    - Functional components with Hooks.
    - Tailwind for all styling.
    - Centralized API client in `services/`.

## Build & Run Commands
- **Backend**: `pip install -r backend/requirements.txt` $\rightarrow$ `uvicorn backend.app.main:app --reload`
- **DB**: `docker compose up -d`
- **Migrations**: `alembic upgrade head`
