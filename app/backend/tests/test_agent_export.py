"""Agent export persist paths with mocked DB."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app import infra as runtime
from app.services import agent_export


@pytest.mark.asyncio
async def test_persist_and_export_without_session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime, "session_factory", None)
    urls = await agent_export.persist_and_export({"project_id": str(uuid4())})
    assert urls == {"docx": None, "pdf": None}


@pytest.mark.asyncio
async def test_trigger_export_without_minio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime, "minio_client", None)
    urls = await agent_export._trigger_export(MagicMock(), MagicMock())
    assert urls == {"docx": None, "pdf": None}


@pytest.mark.asyncio
async def test_trigger_export_maps_file_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime, "minio_client", MagicMock())
    job = SimpleNamespace(
        files=[
            SimpleNamespace(format="pdf", download_url="http://p"),
            SimpleNamespace(format="docx", download_url="http://d"),
        ]
    )
    with patch(
        "app.services.export_service.ExportService.trigger_export",
        new_callable=AsyncMock,
        return_value=job,
    ):
        urls = await agent_export._trigger_export(MagicMock(), MagicMock())
    assert urls["pdf"] == "http://p"
    assert urls["docx"] == "http://d"


class _AsyncSession:
    def __init__(self, execute_values: list) -> None:
        self._execute_values = list(execute_values)
        self.added: list = []
        self.committed = False

    async def execute(self, _query):
        return self._execute_values.pop(0)

    def add(self, obj) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, _obj) -> None:
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False


@pytest.mark.asyncio
async def test_persist_and_export_writes_sections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = MagicMock()
    project_result = MagicMock()
    project_result.scalar_one_or_none.return_value = project
    section_result = MagicMock()
    section_result.scalar_one_or_none.return_value = None
    version_result = MagicMock()
    version_result.scalars.return_value.all.return_value = []
    session = _AsyncSession([project_result, section_result, version_result])
    monkeypatch.setattr(runtime, "session_factory", lambda: session)
    with (
        patch("app.services.agent_export.TOR_SECTION_ORDER", ["s1"]),
        patch(
            "app.services.agent_export.apply_slot_map_to_sections",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.agent_export._trigger_export",
            new_callable=AsyncMock,
            return_value={"docx": "d", "pdf": "p"},
        ),
    ):
        urls = await agent_export.persist_and_export(
            {
                "project_id": str(uuid4()),
                "section_drafts": {"s1": "ร่างหมวดหนึ่ง"},
                "slot_map": {},
                "draft_quality_scores": {"s1": 80},
            }
        )
    assert urls == {"docx": "d", "pdf": "p"}
    assert session.committed is True
    assert session.added


@pytest.mark.asyncio
async def test_persist_and_export_missing_project(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing = MagicMock()
    missing.scalar_one_or_none.return_value = None
    session = _AsyncSession([missing])
    monkeypatch.setattr(runtime, "session_factory", lambda: session)
    with patch(
        "app.services.agent_export.apply_slot_map_to_sections",
        new_callable=AsyncMock,
    ):
        with pytest.raises(ValueError, match="ไม่พบโครงการ"):
            await agent_export.persist_and_export({"project_id": str(uuid4())})


@pytest.mark.asyncio
async def test_persist_and_export_updates_existing_and_versions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = MagicMock()
    project_result = MagicMock()
    project_result.scalar_one_or_none.return_value = project
    existing = SimpleNamespace(content="", ai_draft="")
    section_result = MagicMock()
    section_result.scalar_one_or_none.return_value = existing
    version_result = MagicMock()
    version_result.scalars.return_value.all.return_value = [SimpleNamespace(version_number=3)]
    session = _AsyncSession([project_result, section_result, version_result])
    monkeypatch.setattr(runtime, "session_factory", lambda: session)
    with (
        patch("app.services.agent_export.TOR_SECTION_ORDER", ["s1"]),
        patch(
            "app.services.agent_export.apply_slot_map_to_sections",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.agent_export._trigger_export",
            new_callable=AsyncMock,
            return_value={"docx": None, "pdf": None},
        ),
    ):
        await agent_export.persist_and_export(
            {
                "project_id": str(uuid4()),
                "section_drafts": {"s1": "ร่างใหม่"},
                "slot_map": {},
            }
        )
    assert existing.content == "ร่างใหม่"
    assert existing.ai_draft == "ร่างใหม่"
    version = session.added[0]
    assert version.version_number == 4


@pytest.mark.asyncio
async def test_persist_and_export_skips_blank_drafts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = MagicMock()
    project_result = MagicMock()
    project_result.scalar_one_or_none.return_value = project
    version_result = MagicMock()
    version_result.scalars.return_value.all.return_value = []
    session = _AsyncSession([project_result, version_result])
    monkeypatch.setattr(runtime, "session_factory", lambda: session)
    with (
        patch("app.services.agent_export.TOR_SECTION_ORDER", ["s1"]),
        patch(
            "app.services.agent_export.apply_slot_map_to_sections",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.agent_export._trigger_export",
            new_callable=AsyncMock,
            return_value={"docx": None, "pdf": None},
        ),
    ):
        await agent_export.persist_and_export(
            {"project_id": str(uuid4()), "section_drafts": {"s1": "  "}, "slot_map": {}}
        )
    assert len(session.added) == 1


@pytest.mark.asyncio
async def test_trigger_export_filename_and_empty_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime, "minio_client", MagicMock())
    job = SimpleNamespace(
        files=[
            SimpleNamespace(filename="out.pdf", download_url="http://p"),
            SimpleNamespace(filename="out.docx", download_url="http://d"),
        ]
    )
    with patch(
        "app.services.export_service.ExportService.trigger_export",
        new_callable=AsyncMock,
        return_value=job,
    ):
        urls = await agent_export._trigger_export(MagicMock(), MagicMock())
    assert urls["pdf"] == "http://p"
    assert urls["docx"] == "http://d"

    with patch(
        "app.services.export_service.ExportService.trigger_export",
        new_callable=AsyncMock,
        return_value=SimpleNamespace(files=None),
    ):
        empty = await agent_export._trigger_export(MagicMock(), MagicMock())
    assert empty == {"docx": None, "pdf": None}
