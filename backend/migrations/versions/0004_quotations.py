"""Add quotations with costing snapshots.

Revision ID: 0004_quotations
Revises: 0003_rfqs
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
revision: str = "0004_quotations"
down_revision: Union[str, None] = "0003_rfqs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "quotations",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rfq_id", sa.String(36), sa.ForeignKey("rfqs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reference", sa.String(80), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("line_items", sa.JSON(), nullable=False),
        sa.Column("material_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("labor_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("overhead_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("selling_price", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("gross_margin_percent", sa.Numeric(7, 3), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "reference", "revision", name="uq_quotations_org_ref_revision"),
    )
    op.create_index("ix_quotations_organization_id", "quotations", ["organization_id"])
    op.create_index("ix_quotations_rfq_id", "quotations", ["rfq_id"])
    op.create_index("ix_quotations_org_created", "quotations", ["organization_id", "created_at"])

def downgrade() -> None:
    op.drop_index("ix_quotations_org_created", table_name="quotations")
    op.drop_index("ix_quotations_rfq_id", table_name="quotations")
    op.drop_index("ix_quotations_organization_id", table_name="quotations")
    op.drop_table("quotations")
