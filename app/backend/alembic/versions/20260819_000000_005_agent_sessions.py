"""Agent workflow sessions, KB chat sessions, and project workflow_mode.

Revision ID: 005_agent_sessions
Revises: 004_chat_kb_owner
Create Date: 2026-08-19 00:00:00.000000
"""

from alembic import op

revision = "005_agent_sessions"
down_revision = "004_chat_kb_owner"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id),
            user_id UUID NOT NULL REFERENCES users(id),
            phase VARCHAR(30) NOT NULL DEFAULT 'idle',
            slot_map JSONB NOT NULL DEFAULT '{}'::jsonb,
            gap_iteration INTEGER NOT NULL DEFAULT 0,
            graph_state JSONB,
            messages JSONB NOT NULL DEFAULT '[]'::jsonb,
            warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL DEFAULT now() + INTERVAL '30 days'
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_sessions_user "
        "ON agent_sessions (user_id, phase)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_sessions_project "
        "ON agent_sessions (project_id)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS kb_chat_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id),
            history JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_active_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_kb_chat_user ON kb_chat_sessions (user_id)"
    )
    op.execute(
        "ALTER TABLE projects "
        "ADD COLUMN IF NOT EXISTS workflow_mode VARCHAR(20) NOT NULL DEFAULT 'wizard'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS workflow_mode")
    op.execute("DROP TABLE IF EXISTS kb_chat_sessions")
    op.execute("DROP INDEX IF EXISTS idx_agent_sessions_project")
    op.execute("DROP INDEX IF EXISTS idx_agent_sessions_user")
    op.execute("DROP TABLE IF EXISTS agent_sessions")
