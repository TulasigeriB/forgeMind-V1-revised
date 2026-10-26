from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID

class FileUpload(BaseModel):
    project_id: UUID
    file_type: str

class EngineeringFile(BaseModel):
    id: UUID
    project_id: UUID
    file_type: str
    storage_path: str
    version: int
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
