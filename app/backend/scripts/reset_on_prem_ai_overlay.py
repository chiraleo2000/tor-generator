"""Point persisted Admin AI overlay back at local LM Studio.

Run inside the backend container (WORKDIR /app):
  python /app/scripts/reset_on_prem_ai_overlay.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import Settings

_LOCAL = {
    "deployment_mode": "on_prem",
    "llm_provider": "lm_studio",
    "embedding_provider": "local",
    "local_embedding_server": "lm_studio",
    "mcp_rag_enabled": False,
}


async def _reset() -> dict[str, str] | None:
    settings = Settings()
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as conn:
            row = (
                await conn.execute(text("SELECT id FROM ai_runtime_settings WHERE id = 1"))
            ).first()
            if row is None:
                return None
            await conn.execute(
                text(
                    """
                    UPDATE ai_runtime_settings
                    SET payload = payload || CAST(:patch AS jsonb),
                        updated_at = NOW()
                    WHERE id = 1
                    """
                ),
                {"patch": json.dumps(_LOCAL)},
            )
            check = (
                await conn.execute(
                    text(
                        """
                        SELECT payload->>'llm_provider' AS llm,
                               payload->>'deployment_mode' AS mode,
                               payload->>'mcp_rag_enabled' AS mcp
                        FROM ai_runtime_settings
                        WHERE id = 1
                        """
                    )
                )
            ).mappings().first()
            return dict(check or {})
    finally:
        await engine.dispose()


def main() -> None:
    result = asyncio.run(_reset())
    if result is None:
        print("overlay_missing")
        return
    print("overlay_reset", result)


if __name__ == "__main__":
    main()
