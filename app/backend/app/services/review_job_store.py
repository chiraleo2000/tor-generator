"""Persist standalone review extract jobs in Postgres."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_job import ReviewJob
from app.storage.mongo_store import store_from_client

logger = logging.getLogger(__name__)


def store_review_original(
    mongo_client: Any,
    *,
    raw: bytes,
    filename: str,
    mime: str,
    owner_id: uuid.UUID,
) -> str | None:
    store = store_from_client(mongo_client)
    if store is None:
        return None
    try:
        meta = store.put_file(
            filename=filename or "tor.bin",
            content=raw,
            content_type=mime,
            scope="user",
            owner_id=str(owner_id),
        )
        grid_id = str(meta.get("gridfs_id") or "")
        return grid_id or None
    except Exception:
        logger.warning("GridFS store for review extract failed")
        return None


async def save_review_job(db: AsyncSession, job: ReviewJob) -> ReviewJob:
    db.add(job)
    await db.commit()
    return job


async def fetch_review_job(
    db: AsyncSession,
    job_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> ReviewJob | None:
    result = await db.execute(
        select(ReviewJob).where(ReviewJob.id == job_id, ReviewJob.owner_id == owner_id)
    )
    return result.scalar_one_or_none()


async def save_review_result(db: AsyncSession, job: ReviewJob, payload: dict[str, Any]) -> None:
    job.result_json = payload
    job.status = "completed"
    await db.commit()
