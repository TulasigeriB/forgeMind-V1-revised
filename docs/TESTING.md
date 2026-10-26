# Testing Strategy

## Core workflow acceptance test

The isolated end-to-end test creates a customer, RFQ, and project; uploads a generated searchable PDF; runs the analysis worker; accepts all extraction targets; approves the manufacturing route; and verifies the persisted quantity-based quote.

Run it from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest .\backend\tests\test_workflow_e2e.py -q
```

From the `backend` directory, run the full suite with:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The virtual environment is under `backend\.venv`; the root-level command `.\.venv\Scripts\python.exe` will not work unless you created a separate environment at the repository root.

The test uses a temporary SQLite database and upload directory. It does not require PostgreSQL, Redis, or a running Celery worker.

Run the focused extraction and review suite:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest .\backend\tests\test_drawing_intelligence.py .\backend\tests\test_analysis_review.py -q
```

## Current capability boundary

PDF is the supported drawing input. STEP analysis remains planned and must not be treated as validated. Use searchable PDFs in automated tests; OCR requires a separately installed and configured Tesseract executable.
