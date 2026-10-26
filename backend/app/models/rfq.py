from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship
from app.db.session import Base

class RFQ(Base):
    __tablename__ = "rfqs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    status = Column(String, default="pending", index=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    quantity = Column(Integer, default=1)
    priority = Column(String, nullable=False, default="normal")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    customer = relationship("Customer", back_populates="rfqs")
    projects = relationship("Project", back_populates="rfq")
