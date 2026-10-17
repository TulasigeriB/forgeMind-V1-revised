from datetime import date, datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.audit_event import AuditEvent
from app.models.customer import Customer
from app.models.rfq import RFQ
from app.models.user import User

router = APIRouter(prefix="/rfqs", tags=["rfqs"])
RFQStatus = Literal["Draft", "Received", "Quoting", "Submitted", "Won", "Lost", "Cancelled"]

class RFQInput(BaseModel):
    customer_id: str = Field(min_length=1, max_length=36)
    reference: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    quantity: float = Field(gt=0, le=1_000_000_000)
    due_date: date | None = None
    status: RFQStatus = "Received"
    notes: str | None = Field(default=None, max_length=10000)

    @field_validator("reference", "title")
    @classmethod
    def trim_required(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Must contain at least 2 non-space characters")
        return value

class RFQResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    customer_id: str
    customer_name: str
    reference: str
    title: str
    description: str | None
    quantity: float
    due_date: date | None
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime

def _response(rfq: RFQ, customer: Customer) -> dict:
    return {"id": rfq.id, "organization_id": rfq.organization_id, "customer_id": rfq.customer_id,
            "customer_name": customer.name, "reference": rfq.reference, "title": rfq.title,
            "description": rfq.description, "quantity": rfq.quantity, "due_date": rfq.due_date,
            "status": rfq.status, "notes": rfq.notes, "created_at": rfq.created_at, "updated_at": rfq.updated_at}

def _customer(db: Session, user: User, customer_id: str) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.id == customer_id, Customer.organization_id == user.organization_id))
    if customer is None:
        raise HTTPException(status_code=422, detail="Select a customer belonging to your organization")
    return customer

def _audit(db: Session, user: User, action: str, rfq: RFQ) -> None:
    db.add(AuditEvent(organization_id=user.organization_id, actor_user_id=user.id, action=action,
                      entity_type="rfq", entity_id=rfq.id, details={"reference": rfq.reference, "status": rfq.status}))

@router.get("", response_model=list[RFQResponse])
def list_rfqs(status_filter: RFQStatus | None = Query(default=None, alias="status"),
              limit: int = Query(default=100, ge=1, le=200), offset: int = Query(default=0, ge=0),
              user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(RFQ, Customer).join(Customer, RFQ.customer_id == Customer.id).where(RFQ.organization_id == user.organization_id)
    if status_filter:
        query = query.where(RFQ.status == status_filter)
    rows = db.execute(query.order_by(RFQ.created_at.desc()).limit(limit).offset(offset)).all()
    return [_response(rfq, customer) for rfq, customer in rows]

@router.post("", response_model=RFQResponse, status_code=status.HTTP_201_CREATED)
def create_rfq(payload: RFQInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    customer = _customer(db, user, payload.customer_id)
    rfq = RFQ(organization_id=user.organization_id, **payload.model_dump())
    db.add(rfq)
    db.flush()
    _audit(db, user, "rfq.created", rfq)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An RFQ with this reference already exists in this organization") from None
    db.refresh(rfq)
    return _response(rfq, customer)

@router.get("/{rfq_id}", response_model=RFQResponse)
def get_rfq(rfq_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.execute(select(RFQ, Customer).join(Customer, RFQ.customer_id == Customer.id).where(RFQ.id == rfq_id, RFQ.organization_id == user.organization_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="RFQ not found")
    return _response(*row)

@router.patch("/{rfq_id}", response_model=RFQResponse)
def update_rfq(rfq_id: str, payload: RFQInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rfq = db.scalar(select(RFQ).where(RFQ.id == rfq_id, RFQ.organization_id == user.organization_id))
    if rfq is None:
        raise HTTPException(status_code=404, detail="RFQ not found")
    customer = _customer(db, user, payload.customer_id)
    for key, value in payload.model_dump().items():
        setattr(rfq, key, value)
    _audit(db, user, "rfq.updated", rfq)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An RFQ with this reference already exists in this organization") from None
    db.refresh(rfq)
    return _response(rfq, customer)

@router.delete("/{rfq_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rfq(rfq_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rfq = db.scalar(select(RFQ).where(RFQ.id == rfq_id, RFQ.organization_id == user.organization_id))
    if rfq is None:
        raise HTTPException(status_code=404, detail="RFQ not found")
    _audit(db, user, "rfq.deleted", rfq)
    db.delete(rfq)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
