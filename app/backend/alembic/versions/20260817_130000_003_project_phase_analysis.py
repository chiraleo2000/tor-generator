"""Resize kb_chunks embeddings to 768 and add ai_runtime_settings.

Revision ID: 003_project_phase_analysis
Revises: 002_embedding_768_ai_settings
Create Date: 2026-08-17 13:00:00.000000
"""

from alembic import op

revision = "003_project_phase_analysis"
down_revision = "002_embedding_768_ai_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS current_phase INTEGER NOT NULL DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb"
    )
    op.execute(
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS extracted_fields JSONB NOT NULL DEFAULT '{}'::jsonb"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS extracted_fields")
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS analysis_json")
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS current_phase")
