"""Process-wide handles set during FastAPI lifespan.

The orchestrator and seed CLIs read these without a Request object.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

session_factory: async_sessionmaker[AsyncSession] | None = None
mongo_client: Any = None
neo4j_driver: Any = None


def set_session_factory(value: async_sessionmaker[AsyncSession] | None) -> None:
    global session_factory
    session_factory = value


def set_mongo_client(value: Any) -> None:
    global mongo_client
    mongo_client = value


def set_neo4j_driver(value: Any) -> None:
    global neo4j_driver
    neo4j_driver = value
