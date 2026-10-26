from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

class RFQBase(BaseModel):
    customer_id: UUID
    deadline: Optional[datetime] = None
    quantity: int = Field(default=1, gt=0)
    priority: Literal["low", "normal", "high", "urgent"] = "normal"

class RFQCreate(RFQBase):
    pass

class RFQ(RFQBase):
    id: UUID
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
