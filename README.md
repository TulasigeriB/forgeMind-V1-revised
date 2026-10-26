# ForgeMind
Manufacturing intelligence platform for CNC/VMC businesses.

## Apply database migrations

From the repository root, run the Alembic upgrade after pulling schema changes:

```powershell
.\backend\.venv\Scripts\alembic.exe upgrade head
```

## Local testing without authentication

For local testing only, set `AUTH_DISABLED_FOR_TESTING=true` in the backend environment before starting or restarting the API. For example, from the `backend` directory in PowerShell:

```powershell
$env:AUTH_DISABLED_FOR_TESTING = "true"
uvicorn app.main:app --reload
```

Authentication remains enabled by default. Remove the environment variable or set it to `false` and restart the API to restore authentication. Do not enable this setting in a shared or production environment.
