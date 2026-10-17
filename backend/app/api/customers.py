from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.audit_event import AuditEvent
from app.models.customer import Customer
from app.models.user import User

router = APIRouter(prefix="/customers", tags=["customers"])


class CustomerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    contact_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=5000)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Customer name must contain at least 2 non-space characters")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip().lower()
        if value.count("@") != 1 or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("A valid email address is required")
        return value


class CustomerUpdate(CustomerCreate):
    pass


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    contact_name: str | None
    email: str | None
    phone: str | None
    address: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


def _audit(db: Session, user: User, action: str, customer: Customer) -> None:
    db.add(AuditEvent(
        organization_id=user.organization_id,
        actor_user_id=user.id,
        action=action,
        entity_type="customer",
        entity_id=customer.id,
        details={"name": customer.name},
    ))


@router.get("", response_model=list[CustomerResponse])
def list_customers(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Customer)
        .where(Customer.organization_id == user.organization_id)
        .order_by(Customer.created_at.desc(), Customer.id)
        .limit(limit).offset(offset)
    ).all()


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = Customer(organization_id=user.organization_id, **payload.model_dump())
    db.add(customer)
    db.flush()
    _audit(db, user, "customer.created", customer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A customer with this name already exists in this organization") from None
    db.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = db.scalar(select(Customer).where(
        Customer.id == customer_id, Customer.organization_id == user.organization_id
    ))
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: str,
    payload: CustomerUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = db.scalar(select(Customer).where(
        Customer.id == customer_id, Customer.organization_id == user.organization_id
    ))
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    for key, value in payload.model_dump().items():
        setattr(customer, key, value)
    _audit(db, user, "customer.updated", customer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A customer with this name already exists in this organization") from None
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = db.scalar(select(Customer).where(
        Customer.id == customer_id, Customer.organization_id == user.organization_id
    ))
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    _audit(db, user, "customer.deleted", customer)
    db.delete(customer)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
