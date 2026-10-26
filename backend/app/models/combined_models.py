from sqlalchemy import Column, String, DateTime, ForeignKey, func, Integer
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship
from backend.app.db.session import Base

class Customer(Base):
    __tablename__ = "customers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, index=True)
    contact_email = Column(String, unique=True, index=True)
    address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    rfqs = relationship("RFQ", back_populates="customer")

class RFQ(Base):
    __tablename__ = "rfqs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    status = Column(String, default="pending", index=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    customer = relationship("Customer", back_populates="rfqs")
    projects = relationship("Project", back_populates="rfq")

class Project(Base):
    __tablename__ = "projects"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rfq_id = Column(UUID(as_uuid=True), ForeignKey("rfqs.id"), nullable=False)
    part_number = Column(String, index=True, nullable=False)
    material_spec = Column(String, nullable=True)
    status = Column(String, default="initialization", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    rfq = relationship("RFQ", back_populates="projects")
    files = relationship("EngineeringFile", back_populates="project")

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
