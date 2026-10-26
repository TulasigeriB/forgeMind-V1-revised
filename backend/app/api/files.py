from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.engineering_file import EngineeringFile
from app.models.project import Project
from app.schemas.file import EngineeringFile as FileSchema
from app.core.security import get_current_user
from app.core.config import settings
from app.services.drawing_intelligence import DrawingIntelligenceService
import os
import uuid
from pathlib import Path
from uuid import UUID

router = APIRouter()
UPLOAD_DIR = Path(settings.UPLOAD_DIR).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload", response_model=FileSchema)
async def upload_file(project_id: UUID, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext != ".pdf":
        raise HTTPException(
            status_code=415,
            detail="Only PDF drawings are currently supported for analysis. STEP support is planned.",
        )
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    file_id = str(uuid.uuid4())
    filename = f"{file_id}{ext}"
    filepath = UPLOAD_DIR / filename
    try:
        with filepath.open("wb") as buffer:
            buffer.write(await file.read())

        db_file = EngineeringFile(project_id=project_id, file_type="PDF", storage_path=str(filepath), status="uploaded")
        db.add(db_file)
        project.status = "uploaded"
        db.commit()
        db.refresh(db_file)
    except Exception:
        db.rollback()
        filepath.unlink(missing_ok=True)
        raise
    return db_file


@router.get("/projects/{project_id}/files", response_model=list[FileSchema])
def list_project_files(project_id: UUID, db: Session = Depends(get_db)):
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(EngineeringFile).filter(
        EngineeringFile.project_id == project_id
    ).order_by(EngineeringFile.created_at).all()


@router.get("/files/{file_id}/content")
def get_file_content(file_id: UUID, db: Session = Depends(get_db)):
    engineering_file = db.get(EngineeringFile, file_id)
    if engineering_file is None:
        raise HTTPException(status_code=404, detail="Drawing file not found")
    try:
        path = DrawingIntelligenceService._resolve_storage_path(engineering_file.storage_path)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Stored drawing file was not found") from error
    return FileResponse(path, media_type="application/pdf", filename=path.name)
