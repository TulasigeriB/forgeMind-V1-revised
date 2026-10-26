"""add_project_analysis_data

Revision ID: 43e07b29f6a1
Revises: 2d19a8f3c6b4
Create Date: 2026-10-24 22:49:33

"""
from alembic import op
import sqlalchemy as sa


revision = "43e07b29f6a1"
down_revision = "2d19a8f3c6b4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("projects", sa.Column("analysis_data", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("projects", "analysis_data")
