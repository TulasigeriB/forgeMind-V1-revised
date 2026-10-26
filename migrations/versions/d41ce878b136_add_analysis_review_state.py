"""add analysis review state

Revision ID: d41ce878b136
Revises: 43e07b29f6a1
Create Date: 2026-10-25

"""
from alembic import op
import sqlalchemy as sa


revision = "d41ce878b136"
down_revision = "43e07b29f6a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("projects", sa.Column("analysis_review", sa.JSON(), nullable=True))
    op.add_column(
        "projects",
        sa.Column("process_plan_status", sa.String(), nullable=False, server_default="not_generated"),
    )
    op.add_column("projects", sa.Column("route_review", sa.JSON(), nullable=True))
    op.create_table(
        "quotes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("order_quantity", sa.Integer(), nullable=False),
        sa.Column("total_cost", sa.Float(), nullable=False),
        sa.Column("total_time_minutes", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="estimate"),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quotes_project_id"), "quotes", ["project_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_quotes_project_id"), table_name="quotes")
    op.drop_table("quotes")
    op.drop_column("projects", "route_review")
    op.drop_column("projects", "process_plan_status")
    op.drop_column("projects", "analysis_review")
