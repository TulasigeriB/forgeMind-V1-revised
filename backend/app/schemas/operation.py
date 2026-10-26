from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ManufacturingOperation(BaseModel):
    id: UUID
    project_id: UUID
    operation_name: str
    sequence_order: int = Field(ge=1)
    estimated_time_minutes: float = Field(ge=0)
    estimated_cost: float = Field(ge=0)
    machine_type: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
