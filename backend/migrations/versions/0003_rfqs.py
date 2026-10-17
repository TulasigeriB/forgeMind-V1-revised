"""Add organization-scoped RFQ management.

Revision ID: 0003_rfqs
Revises: 0002_customers
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003_rfqs"
down_revision: Union[str, None] = "0002_customers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "rfqs",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reference", sa.String(80), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Received"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "reference", name="uq_rfqs_org_reference"),
    )
    op.create_index("ix_rfqs_organization_id", "rfqs", ["organization_id"])
    op.create_index("ix_rfqs_customer_id", "rfqs", ["customer_id"])
    op.create_index("ix_rfqs_org_created", "rfqs", ["organization_id", "created_at"])

def downgrade() -> None:
    op.drop_index("ix_rfqs_org_created", table_name="rfqs")
    op.drop_index("ix_rfqs_customer_id", table_name="rfqs")
    op.drop_index("ix_rfqs_organization_id", table_name="rfqs")
    op.drop_table("rfqs")
