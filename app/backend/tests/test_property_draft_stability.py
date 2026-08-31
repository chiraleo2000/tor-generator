"""Property tests for draft job store, submit completeness, and SSE contract.

Feature: local-llm-verification-aws-migration-plan
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from app.api.v1.endpoints.projects import missing_submit_sections, officer_can_submit
from app.deps import get_current_user, get_db
from app.domain.slots import FACT_REQUIRED_SLOTS
from app.domain.tor_sections import TOR_SECTION_ORDER
from app.draft_job_store import bump_progress, clear_memory, get_job, mark_status, set_job
from app.main import app
from app.models.project import Project
from app.models.user import User
from app.services.intake_service import empty_slot_map

USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")
PROJECT_ID = uuid.UUID("abcdefab-abcd-abcd-abcd-abcdefabcdef")
STATUSES = ["queued", "running", "done", "failed"]


def _row(section_key: str, filled: bool):
    row = MagicMock()
    row.section_key = section_key
    row.sub_key = None
    row.content = f"เนื้อหา {section_key}" if filled else ""
    row.ai_draft = ""
    return row


@pytest.fixture(autouse=True)
def _reset_store():
    from app.api.v1.endpoints import draft_chat as draft_chat_ep

    draft_chat_ep._DRAFT_JOBS.clear()
    clear_memory()
    app.state.redis = None
    yield
    draft_chat_ep._DRAFT_JOBS.clear()
    clear_memory()
    app.dependency_overrides.clear()


@pytest.mark.property
@settings(max_examples=100, deadline=None)
@given(
    status=st.sampled_from(STATUSES),
    drafted_count=st.integers(min_value=0, max_value=13),
    total=st.integers(min_value=1, max_value=13),
)
def test_property_8_job_status_readable_across_instances(
    status: str, drafted_count: int, total: int
):
    """Feature: local-llm-verification-aws-migration-plan, Property 8: สถานะงานร่างอ่านได้ข้ามอินสแตนซ์"""

    async def body():
        pid = uuid.uuid4()
        written = await set_job(None, pid, status, min(drafted_count, total), total)
        read_a = await get_job(None, pid)
        read_b = await get_job(None, pid)
        assert read_a == read_b
        assert read_a["status"] == written["status"]
        assert read_a["drafted_count"] == written["drafted_count"]
        assert read_a["total"] == written["total"]

    asyncio.run(body())


@pytest.mark.property
@settings(max_examples=100, deadline=None)
@given(
    flags=st.lists(st.booleans(), min_size=13, max_size=13),
    status=st.sampled_from(["draft", "rejected", "in_review", "approved", "archived"]),
)
def test_property_9_submit_rejected_iff_incomplete_or_bad_status(
    flags: list[bool], status: str
):
    """Feature: local-llm-verification-aws-migration-plan, Property 9: submit ถูกปฏิเสธก็ต่อเมื่อไม่ครบหรือสถานะผิด"""
    rows = [_row(key, filled) for key, filled in zip(TOR_SECTION_ORDER, flags, strict=True)]
    missing = missing_submit_sections(rows)
    allowed = officer_can_submit(status, 4, True)
    rejected = bool(missing) or not allowed
    assert rejected is (len(missing) > 0 or status not in {"draft", "rejected", "archived"})
    if status in {"draft", "rejected"}:
        assert rejected is (not all(flags))
    if status == "archived":
        assert rejected is (not all(flags))
    if status in {"in_review", "approved"}:
        assert rejected is True
    assert allowed is officer_can_submit(status, 4, True)
    assert (not missing) is all(flags)


@pytest.mark.property
@settings(max_examples=100, deadline=None)
@given(fail_mask=st.lists(st.booleans(), min_size=13, max_size=13))
def test_property_10_draft_job_reaches_terminal_status(fail_mask: list[bool]):
    """Feature: local-llm-verification-aws-migration-plan, Property 10: งานร่างเดินไปถึงสถานะปลายทางเสมอ"""

    async def body():
        pid = uuid.uuid4()
        await set_job(None, pid, "running", 0, 13)
        drafted = 0
        for failed in fail_mask:
            if failed:
                continue
            drafted += 1
            await bump_progress(None, pid, drafted)
        await mark_status(None, pid, "done" if drafted == 13 else "failed")
        job = await get_job(None, pid)
        assert job["status"] in {"done", "failed"}
        assert job["status"] != "running"
        assert job["drafted_count"] == drafted

    asyncio.run(body())


@pytest.mark.property
def test_property_11_sse_contract_compatible():
    """Feature: local-llm-verification-aws-migration-plan, Property 11: สัญญา SSE เข้ากันได้กับ frontend เดิม"""
    user = MagicMock(spec=User)
    user.id = USER_ID
    user.role = "officer"
    user.email = "test@example.go.th"
    user.name = "Test User"

    async def override_user():
        return user

    app.dependency_overrides[get_current_user] = override_user

    slots = empty_slot_map()
    for key in FACT_REQUIRED_SLOTS:
        slots[key] = {"content": "ข้อมูลโครงการทดสอบ", "status": "filled", "sources": []}
    project = MagicMock(spec=Project)
    project.id = PROJECT_ID
    project.owner_id = USER_ID
    project.name = "โครงการทดสอบ"
    project.analysis_json = {
        "slot_map": slots,
        "ready_to_compose": True,
        "analyzed": True,
    }
    project.extracted_fields = {}
    project.current_phase = 3
    project.created_at = datetime(2026, 8, 24, tzinfo=timezone.utc)
    project.updated_at = datetime(2026, 8, 24, tzinfo=timezone.utc)

    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=result)

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db

    persist = AsyncMock()
    persist.commit = AsyncMock()
    persist.add = MagicMock()
    persist_result = MagicMock()
    row = MagicMock()
    row.content = "ร่างที่มีอยู่แล้วอย่างน้อยยี่สิบตัวอักษร"
    row.ai_draft = "ร่างที่มีอยู่แล้วอย่างน้อยยี่สิบตัวอักษร"
    row.is_approved = False
    persist_result.scalar_one_or_none.return_value = row
    persist.execute = AsyncMock(return_value=persist_result)

    class _SessionCM:
        def __init__(self, inner):
            self._inner = inner

        async def __aenter__(self):
            return self._inner

        async def __aexit__(self, *_args):
            return False

    app.state.db_session_factory = lambda: _SessionCM(persist)

    async def existing(*_args, **_kwargs):
        return "ร่างที่มีอยู่แล้วอย่างน้อยยี่สิบตัวอักษร"

    client = TestClient(app, raise_server_exceptions=False)
    with (
        patch("app.api.v1.endpoints.draft_chat._existing_section_text", side_effect=existing),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        with client.stream("POST", f"/api/v1/projects/{PROJECT_ID}/draft-chat/start") as response:
            body = b"".join(response.iter_bytes()).decode("utf-8")
    assert response.status_code == 200
    events = [
        line[len("event: "):].strip()
        for line in body.splitlines()
        if line.startswith("event: ")
    ]
    assert events[0] == "progress"
    assert "section_done" in events
    assert events[-1] == "all_done"
    assert "drafted_count" in body
    assert "total" in body
