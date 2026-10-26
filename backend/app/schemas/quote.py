from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QuoteBreakdownItem(BaseModel):
    operation: str
    quantity: int = Field(ge=1)
    unit_cost: float = Field(ge=0)
    extended_cost: float = Field(ge=0)
    unit_time_minutes: float = Field(ge=0)
    extended_time_minutes: float = Field(ge=0)
    machine_type: str | None = None


class QuoteResponse(BaseModel):
    id: UUID
    project_id: UUID
    order_quantity: int = Field(ge=1)
    status: str
    total_cost: float = Field(ge=0)
    total_time_minutes: float = Field(ge=0)
    assumptions: list[str]
    breakdown: list[QuoteBreakdownItem]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
