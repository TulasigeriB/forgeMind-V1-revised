import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    order_quantity = Column(Integer, nullable=False)
    total_cost = Column(Float, nullable=False)
    total_time_minutes = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="estimate")
    details = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="quotes")
