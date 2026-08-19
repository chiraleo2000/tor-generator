"""Add corpus_group on knowledge_base_documents for mandatory vs user RAG.

Revision ID: 006_kb_corpus_group
Revises: 005_agent_sessions
Create Date: 2026-08-19 12:00:00.000000
"""

from alembic import op

revision = "006_kb_corpus_group"
down_revision = "005_agent_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE knowledge_base_documents "
        "ADD COLUMN IF NOT EXISTS corpus_group VARCHAR(40) NOT NULL DEFAULT 'mandatory_raw'"
    )
    op.execute(
        "UPDATE knowledge_base_documents SET corpus_group = 'user' "
        "WHERE owner_id IS NOT NULL"
    )
    op.execute(
        "UPDATE knowledge_base_documents SET corpus_group = 'mandatory_handbook' "
        "WHERE owner_id IS NULL AND name LIKE '%คู่มือแนวปฏิบัติ%'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE knowledge_base_documents DROP COLUMN IF EXISTS corpus_group")
