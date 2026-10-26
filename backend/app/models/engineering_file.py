from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship
from app.db.session import Base

class EngineeringFile(Base):
    __tablename__ = "engineering_files"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    file_type = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    version = Column(Integer, default=1)
    status = Column(String, default="uploaded")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    project = relationship("Project", back_populates="files")
