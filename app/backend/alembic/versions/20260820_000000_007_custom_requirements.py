"""Add custom_requirements_text column on projects.

Revision ID: 007_custom_requirements
Revises: 006_kb_corpus_group
Create Date: 2026-08-20 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "007_custom_requirements"
down_revision = "006_kb_corpus_group"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("custom_requirements_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "custom_requirements_text")
