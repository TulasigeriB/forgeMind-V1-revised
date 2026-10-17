from datetime import date, datetime
from uuid import uuid4
from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base_model import BaseModel

class Quotation(BaseModel):
    __tablename__ = "quotations"
    __table_args__ = (
        UniqueConstraint("organization_id", "reference", "revision", name="uq_quotations_org_ref_revision"),
        Index("ix_quotations_org_created", "organization_id", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    rfq_id: Mapped[str] = mapped_column(ForeignKey("rfqs.id", ondelete="RESTRICT"), nullable=False, index=True)
    reference: Mapped[str] = mapped_column(String(80), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Draft")
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    line_items: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    material_cost: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    labor_cost: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    overhead_cost: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    total_cost: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    selling_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    gross_margin_percent: Mapped[float] = mapped_column(Numeric(7, 3), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
