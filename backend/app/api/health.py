from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.db.session import get_engine

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness check")
def health():
    return {"status": "ok", "service": "forgemind-api"}


@router.get("/ready", summary="Readiness check")
def readiness():
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        # Deliberately do not expose DSNs or low-level driver/database errors.
        raise HTTPException(status_code=503, detail={"status": "not_ready", "dependency": "database"}) from exc
    return {"status": "ready", "database": "ok"}
