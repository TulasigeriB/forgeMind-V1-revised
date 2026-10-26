from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime

class ManufacturingFeatureBase(BaseModel):
    feature_type: str
    dimension: Optional[float] = None
    tolerance: Optional[str] = None
    quantity: int = 1

class ManufacturingFeatureCreate(ManufacturingFeatureBase):
    project_id: UUID

class ManufacturingFeature(ManufacturingFeatureBase):
    id: UUID
    project_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CostTemplateBase(BaseModel):
    feature_type: str
    base_cost_per_unit: float
    time_per_unit_minutes: float
    precision_multiplier: float = 1.0

class CostTemplateCreate(CostTemplateBase):
    pass

class CostTemplate(CostTemplateBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)
