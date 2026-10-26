from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional
from uuid import UUID

class ProjectBase(BaseModel):
    rfq_id: UUID
    part_number: str = Field(min_length=1, max_length=255)
    material_spec: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: UUID
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
