"""Unit tests for agent ingest/confirm/export node guards."""

from __future__ import annotations

import pytest

from app.orchestrator.agent_nodes import confirm_node, export_node, ingest_node
from app.services.agent_workflow import serializable_state
from app.services.intake_service import empty_slot_map


@pytest.mark.asyncio
async def test_ingest_requires_material():
    result = await ingest_node({"project_id": "x", "pending_files": [], "free_text": ""})
    assert result["phase"] == "error"


@pytest.mark.asyncio
async def test_ingest_uses_existing_texts():
    result = await ingest_node(
        {
            "project_id": "x",
            "intake_texts": [{"name": "a.txt", "text": "hello"}],
            "pending_files": [],
            "free_text": "",
        }
    )
    assert result["phase"] == "mapping"
    assert result["total_chars"] == 5


def test_confirm_requires_flag():
    result = confirm_node({"user_confirmed": False})
    assert result["phase"] == "confirming"
    result = confirm_node({"user_confirmed": True})
    assert result["phase"] == "drafting"


@pytest.mark.asyncio
async def test_export_requires_ack():
    result = await export_node(
        {
            "slot_map": empty_slot_map(),
            "sections_acknowledged": [],
            "section_drafts": {},
        }
    )
    assert result["phase"] == "human_review"


def test_serializable_state_drops_upload_handles():
    payload = serializable_state({"pending_files": [object()], "phase": "idle"})
    assert "pending_files" not in payload
    assert payload["phase"] == "idle"


def test_handle_error_node_defaults() -> None:
    from app.orchestrator.agent_nodes import handle_error_node, human_review_node

    assert handle_error_node({})["phase"] == "error"
    approved = human_review_node({"human_approved": True, "sections_acknowledged": []})
    assert approved["phase"] == "exporting"
    feedback = human_review_node({"human_feedback": "แก้ s1"})
    assert feedback["phase"] == "drafting"
    waiting = human_review_node({})
    assert waiting["phase"] == "human_review"


@pytest.mark.asyncio
async def test_detect_gaps_ready_goes_confirming() -> None:
    from unittest.mock import patch

    from app.orchestrator.agent_nodes import detect_gaps_node

    with (
        patch("app.orchestrator.agent_nodes.GapDetector") as detector_cls,
        patch("app.orchestrator.agent_nodes.compute_ready", return_value=True),
        patch("app.orchestrator.agent_nodes.build_coverage_map", return_value=[]),
        patch("app.orchestrator.agent_nodes.compute_readiness_score", return_value=1.0),
    ):
        detector_cls.return_value.detect_gaps.return_value = []
        result = await detect_gaps_node({"slot_map": {}, "gap_iteration": 0})
    assert result["phase"] == "confirming"


@pytest.mark.asyncio
async def test_detect_gaps_max_iteration() -> None:
    from unittest.mock import patch

    from app.orchestrator.agent_nodes import MAX_GAP_ITERATIONS, detect_gaps_node

    with (
        patch("app.orchestrator.agent_nodes.build_coverage_map", return_value=[]),
        patch("app.orchestrator.agent_nodes.compute_readiness_score", return_value=0.1),
        patch("app.orchestrator.agent_nodes.compute_ready", return_value=False),
    ):
        result = await detect_gaps_node(
            {"slot_map": {}, "gap_iteration": MAX_GAP_ITERATIONS}
        )
    assert result["phase"] == "confirming"
    assert result["gap_questions"] == []


@pytest.mark.asyncio
async def test_ingest_process_batch_success() -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.orchestrator.agent_nodes import ingest_node

    service = MagicMock()
    service.process_batch = AsyncMock(
        return_value=SimpleNamespace(
            files=[
                SimpleNamespace(
                    name="a.pdf",
                    size=1,
                    content_hash="h",
                    status="ok",
                    chars=10,
                    error=None,
                )
            ],
            texts=[{"name": "a.pdf", "text": "ก" * 60}],
            total_chars=60,
            timed_out=True,
        )
    )
    with patch("app.orchestrator.agent_nodes.IntakeIngestionService", return_value=service):
        result = await ingest_node(
            {
                "project_id": "12345678-1234-5678-1234-567812345678",
                "pending_files": [object()],
                "free_text": "ก" * 60,
            }
        )
    assert result["phase"] == "mapping"
    assert result["total_chars"] == 60
    assert any("หมดเวลา" in item for item in result["warnings"])


@pytest.mark.asyncio
async def test_ingest_process_batch_failure() -> None:
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.orchestrator.agent_nodes import ingest_node

    service = MagicMock()
    service.process_batch = AsyncMock(side_effect=RuntimeError("minio down"))
    with patch("app.orchestrator.agent_nodes.IntakeIngestionService", return_value=service):
        result = await ingest_node(
            {
                "project_id": "12345678-1234-5678-1234-567812345678",
                "pending_files": [object()],
                "free_text": "ก" * 60,
            }
        )
    assert result["phase"] == "error"
    assert "minio down" in result["error"]


@pytest.mark.asyncio
async def test_map_sections_and_fill_slot() -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.orchestrator.agent_nodes import fill_slot_node, map_sections_node

    mapper = MagicMock()
    mapper.map_content = AsyncMock(
        return_value=SimpleNamespace(slot_map={"s1": {"content": "ก"}}, error="บางส่วน")
    )
    mapper.incremental_update = AsyncMock(
        return_value=SimpleNamespace(
            slot_map={"s1": {"content": "ข"}},
            affected=["s1"],
            error=None,
        )
    )
    cache = MagicMock()
    cache.set_slot_map = AsyncMock()
    with (
        patch("app.orchestrator.agent_nodes.SectionMapper", return_value=mapper),
        patch("app.orchestrator.agent_nodes.SessionCacheService", return_value=cache),
        patch("app.orchestrator.agent_nodes.build_coverage_map", return_value=[]),
        patch("app.orchestrator.agent_nodes.compute_readiness_score", return_value=0.5),
        patch("app.orchestrator.agent_nodes.compute_ready", return_value=False),
    ):
        mapped = await map_sections_node(
            {
                "project_id": "p1",
                "intake_texts": [{"text": "เนื้อหา"}],
                "project_metadata": {},
            }
        )
        filled = await fill_slot_node(
            {
                "project_id": "p1",
                "last_answer": "วงเงินสองล้าน",
                "slot_map": {},
                "gap_questions": [],
            }
        )
        empty = await fill_slot_node({"last_answer": "  "})
    assert mapped["phase"] == "gap_filling"
    assert filled["gap_iteration"] == 1
    assert empty["error"] == "ไม่มีคำตอบ"


@pytest.mark.asyncio
async def test_detect_gaps_asks_questions() -> None:
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.orchestrator.agent_nodes import detect_gaps_node

    detector = MagicMock()
    detector.detect_gaps.return_value = ["s1"]
    detector.generate_questions = AsyncMock(return_value=[{"slot": "s1"}])
    with (
        patch("app.orchestrator.agent_nodes.GapDetector", return_value=detector),
        patch("app.orchestrator.agent_nodes.build_coverage_map", return_value=[]),
        patch("app.orchestrator.agent_nodes.compute_readiness_score", return_value=0.1),
        patch("app.orchestrator.agent_nodes.compute_ready", return_value=False),
    ):
        result = await detect_gaps_node({"slot_map": {}, "gap_iteration": 0})
    assert result["phase"] == "gap_filling"
    assert result["gap_questions"]


@pytest.mark.asyncio
async def test_draft_validate_and_export_nodes() -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.orchestrator.agent_nodes import (
        draft_all_node,
        export_node,
        validate_draft_node,
    )

    generator = MagicMock()
    generator.generate_all = AsyncMock(
        return_value=SimpleNamespace(
            warnings=[],
            section_drafts={"s1": "ร่าง"},
            sections_pending=[],
            draft_quality_scores={"s1": 80},
            overall_quality_score=80,
        )
    )
    generator.validate_document.return_value = SimpleNamespace(
        findings=[SimpleNamespace()],
        quality_score=70,
    )
    generator.auto_correct = AsyncMock(return_value="แก้แล้ว")
    from app.services.full_draft_generator import FullDraftGenerator as RealGenerator

    with (
        patch.object(RealGenerator, "generate_all", generator.generate_all),
        patch.object(RealGenerator, "validate_document", generator.validate_document),
        patch.object(RealGenerator, "auto_correct", generator.auto_correct),
        patch(
            "app.rule_engine.engine.finding_as_dict",
            return_value={"severity": "error", "affected_section": "s1"},
        ),
        patch("app.orchestrator.agent_nodes.TOR_SECTION_ORDER", ["s1"]),
        patch(
            "app.orchestrator.agent_nodes.get_settings",
            return_value=MagicMock(deployment_mode="on_prem"),
        ),
    ):
        drafted = await draft_all_node({"slot_map": {}, "project_id": "p1"})
        validated = await validate_draft_node(
            {
                "section_drafts": {"s1": "ร่าง"},
                "correction_attempts": {},
                "draft_quality_scores": {"s1": 80},
                "slot_map": {},
            }
        )
    assert drafted["phase"] == "validating"
    assert validated["phase"] == "drafting"

    with patch(
        "app.services.agent_export.persist_and_export",
        new_callable=AsyncMock,
        return_value={"docx": "d", "pdf": "p"},
    ):
        exported = await export_node(
            {
                "sections_acknowledged": ["s3", "s6", "s8", "s10", "s13"],
                "slot_map": empty_slot_map(),
            }
        )
    assert exported["phase"] == "complete"

    with patch(
        "app.services.agent_export.persist_and_export",
        new_callable=AsyncMock,
        side_effect=RuntimeError("export down"),
    ):
        failed = await export_node(
            {
                "sections_acknowledged": ["s3", "s6", "s8", "s10", "s13"],
                "slot_map": empty_slot_map(),
            }
        )
    assert failed["phase"] == "error"


def test_handle_error_preserves_message() -> None:
    from app.orchestrator.agent_nodes import handle_error_node

    assert handle_error_node({"error": "minio down"})["error"] == "minio down"


@pytest.mark.asyncio
async def test_map_sections_without_mapper_error() -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.orchestrator.agent_nodes import map_sections_node

    mapper = MagicMock()
    mapper.map_content = AsyncMock(
        return_value=SimpleNamespace(slot_map={"s1": {"content": "ก"}}, error=None)
    )
    cache = MagicMock()
    cache.set_slot_map = AsyncMock()
    with (
        patch("app.orchestrator.agent_nodes.SectionMapper", return_value=mapper),
        patch("app.orchestrator.agent_nodes.SessionCacheService", return_value=cache),
        patch("app.orchestrator.agent_nodes.build_coverage_map", return_value=[]),
        patch("app.orchestrator.agent_nodes.compute_readiness_score", return_value=0.5),
        patch("app.orchestrator.agent_nodes.compute_ready", return_value=False),
    ):
        mapped = await map_sections_node(
            {
                "project_id": "p1",
                "intake_texts": [{"text": "เนื้อหา"}, "skip"],
                "project_metadata": {},
                "warnings": [],
            }
        )
    assert mapped["phase"] == "gap_filling"
    assert mapped["error"] is None
    assert mapped["warnings"] == []
    cache.set_slot_map.assert_awaited()


@pytest.mark.asyncio
async def test_fill_slot_without_affected_keys() -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.orchestrator.agent_nodes import fill_slot_node

    mapper = MagicMock()
    mapper.incremental_update = AsyncMock(
        return_value=SimpleNamespace(slot_map={"s1": {"content": "ข"}}, affected=[], error=None)
    )
    cache = MagicMock()
    cache.set_slot_map = AsyncMock()
    with (
        patch("app.orchestrator.agent_nodes.SectionMapper", return_value=mapper),
        patch("app.orchestrator.agent_nodes.SessionCacheService", return_value=cache),
        patch("app.orchestrator.agent_nodes.build_coverage_map", return_value=[]),
        patch("app.orchestrator.agent_nodes.compute_readiness_score", return_value=0.2),
        patch("app.orchestrator.agent_nodes.compute_ready", return_value=False),
    ):
        filled = await fill_slot_node(
            {
                "project_id": "p1",
                "last_answer": "วงเงินสองล้าน",
                "slot_map": {},
                "gap_questions": [],
                "messages": [],
            }
        )
    assert filled["gap_iteration"] == 1
    assert filled["last_answer"] == ""
    roles = [item["role"] for item in filled["messages"]]
    assert roles == ["user"]


@pytest.mark.asyncio
async def test_detect_gaps_honors_state_max_iterations() -> None:
    from unittest.mock import MagicMock, patch

    from app.orchestrator.agent_nodes import detect_gaps_node

    detector = MagicMock()
    detector.detect_gaps.return_value = ["s1"]
    with (
        patch("app.orchestrator.agent_nodes.GapDetector", return_value=detector),
        patch("app.orchestrator.agent_nodes.build_coverage_map", return_value=[]),
        patch("app.orchestrator.agent_nodes.compute_readiness_score", return_value=0.1),
        patch("app.orchestrator.agent_nodes.compute_ready", return_value=False),
    ):
        result = await detect_gaps_node(
            {"slot_map": {}, "gap_iteration": 2, "max_gap_iterations": 2, "warnings": []}
        )
    assert result["phase"] == "confirming"
    assert result["gap_questions"] == []
    detector.generate_questions.assert_not_called()


@pytest.mark.asyncio
async def test_validate_draft_human_review_and_skips() -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.orchestrator.agent_nodes import validate_draft_node
    from app.services.full_draft_generator import FullDraftGenerator as RealGenerator

    with (
        patch.object(
            RealGenerator,
            "validate_document",
            return_value=SimpleNamespace(findings=[], quality_score=88),
        ),
        patch.object(RealGenerator, "auto_correct", new=AsyncMock()) as correct,
    ):
        clean = await validate_draft_node(
            {
                "section_drafts": {"s1": "ร่าง"},
                "correction_attempts": {},
                "draft_quality_scores": {},
                "slot_map": {},
            }
        )
    assert clean["phase"] == "human_review"
    assert clean["overall_quality_score"] == 88.0
    correct.assert_not_awaited()

    with (
        patch.object(
            RealGenerator,
            "validate_document",
            return_value=SimpleNamespace(findings=[object()], quality_score=40),
        ),
        patch(
            "app.rule_engine.engine.finding_as_dict",
            return_value={"severity": "error", "affected_section": "unknown"},
        ),
        patch.object(RealGenerator, "auto_correct", new=AsyncMock()) as correct,
        patch("app.orchestrator.agent_nodes.TOR_SECTION_ORDER", ["s1"]),
    ):
        skipped = await validate_draft_node(
            {
                "section_drafts": {"s1": "ร่าง"},
                "correction_attempts": {},
                "draft_quality_scores": {"s1": 40},
                "slot_map": {},
            }
        )
    assert skipped["phase"] == "human_review"
    correct.assert_not_awaited()

    with (
        patch.object(
            RealGenerator,
            "validate_document",
            return_value=SimpleNamespace(findings=[object()], quality_score=40),
        ),
        patch(
            "app.rule_engine.engine.finding_as_dict",
            return_value={"severity": "error", "affected_section": "s1"},
        ),
        patch.object(RealGenerator, "auto_correct", new=AsyncMock()) as correct,
        patch("app.orchestrator.agent_nodes.TOR_SECTION_ORDER", ["s1"]),
    ):
        exhausted = await validate_draft_node(
            {
                "section_drafts": {"s1": "ร่าง"},
                "correction_attempts": {"s1": 3},
                "draft_quality_scores": {"s1": 40},
                "slot_map": {},
            }
        )
    assert exhausted["phase"] == "human_review"
    correct.assert_not_awaited()


@pytest.mark.asyncio
async def test_ingest_with_files_ignores_existing_texts_shortcut() -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.orchestrator.agent_nodes import ingest_node

    service = MagicMock()
    service.process_batch = AsyncMock(
        return_value=SimpleNamespace(
            files=[],
            texts=[{"name": "a.txt", "text": "จากไฟล์"}],
            total_chars=7,
            timed_out=False,
        )
    )
    with patch("app.orchestrator.agent_nodes.IntakeIngestionService", return_value=service):
        result = await ingest_node(
            {
                "project_id": "12345678-1234-5678-1234-567812345678",
                "pending_files": [object()],
                "intake_texts": [{"name": "old.txt", "text": "เก่า"}],
                "free_text": "",
            }
        )
    assert result["phase"] == "mapping"
    assert result["total_chars"] == 7
    service.process_batch.assert_awaited()
