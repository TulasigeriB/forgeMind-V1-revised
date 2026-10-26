from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import projects, files

app = FastAPI(title=settings.PROJECT_NAME, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix=settings.API_V1_STR, tags=["Projects"])
app.include_router(files.router, prefix=settings.API_V1_STR, tags=["Files"])

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}
