from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.audit_event import AuditEvent
from app.models.organization import Organization
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["authentication"])


class RegisterRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=200)
    email: str
    password: str = Field(min_length=12, max_length=128)
    default_currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")

    @field_validator("organization_name")
    @classmethod
    def normalize_org_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Organization name must contain at least 2 non-space characters")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if len(value) > 320 or value.count("@") != 1 or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("A valid email address is required")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)


    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if len(value) > 320 or value.count("@") != 1 or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("A valid email address is required")
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    email: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = 3600
    user: UserResponse


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Create an organization and its first owner. Restrict this endpoint before public deployment."""
    email = payload.email
    # Email-only login requires emails to be unique across organizations.
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    organization = Organization(name=payload.organization_name, default_currency=payload.default_currency)
    db.add(organization)
    db.flush()
    user = User(
        organization_id=organization.id,
        email=email,
        password_hash=hash_password(payload.password),
        role="owner",
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.add(AuditEvent(
        organization_id=organization.id,
        actor_user_id=user.id,
        action="organization.registered",
        entity_type="organization",
        entity_id=organization.id,
        details={"owner_email": email},
    ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Could not register account with these details") from None
    db.refresh(user)
    token = create_access_token(user.id, user.organization_id, user.role)
    return TokenResponse(access_token=token, user=user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.email
    matches = db.scalars(select(User).where(User.email == email, User.is_active.is_(True)).limit(2)).all()
    # Fail closed if legacy/manual data contains duplicate emails across organizations.
    user = matches[0] if len(matches) == 1 else None
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password", headers={"WWW-Authenticate": "Bearer"})
    return TokenResponse(
        access_token=create_access_token(user.id, user.organization_id, user.role),
        user=user,
    )


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user
