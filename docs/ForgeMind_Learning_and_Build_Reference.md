# Learning and Build Reference
Milestone 0 established a "Correctness First" mindset.

## Regression-testing milestone — 2026-10-29

### Scope
Compared the supplied source archive and feature implementation audit. This milestone adds regression coverage for project/file deletion, review persistence, quotation arithmetic, and auth-required API boundaries; fixes cross-platform legacy drawing path resolution; and makes the auth bypass opt-in rather than the default.

### Changes prepared
- `backend/app/core/config.py`: `AUTH_DISABLED_FOR_TESTING` now defaults to `False`.
- `backend/app/api/projects.py` and `backend/app/api/files.py`: apply `get_current_user` at router level so data endpoints cannot accidentally omit the authentication dependency.
- `backend/app/api/projects.py`: project deletion removes referenced physical drawing files as well as cascade-deleting related database records.
- `backend/app/services/drawing_intelligence.py`: normalizes Windows path separators when resolving persisted relative drawing paths.
- `backend/tests/test_api.py`: explicitly opts legacy behavior tests into the auth bypass, adds missing-token route coverage, analysis-review persistence/source immutability coverage, and project/file deletion coverage.
- `backend/tests/test_workflow_e2e.py`: explicitly opts workflow tests into test mode and checks quote cost/time totals against saved breakdowns and quantity.

### Commands and observed results
- `python -m compileall -q backend/app backend/tests` — passed.
- `python -m pytest -q tests/test_analysis_review.py tests/test_feature_normalizer.py tests/test_drawing_intelligence.py` — 14 passed after fixing a pre-existing cross-platform path test failure.
- `python -m pytest -q` — blocked during test collection because `psycopg` is not installed in the execution environment. Attempting to install it failed because package-index DNS/network access was unavailable.
- `DATABASE_URL='sqlite:////tmp/forgemind-test-import.db' python -m pytest -q tests/test_workflow_e2e.py` — blocked during collection because `celery` is not installed.

### Important unresolved security limitation
JWT validation currently verifies a signed token subject, but the repository has no persistent user model or project/customer ownership fields. Router-level authentication rejects missing/invalid tokens when the bypass is off, but it does **not** provide per-user resource isolation. Do not claim that cross-user authorization is complete until account persistence, ownership/organization relationships, and ownership checks are implemented and tested.

### Verification status
The modified API and end-to-end tests were syntax-checked but could not be executed in this environment due to missing runtime dependencies. Do not mark those regression tests as passing until run in the project's configured backend environment with the test database available.

### Next actions
1. Install project dependencies in the intended virtual environment and confirm the configured PostgreSQL test database is reachable.
2. Run the full backend suite; fix failures without weakening assertions.
3. Verify the test database is isolated and that test fixtures clean up database state and temporary files.
4. Implement a user/account ownership model before claiming per-user authorization.
5. Commit the changes and record the resulting Git commit hash after local verification.

Analysis-response schema regression fixed.
Targeted test: 1 passed.
Full backend suite: 37 passed, 0 failed.
Two deprecation warnings.
Frontend build result, once verified.
Remaining regression coverage and security limitations.