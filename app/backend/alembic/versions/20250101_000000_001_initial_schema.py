"""Initial schema: all 11 tables, indexes, pgvector extension.

Revision ID: 001_initial_schema
Revises: (none)
Create Date: 2025-01-01 00:00:00.000000

This migration creates the complete database schema for the TOR Drafting
and Review Application. It includes:
- pgvector extension for vector storage
- 11 tables: users, projects, project_versions, tor_sections, templates,
  template_versions, knowledge_base_documents, kb_chunks, suggestions,
  audit_logs, uploaded_files
- All foreign keys and constraints
- Performance indexes including HNSW index for vector similarity search

NOTE: Thai collation (th_TH.UTF-8 or ICU collation for proper ก-ฮ sorting)
should be configured at the DATABASE level when creating the PostgreSQL database:
    CREATE DATABASE tor_generator
        WITH ENCODING 'UTF8'
        LC_COLLATE = 'th_TH.UTF-8'
        LC_CTYPE = 'th_TH.UTF-8'
        TEMPLATE = template0;
Alternatively, use ICU collation on PostgreSQL 15+:
    CREATE DATABASE tor_generator
        WITH ENCODING 'UTF8'
        ICU_LOCALE = 'th-TH'
        LOCALE_PROVIDER = icu
        TEMPLATE = template0;
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables, indexes, and extensions."""

    # Enable pgvector extension for vector storage
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # =========================================================================
    # Table 1: users
    # =========================================================================
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("organization", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="officer"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # =========================================================================
    # Table 2: templates
    # (Created before projects because projects has FK to templates)
    # =========================================================================
    op.create_table(
        "templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("industry", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("section_structure", JSONB, nullable=False),
        sa.Column("placeholder_guidance", JSONB, nullable=False),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # =========================================================================
    # Table 3: projects
    # =========================================================================
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("ministry", sa.String(255), nullable=False),
        sa.Column("budget", sa.BigInteger, nullable=False),
        sa.Column(
            "project_type", sa.String(50), nullable=False, server_default="general"
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("current_step", sa.Integer, nullable=False, server_default="1"),
        sa.Column("quality_score", sa.Integer, nullable=True),
        sa.Column(
            "template_id",
            UUID(as_uuid=True),
            sa.ForeignKey("templates.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # =========================================================================
    # Table 4: project_versions
    # =========================================================================
    op.create_table(
        "project_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("snapshot_data", JSONB, nullable=False),
        sa.Column("step_number", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # =========================================================================
    # Table 5: tor_sections
    # =========================================================================
    op.create_table(
        "tor_sections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column("section_key", sa.String(20), nullable=False),
        sa.Column("sub_key", sa.String(20), nullable=True),
        sa.Column("content", sa.Text, nullable=False, server_default=""),
        sa.Column("ai_draft", sa.Text, nullable=True),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("validation_findings", JSONB, nullable=True),
        sa.Column("is_approved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # =========================================================================
    # Table 6: template_versions
    # =========================================================================
    op.create_table(
        "template_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "template_id",
            UUID(as_uuid=True),
            sa.ForeignKey("templates.id"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("section_structure", JSONB, nullable=False),
        sa.Column("placeholder_guidance", JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # =========================================================================
    # Table 7: knowledge_base_documents
    # =========================================================================
    op.create_table(
        "knowledge_base_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column(
            "processing_status",
            sa.String(50),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("chunk_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # =========================================================================
    # Table 8: kb_chunks (with pgvector embedding column)
    # =========================================================================
    op.create_table(
        "kb_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("knowledge_base_documents.id"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("section_label", sa.String(255), nullable=True),
        sa.Column("page_number", sa.Integer, nullable=True),
        # NOTE: embedding column added below via raw SQL (pgvector vector type)
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
    )
    # Add pgvector embedding column (1536 dimensions for OpenAI/compatible embeddings)
    op.execute("ALTER TABLE kb_chunks ADD COLUMN embedding vector(1536)")

    # =========================================================================
    # Table 9: suggestions
    # =========================================================================
    op.create_table(
        "suggestions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column("section_key", sa.String(20), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("current_text", sa.Text, nullable=False),
        sa.Column("suggested_text", sa.Text, nullable=False),
        sa.Column("predicted_score_improvement", sa.Float, nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # =========================================================================
    # Table 10: audit_logs
    # =========================================================================
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=False),
        sa.Column("details", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # =========================================================================
    # Table 11: uploaded_files
    # =========================================================================
    op.create_table(
        "uploaded_files",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id"),
            nullable=True,
        ),
        sa.Column(
            "uploaded_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("original_name", sa.String(500), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("extracted_text", sa.Text, nullable=True),
        sa.Column(
            "ocr_status", sa.String(50), nullable=False, server_default="pending"
        ),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # =========================================================================
    # Performance Indexes
    # =========================================================================

    # projects indexes
    op.create_index(
        "idx_projects_owner_status",
        "projects",
        ["owner_id", "status"],
    )
    op.create_index(
        "idx_projects_updated_at",
        "projects",
        [sa.text("updated_at DESC")],
    )

    # tor_sections index
    op.create_index(
        "idx_tor_sections_project",
        "tor_sections",
        ["project_id", "section_key"],
    )

    # kb_chunks indexes
    op.create_index(
        "idx_kb_chunks_document",
        "kb_chunks",
        ["document_id", "chunk_index"],
    )

    # suggestions index
    op.create_index(
        "idx_suggestions_project_status",
        "suggestions",
        ["project_id", "status"],
    )

    # audit_logs index (composite with DESC on created_at)
    op.create_index(
        "idx_audit_logs_user_action",
        "audit_logs",
        ["user_id", "action", sa.text("created_at DESC")],
    )

    # pgvector HNSW index for fast cosine similarity search
    # Using raw SQL because Alembic's create_index doesn't natively support
    # HNSW operator classes and WITH parameters
    op.execute(
        """
        CREATE INDEX idx_kb_chunks_embedding
        ON kb_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    """Drop all tables and the pgvector extension."""

    # Drop indexes (those created via raw SQL)
    op.execute("DROP INDEX IF EXISTS idx_kb_chunks_embedding")

    # Drop all tables in reverse dependency order
    op.drop_table("uploaded_files")
    op.drop_table("audit_logs")
    op.drop_table("suggestions")
    op.drop_table("kb_chunks")
    op.drop_table("knowledge_base_documents")
    op.drop_table("template_versions")
    op.drop_table("tor_sections")
    op.drop_table("project_versions")
    op.drop_table("projects")
    op.drop_table("templates")
    op.drop_table("users")

    # Remove pgvector extension
    op.execute("DROP EXTENSION IF EXISTS vector")
