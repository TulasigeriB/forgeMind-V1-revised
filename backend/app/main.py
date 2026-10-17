from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.auth import router as auth_router
from app.api.customers import router as customers_router
from app.api.health import router as health_router
from app.api.rfqs import router as rfqs_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("forgemind.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("application_start", extra={"environment": settings.app_env})
    yield
    logger.info("application_stop")


app = FastAPI(
    title="ForgeMind API",
    version="0.2.0",
    description="Manufacturing intelligence platform API. Engineering results remain subject to validation and review.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(rfqs_router)
