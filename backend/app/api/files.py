import logging
import os
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.engineering_file import EngineeringFile
from app.models.project import Project
from app.schemas.file import EngineeringFile as FileSchema
from app.schemas.analysis import DrawingAnalysis
from app.core.security import get_current_user
from app.core.config import settings
from app.services.drawing_intelligence import DrawingIntelligenceService
from app.services.feature_normalizer import FeatureNormalizer
from app.services.route_service import ManufacturingRouteService

router = APIRouter(dependencies=[Depends(get_current_user)])
UPLOAD_DIR = Path(settings.UPLOAD_DIR).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger(__name__)
MAX_DRAWING_SIZE_BYTES = 25 * 1024 * 1024

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


@router.post("/files/analyze", response_model=DrawingAnalysis)
async def analyze_uploaded_file(
    project_id: UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext != ".pdf":
        raise HTTPException(
            status_code=415,
            detail="Only PDF drawings are currently supported for analysis. STEP support is planned.",
        )

    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    content = await file.read(MAX_DRAWING_SIZE_BYTES + 1)
    if len(content) > MAX_DRAWING_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Drawing files must be 25 MB or smaller")
    if b"%PDF-" not in content[:1024]:
        raise HTTPException(status_code=422, detail="The uploaded file is not a valid PDF")

    filepath = UPLOAD_DIR / f"{uuid.uuid4()}{ext}"
    db_file: EngineeringFile | None = None
    try:
        filepath.write_bytes(content)
        db_file = EngineeringFile(
            project_id=project_id,
            file_type="PDF",
            storage_path=str(filepath),
            status="parsing",
        )
        db.add(db_file)
        db.flush()

        project_files = db.query(EngineeringFile).filter(
            EngineeringFile.project_id == project_id,
            EngineeringFile.status != "failed",
        ).order_by(EngineeringFile.created_at, EngineeringFile.id).all()
        raw_analysis = DrawingIntelligenceService.analyze_files(
            files=project_files,
            project_part_number=project.part_number,
            project_material=project.material_spec,
        )
        normalized_feature_model = FeatureNormalizer.normalize_to_dict(raw_analysis)
        analysis = DrawingAnalysis.model_validate(raw_analysis)

        normalized_review_notes = normalized_feature_model.get("review_notes", [])
        if normalized_review_notes:
            existing_issues = {flag.get("issue") for flag in analysis.review_flags if isinstance(flag, dict)}
            for note in normalized_review_notes:
                if note not in existing_issues:
                    analysis.review_flags.append({
                        "issue": note,
                        "confidence": 0.8,
                        "needs_engineer_confirmation": True,
                    })

        if analysis.metadata_and_notes:
            analysis.metadata_and_notes[0]["normalized_feature_model"] = normalized_feature_model

        for project_file in project_files:
            project_file.status = "analyzed"
        ManufacturingRouteService.invalidate(db, project_id)
        persisted_analysis = analysis.model_dump(mode="json")
        project.analysis_data = persisted_analysis
        project.analysis_review = None
        project.route_review = None
        project.process_plan_status = "not_generated"
        project.status = "analysis_ready"
        db.commit()
        return analysis
    except (ValueError, RuntimeError) as error:
        if db_file is not None:
            db_file.status = "failed"
            project.status = "analysis_failed"
            db.commit()
        else:
            db.rollback()
            filepath.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception:
        db.rollback()
        filepath.unlink(missing_ok=True)
        logger.exception("Drawing upload analysis failed for project %s", project_id)
        raise
    finally:
        await file.close()


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


@router.delete("/files/{file_id}", status_code=204)
def delete_file(file_id: UUID, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    engineering_file = db.get(EngineeringFile, file_id)
    if not engineering_file:
        raise HTTPException(status_code=404, detail="Drawing file not found")

    try:
        path = DrawingIntelligenceService._resolve_storage_path(engineering_file.storage_path)
    except FileNotFoundError:
        path = None
    if path is not None:
        try:
            path.unlink(missing_ok=True)
        except OSError as error:
            logger.exception("Failed to remove drawing file %s", engineering_file.id)
            raise HTTPException(status_code=500, detail="Stored drawing file could not be deleted") from error

    db.delete(engineering_file)
    db.commit()
    return None
