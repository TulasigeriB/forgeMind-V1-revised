from sqlalchemy import Column, JSON, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class Project(Base):
    __tablename__ = "projects"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rfq_id = Column(UUID(as_uuid=True), ForeignKey("rfqs.id"), nullable=False)
    part_number = Column(String, index=True, nullable=False)
    material_spec = Column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="initialization", index=True)
    analysis_data = Column(JSON, nullable=True)
    analysis_review = Column(JSON, nullable=True)
    process_plan_status: Mapped[str] = mapped_column(String, default="not_generated")
    route_review = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    rfq = relationship("RFQ", back_populates="projects")
    files = relationship("EngineeringFile", back_populates="project", cascade="all, delete-orphan")
    features = relationship("ManufacturingFeature", back_populates="project", cascade="all, delete-orphan")
    operations = relationship("ManufacturingOperation", back_populates="project", cascade="all, delete-orphan")
    quotes = relationship("Quote", back_populates="project", cascade="all, delete-orphan")

    @property
    def customer_name(self) -> str | None:
        if self.rfq is None or self.rfq.customer is None:
            return None
        return self.rfq.customer.name
