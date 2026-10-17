"""Add organization-scoped customer records.

Revision ID: 0002_customers
Revises: 0001_foundation
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002_customers"
down_revision: Union[str, None] = "0001_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.String(length=36),
                  sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("contact_name", sa.String(length=200), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "name", name="uq_customers_org_name"),
    )
    op.create_index("ix_customers_organization_id", "customers", ["organization_id"])
    op.create_index("ix_customers_org_created", "customers", ["organization_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_customers_org_created", table_name="customers")
    op.drop_index("ix_customers_organization_id", table_name="customers")
    op.drop_table("customers")
