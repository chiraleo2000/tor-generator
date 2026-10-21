"""LLM usage events, in-app alerts, and pricing overrides.

Revision ID: 010_llm_usage
Revises: 009_kb_content_sha256
Create Date: 2026-10-21 00:00:00.000000
"""

from alembic import op

revision = "010_llm_usage"
down_revision = "009_kb_content_sha256"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_usage_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            user_id UUID,
            request_id VARCHAR(64),
            task VARCHAR(40) NOT NULL DEFAULT 'chat',
            provider VARCHAR(40) NOT NULL DEFAULT '',
            model VARCHAR(200) NOT NULL DEFAULT '',
            latency_ms INTEGER NOT NULL DEFAULT 0,
            prompt_tokens INTEGER NOT NULL DEFAULT 0,
            completion_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            cache_creation_input_tokens INTEGER NOT NULL DEFAULT 0,
            cache_read_input_tokens INTEGER NOT NULL DEFAULT 0,
            tokens_estimated BOOLEAN NOT NULL DEFAULT false,
            cost_usd DOUBLE PRECISION NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'ok',
            error VARCHAR(300)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_usage_events_created "
        "ON llm_usage_events (created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_usage_events_user "
        "ON llm_usage_events (user_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_usage_events_provider "
        "ON llm_usage_events (provider, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_usage_events_task "
        "ON llm_usage_events (task, created_at)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS usage_alerts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            severity VARCHAR(20) NOT NULL DEFAULT 'warn',
            rule_id VARCHAR(60) NOT NULL,
            subject_key VARCHAR(120) NOT NULL DEFAULT '',
            title VARCHAR(200) NOT NULL,
            detail JSONB,
            window_start TIMESTAMPTZ,
            window_end TIMESTAMPTZ,
            acknowledged_at TIMESTAMPTZ,
            acknowledged_by UUID
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_usage_alerts_open "
        "ON usage_alerts (rule_id, subject_key, acknowledged_at)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_pricing_rates (
            id SERIAL PRIMARY KEY,
            provider VARCHAR(40) NOT NULL,
            model VARCHAR(200) NOT NULL DEFAULT '*',
            input_per_million DOUBLE PRECISION NOT NULL DEFAULT 0,
            output_per_million DOUBLE PRECISION NOT NULL DEFAULT 0,
            cache_write_per_million DOUBLE PRECISION NOT NULL DEFAULT 0,
            cache_read_per_million DOUBLE PRECISION NOT NULL DEFAULT 0,
            CONSTRAINT uq_llm_pricing_provider_model UNIQUE (provider, model)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS llm_pricing_rates")
    op.execute("DROP INDEX IF EXISTS idx_usage_alerts_open")
    op.execute("DROP TABLE IF EXISTS usage_alerts")
    op.execute("DROP INDEX IF EXISTS idx_llm_usage_events_task")
    op.execute("DROP INDEX IF EXISTS idx_llm_usage_events_provider")
    op.execute("DROP INDEX IF EXISTS idx_llm_usage_events_user")
    op.execute("DROP INDEX IF EXISTS idx_llm_usage_events_created")
    op.execute("DROP TABLE IF EXISTS llm_usage_events")
