from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.audit_event import AuditEvent
from app.models.extraction import ExtractionDocument
from app.models.rfq import RFQ
from app.models.user import User
from app.services_extraction import extract_document

router = APIRouter(prefix="/extractions", tags=["extraction engine"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx"}


class ExtractedFieldReview(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    value: str = Field(max_length=2000)
    review_status: Literal["needs_review", "approved", "rejected"]
    label: str | None = Field(default=None, max_length=120)
    source: str | None = Field(default=None, max_length=300)
    confidence: float = Field(default=0, ge=0, le=1)

    @field_validator("value")
    @classmethod
    def trim_value(cls, value: str) -> str:
        return value.strip()


class ReviewInput(BaseModel):
    fields: list[ExtractedFieldReview] = Field(max_length=100)


class ExtractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    rfq_id: str | None
    rfq_reference: str | None = None
    filename: str
    file_type: str
    content_sha256: str
    file_size_bytes: int
    extracted_text: str
    source_map: list[dict]
    fields: list[dict]
    status: str
    extraction_warnings: list[str]
    created_at: datetime
    updated_at: datetime


def serialize(doc: ExtractionDocument, db: Session) -> dict:
    rfq = None
    if doc.rfq_id:
        rfq = db.scalar(select(RFQ).where(RFQ.id == doc.rfq_id, RFQ.organization_id == doc.organization_id))
    return {"id": doc.id, "organization_id": doc.organization_id, "rfq_id": doc.rfq_id, "rfq_reference": rfq.reference if rfq else None, "filename": doc.filename,
            "file_type": doc.file_type, "content_sha256": doc.content_sha256,
            "file_size_bytes": doc.file_size_bytes, "extracted_text": doc.extracted_text,
            "source_map": doc.source_map, "fields": doc.fields, "status": doc.status,
            "extraction_warnings": doc.extraction_warnings, "created_at": doc.created_at,
            "updated_at": doc.updated_at}


def audit(db: Session, user: User, action: str, doc: ExtractionDocument):
    db.add(AuditEvent(organization_id=user.organization_id, actor_user_id=user.id, action=action,
                      entity_type="extraction_document", entity_id=doc.id,
                      details={"filename": doc.filename, "status": doc.status, "sha256": doc.content_sha256}))


@router.get("", response_model=list[ExtractionResponse])
def list_extractions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(ExtractionDocument).where(
        ExtractionDocument.organization_id == user.organization_id
    ).order_by(ExtractionDocument.created_at.desc())).all()
    return [serialize(row, db) for row in rows]


@router.post("", response_model=ExtractionResponse, status_code=status.HTTP_201_CREATED)
async def upload_extraction(file: UploadFile = File(...), rfq_id: str = Form(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()
    if not filename or extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Upload a PDF, DOCX, or XLSX file.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Files must be 10 MB or smaller.")
    if extension == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="The file does not have a valid PDF signature.")
    if extension in {".docx", ".xlsx"} and not content.startswith(b"PK\x03\x04"):
        raise HTTPException(status_code=415, detail="The file does not have a valid Office Open XML signature.")
    rfq = db.scalar(select(RFQ).where(RFQ.id == rfq_id, RFQ.organization_id == user.organization_id))
    if rfq is None:
        raise HTTPException(status_code=422, detail="Select an RFQ belonging to your organization.")
    try:
        extracted_text, source_map, fields, warnings = extract_document(filename, content)
    except Exception as exc:
        message = str(exc) if isinstance(exc, ValueError) else "The document could not be parsed. Check that it is a valid, uncorrupted file."
        raise HTTPException(status_code=422, detail=message) from None
    document = ExtractionDocument(
        organization_id=user.organization_id, rfq_id=rfq.id, uploaded_by_user_id=user.id, filename=filename,
        file_type=extension[1:], content_sha256=sha256(content).hexdigest(), file_size_bytes=len(content),
        file_content=content, extracted_text=extracted_text, source_map=source_map, fields=fields,
        status="needs_review", extraction_warnings=warnings,
    )
    db.add(document)
    db.flush()
    audit(db, user, "extraction.uploaded", document)
    db.commit()
    db.refresh(document)
    return serialize(document, db)


@router.get("/{document_id}", response_model=ExtractionResponse)
def get_extraction(document_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.scalar(select(ExtractionDocument).where(
        ExtractionDocument.id == document_id, ExtractionDocument.organization_id == user.organization_id))
    if doc is None:
        raise HTTPException(status_code=404, detail="Extraction document not found")
    return serialize(doc, db)


@router.patch("/{document_id}/review", response_model=ExtractionResponse)
def review_extraction(document_id: str, payload: ReviewInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.scalar(select(ExtractionDocument).where(
        ExtractionDocument.id == document_id, ExtractionDocument.organization_id == user.organization_id))
    if doc is None:
        raise HTTPException(status_code=404, detail="Extraction document not found")
    by_key = {item["key"]: item for item in doc.fields}
    if len(payload.fields) != len({field.key for field in payload.fields}):
        raise HTTPException(status_code=422, detail="Each field key can only be reviewed once.")
    for review in payload.fields:
        if review.key not in by_key:
            if not review.key.startswith("manual_") or not review.label:
                raise HTTPException(status_code=422, detail=f"Unknown extracted field: {review.key}")
            by_key[review.key] = {"key": review.key, "label": review.label, "value": review.value,
                                  "source": review.source or "Manually added; location not verified",
                                  "confidence": 0, "review_status": review.review_status}
        else:
            by_key[review.key]["value"] = review.value
            by_key[review.key]["review_status"] = review.review_status
    doc.fields = list(by_key.values())
    doc.status = "reviewed" if doc.fields and all(f["review_status"] != "needs_review" for f in doc.fields) else "needs_review"
    audit(db, user, "extraction.reviewed", doc)
    db.commit()
    db.refresh(doc)
    return serialize(doc, db)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_extraction(document_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.scalar(select(ExtractionDocument).where(
        ExtractionDocument.id == document_id, ExtractionDocument.organization_id == user.organization_id))
    if doc is None:
        raise HTTPException(status_code=404, detail="Extraction document not found")
    audit(db, user, "extraction.deleted", doc)
    db.delete(doc)
    db.commit()
    from fastapi import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)
