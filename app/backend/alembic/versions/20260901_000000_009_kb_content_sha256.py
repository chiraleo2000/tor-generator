"""Add content_sha256 on knowledge_base_documents for incremental seed dedupe.

Revision ID: 009_kb_content_sha256
Revises: 008_review_jobs
Create Date: 2026-09-01 00:00:00.000000
"""

from alembic import op

revision = "009_kb_content_sha256"
down_revision = "008_review_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE knowledge_base_documents "
        "ADD COLUMN IF NOT EXISTS content_sha256 VARCHAR(64)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE knowledge_base_documents DROP COLUMN IF EXISTS content_sha256"
    )
