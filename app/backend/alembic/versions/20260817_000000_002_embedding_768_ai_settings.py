"""Resize kb_chunks embeddings to 768 and add ai_runtime_settings.

Revision ID: 002_embedding_768_ai_settings
Revises: 001_initial_schema
Create Date: 2026-08-17 00:00:00.000000
"""

from alembic import op

revision = "002_embedding_768_ai_settings"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_kb_chunks_embedding")
    op.execute("UPDATE kb_chunks SET embedding = NULL")
    op.execute(
        "ALTER TABLE kb_chunks ALTER COLUMN embedding TYPE vector(768) USING NULL"
    )
    op.execute(
        """
        CREATE INDEX idx_kb_chunks_embedding
        ON kb_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_runtime_settings (
            id INTEGER PRIMARY KEY,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ai_runtime_settings")
    op.execute("DROP INDEX IF EXISTS idx_kb_chunks_embedding")
    op.execute("UPDATE kb_chunks SET embedding = NULL")
    op.execute(
        "ALTER TABLE kb_chunks ALTER COLUMN embedding TYPE vector(1536) USING NULL"
    )
    op.execute(
        """
        CREATE INDEX idx_kb_chunks_embedding
        ON kb_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )
