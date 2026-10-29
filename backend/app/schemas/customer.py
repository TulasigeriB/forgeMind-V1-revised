from pydantic import BaseModel, EmailStr, ConfigDict, Field, model_validator
from datetime import datetime
from typing import Optional
from uuid import UUID

class CustomerBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    contact_email: EmailStr
    address: Optional[str] = Field(default=None, max_length=1000)

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    contact_email: Optional[EmailStr] = None
    address: Optional[str] = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_update_fields(self):
        if not self.model_fields_set:
            raise ValueError("At least one customer field must be provided")
        return self

class Customer(CustomerBase):
    id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
