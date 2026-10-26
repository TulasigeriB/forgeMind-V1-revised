from pydantic import BaseModel, EmailStr, ConfigDict, Field
from datetime import datetime
from typing import Optional
from uuid import UUID

class CustomerBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    contact_email: EmailStr
    address: Optional[str] = Field(default=None, max_length=1000)

class CustomerCreate(CustomerBase):
    pass

class Customer(CustomerBase):
    id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
