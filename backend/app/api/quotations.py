from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.audit_event import AuditEvent
from app.models.customer import Customer
from app.models.quotation import Quotation
from app.models.rfq import RFQ
from app.models.user import User

router = APIRouter(prefix="/quotations", tags=["quotations"])
QuoteStatus = Literal["Draft", "Under Review", "Submitted", "Accepted", "Rejected", "Expired"]

class LineItem(BaseModel):
    description: str = Field(min_length=2, max_length=200)
    quantity: Decimal = Field(gt=0, le=Decimal("1000000000"))
    unit: str = Field(default="pcs", min_length=1, max_length=20)
    material_unit_cost: Decimal = Field(default=Decimal("0"), ge=0, le=Decimal("1000000000"))
    labor_unit_cost: Decimal = Field(default=Decimal("0"), ge=0, le=Decimal("1000000000"))
    overhead_unit_cost: Decimal = Field(default=Decimal("0"), ge=0, le=Decimal("1000000000"))
    unit_selling_price: Decimal = Field(default=Decimal("0"), ge=0, le=Decimal("1000000000"))

    @field_validator("description", "unit")
    @classmethod
    def trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Must not be blank")
        return value

class QuotationInput(BaseModel):
    rfq_id: str = Field(min_length=1, max_length=36)
    reference: str = Field(min_length=2, max_length=80)
    revision: int = Field(default=1, ge=1, le=1000)
    currency: Literal["INR", "USD", "EUR", "GBP"] = "INR"
    status: QuoteStatus = "Draft"
    valid_until: date | None = None
    line_items: list[LineItem] = Field(min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=10000)

    @field_validator("reference")
    @classmethod
    def trim_reference(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Reference must contain at least 2 non-space characters")
        return value

class QuotationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    rfq_id: str
    rfq_reference: str
    customer_name: str
    reference: str
    revision: int
    currency: str
    status: str
    valid_until: date | None
    line_items: list[dict]
    material_cost: Decimal
    labor_cost: Decimal
    overhead_cost: Decimal
    total_cost: Decimal
    selling_price: Decimal
    gross_margin_percent: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime

CENT = Decimal("0.01")
def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)

def totals(items: list[LineItem]):
    material = money(sum((x.quantity * x.material_unit_cost for x in items), Decimal(0)))
    labor = money(sum((x.quantity * x.labor_unit_cost for x in items), Decimal(0)))
    overhead = money(sum((x.quantity * x.overhead_unit_cost for x in items), Decimal(0)))
    price = money(sum((x.quantity * x.unit_selling_price for x in items), Decimal(0)))
    cost = money(material + labor + overhead)
    margin = money((price - cost) * Decimal(100) / price) if price > 0 else Decimal(0)
    return material, labor, overhead, cost, price, margin

def rfq_for(db: Session, user: User, rfq_id: str) -> RFQ:
    rfq = db.scalar(select(RFQ).where(RFQ.id == rfq_id, RFQ.organization_id == user.organization_id))
    if rfq is None:
        raise HTTPException(status_code=422, detail="Select an RFQ belonging to your organization")
    return rfq

def serialize(q: Quotation, rfq: RFQ, customer_name: str) -> dict:
    return {"id": q.id, "organization_id": q.organization_id, "rfq_id": q.rfq_id, "rfq_reference": rfq.reference,
            "customer_name": customer_name, "reference": q.reference, "revision": q.revision,
            "currency": q.currency, "status": q.status, "valid_until": q.valid_until, "line_items": q.line_items,
            "material_cost": q.material_cost, "labor_cost": q.labor_cost, "overhead_cost": q.overhead_cost,
            "total_cost": q.total_cost, "selling_price": q.selling_price, "gross_margin_percent": q.gross_margin_percent,
            "notes": q.notes, "created_at": q.created_at, "updated_at": q.updated_at}

def audit(db: Session, user: User, action: str, quote: Quotation):
    db.add(AuditEvent(organization_id=user.organization_id, actor_user_id=user.id, action=action,
                      entity_type="quotation", entity_id=quote.id,
                      details={"reference": quote.reference, "revision": quote.revision, "status": quote.status}))

def apply_input(quote: Quotation, payload: QuotationInput):
    items = [item.model_dump(mode="json") for item in payload.line_items]
    material, labor, overhead, cost, price, margin = totals(payload.line_items)
    quote.rfq_id = payload.rfq_id
    quote.reference = payload.reference
    quote.revision = payload.revision
    quote.currency = payload.currency
    quote.status = payload.status
    quote.valid_until = payload.valid_until
    quote.line_items = items
    quote.material_cost = material
    quote.labor_cost = labor
    quote.overhead_cost = overhead
    quote.total_cost = cost
    quote.selling_price = price
    quote.gross_margin_percent = margin
    quote.notes = payload.notes

@router.get("", response_model=list[QuotationResponse])
def list_quotations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Quotation, RFQ, Customer.name).join(RFQ, Quotation.rfq_id == RFQ.id).join(Customer, RFQ.customer_id == Customer.id).where(Quotation.organization_id == user.organization_id).order_by(Quotation.created_at.desc())).all()
    return [serialize(q, rfq, customer_name) for q, rfq, customer_name in rows]

@router.post("", response_model=QuotationResponse, status_code=status.HTTP_201_CREATED)
def create_quotation(payload: QuotationInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rfq_for(db, user, payload.rfq_id)
    quote = Quotation(organization_id=user.organization_id)
    apply_input(quote, payload)
    db.add(quote)
    try:
        db.flush(); audit(db, user, "quotation.created", quote); db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(status_code=409, detail="This quotation reference and revision already exists") from None
    db.refresh(quote)
    row = db.execute(select(RFQ, Customer.name).join(Customer, RFQ.customer_id == Customer.id).where(RFQ.id == quote.rfq_id)).first()
    return serialize(quote, row[0], row[1])

@router.get("/{quote_id}", response_model=QuotationResponse)
def get_quotation(quote_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.execute(select(Quotation, RFQ, Customer.name).join(RFQ, Quotation.rfq_id == RFQ.id).join(Customer, RFQ.customer_id == Customer.id).where(Quotation.id == quote_id, Quotation.organization_id == user.organization_id)).first()
    if row is None: raise HTTPException(status_code=404, detail="Quotation not found")
    return serialize(row[0], row[1], row[2])

@router.patch("/{quote_id}", response_model=QuotationResponse)
def update_quotation(quote_id: str, payload: QuotationInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    quote = db.scalar(select(Quotation).where(Quotation.id == quote_id, Quotation.organization_id == user.organization_id))
    if quote is None: raise HTTPException(status_code=404, detail="Quotation not found")
    rfq_for(db, user, payload.rfq_id)
    apply_input(quote, payload)
    try:
        audit(db, user, "quotation.updated", quote); db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(status_code=409, detail="This quotation reference and revision already exists") from None
    db.refresh(quote); row = db.execute(select(RFQ, Customer.name).join(Customer, RFQ.customer_id == Customer.id).where(RFQ.id == quote.rfq_id)).first()
    return serialize(quote, row[0], row[1])

@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quotation(quote_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    quote = db.scalar(select(Quotation).where(Quotation.id == quote_id, Quotation.organization_id == user.organization_id))
    if quote is None: raise HTTPException(status_code=404, detail="Quotation not found")
    audit(db, user, "quotation.deleted", quote); db.delete(quote); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
