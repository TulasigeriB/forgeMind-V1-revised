from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship
from app.db.session import Base

class ManufacturingOperation(Base):
    __tablename__ = "manufacturing_operations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)

    operation_name = Column(String, nullable=False) # e.g., "Precision Boring"
    sequence_order = Column(Integer, nullable=False) # Op 10, 20, 30...
    estimated_time_minutes = Column(Float, nullable=False)
    estimated_cost = Column(Float, nullable=False)
    machine_type = Column(String, nullable=True) # e.g., "CNC Lathe", "5-Axis Mill"

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="operations")
