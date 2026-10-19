"""Add secure document ingestion and reviewed extraction records.

Revision ID: 0005_extraction_documents
Revises: 0004_quotations
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005_extraction_documents"
down_revision: Union[str, None] = "0004_quotations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "extraction_documents",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("file_content", sa.LargeBinary(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("source_map", sa.JSON(), nullable=False),
        sa.Column("fields", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="needs_review"),
        sa.Column("extraction_warnings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_extraction_documents_organization_id", "extraction_documents", ["organization_id"])
    op.create_index("ix_extraction_documents_uploaded_by_user_id", "extraction_documents", ["uploaded_by_user_id"])
    op.create_index("ix_extraction_documents_org_created", "extraction_documents", ["organization_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_extraction_documents_org_created", table_name="extraction_documents")
    op.drop_index("ix_extraction_documents_uploaded_by_user_id", table_name="extraction_documents")
    op.drop_index("ix_extraction_documents_organization_id", table_name="extraction_documents")
    op.drop_table("extraction_documents")
