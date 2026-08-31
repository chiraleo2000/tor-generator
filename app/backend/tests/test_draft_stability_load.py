"""Load / stability notes for Req 13.5 (200k pack, 500k paste, 3 concurrent jobs)."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import MagicMock

import pytest

from app.draft_job_store import bump_progress, clear_memory, get_job, mark_status, set_job
from app.models.project import Project
from app.services.intake_service import (
    INTAKE_PACK_LIMIT,
    INTAKE_TEXT_CHAR_LIMIT,
    append_intake_text,
    project_intake_pack,
)


@pytest.fixture(autouse=True)
def _reset_store():
    clear_memory()
    yield
    clear_memory()


def test_paste_accepts_500k_characters():
    project = MagicMock(spec=Project)
    project.analysis_json = {}
    project.extracted_fields = {}
    text = "ก" * INTAKE_TEXT_CHAR_LIMIT
    append_intake_text(project, "วางข้อความ", text)
    pack = project_intake_pack(project, limit=INTAKE_TEXT_CHAR_LIMIT)
    assert len(text) == 500_000
    assert "ก" in pack


def test_review_pack_capped_at_200k():
    project = MagicMock(spec=Project)
    project.analysis_json = {}
    project.extracted_fields = {}
    append_intake_text(project, "แพ็กตรวจ", "ข" * 400_000)
    pack = project_intake_pack(project, limit=INTAKE_PACK_LIMIT)
    assert len(pack) <= INTAKE_PACK_LIMIT
    assert len(pack) == INTAKE_PACK_LIMIT


@pytest.mark.asyncio
async def test_three_concurrent_draft_jobs_reach_done():
    async def run_one(pid: uuid.UUID) -> dict:
        await set_job(None, pid, "queued", 0, 13)
        await set_job(None, pid, "running", 0, 13)
        for count in range(1, 14):
            await bump_progress(None, pid, count)
        await mark_status(None, pid, "done")
        job = await get_job(None, pid)
        assert job is not None
        return job

    pids = [uuid.uuid4() for _ in range(3)]
    results = await asyncio.gather(*(run_one(pid) for pid in pids))
    assert len(results) == 3
    for job in results:
        assert job["status"] == "done"
        assert job["drafted_count"] == 13
        assert job["total"] == 13
