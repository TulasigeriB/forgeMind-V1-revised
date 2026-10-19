"""Link extraction documents to the RFQ they came from."""
from alembic import op
import sqlalchemy as sa

revision = "0006_extraction_rfq_link"
down_revision = "0005_extraction_documents"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("extraction_documents", sa.Column("rfq_id", sa.String(length=36), nullable=True))
    op.create_index("ix_extraction_documents_rfq_id", "extraction_documents", ["rfq_id"])
    op.create_foreign_key("fk_extraction_documents_rfq_id_rfqs", "extraction_documents", "rfqs", ["rfq_id"], ["id"], ondelete="SET NULL")

def downgrade() -> None:
    op.drop_constraint("fk_extraction_documents_rfq_id_rfqs", "extraction_documents", type_="foreignkey")
    op.drop_index("ix_extraction_documents_rfq_id", table_name="extraction_documents")
    op.drop_column("extraction_documents", "rfq_id")
