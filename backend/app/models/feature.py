from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class ManufacturingFeature(Base):
    __tablename__ = "manufacturing_features"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)

    feature_type: Mapped[str] = mapped_column(String, nullable=False) # e.g., "Bore", "Slot", "Thread"
    dimension = Column(Float, nullable=True)
    tolerance: Mapped[str] = mapped_column(String, nullable=True) # e.g., "m6", "h6"
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="features")

class CostTemplate(Base):
    __tablename__ = "cost_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feature_type: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    base_cost_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    time_per_unit_minutes: Mapped[float] = mapped_column(Float, nullable=False)
    precision_multiplier: Mapped[float] = mapped_column(Float, default=1.0) # To account for m6/h6 costs
