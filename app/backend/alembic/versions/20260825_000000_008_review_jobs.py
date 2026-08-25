"""Create review_jobs table for standalone TOR review.

Revision ID: 008_review_jobs
Revises: 007_custom_requirements
Create Date: 2026-08-25 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "008_review_jobs"
down_revision = "007_custom_requirements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False, server_default=""),
        sa.Column("extracted_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("mongo_gridfs_id", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="extracted"),
        sa.Column(
            "result_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "idx_review_jobs_owner_created",
        "review_jobs",
        ["owner_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_review_jobs_owner_created", table_name="review_jobs")
    op.drop_table("review_jobs")
