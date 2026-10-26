"""add_rfq_priority

Revision ID: fcab42dc31a2
Revises: 3a76c292d4e8
Create Date: 2026-10-24 21:54:00

"""
from alembic import op
import sqlalchemy as sa


revision = "fcab42dc31a2"
down_revision = "3a76c292d4e8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "rfqs",
        sa.Column("priority", sa.String(), server_default="normal", nullable=False),
    )
    op.alter_column("rfqs", "priority", server_default=None)


def downgrade():
    op.drop_column("rfqs", "priority")
