"""create_manufacturing_operations

Revision ID: 2d19a8f3c6b4
Revises: fcab42dc31a2
Create Date: 2026-10-24 22:31:27

"""
from alembic import op
import sqlalchemy as sa


revision = "2d19a8f3c6b4"
down_revision = "fcab42dc31a2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "manufacturing_operations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("operation_name", sa.String(), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("estimated_time_minutes", sa.Float(), nullable=False),
        sa.Column("estimated_cost", sa.Float(), nullable=False),
        sa.Column("machine_type", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("manufacturing_operations")
