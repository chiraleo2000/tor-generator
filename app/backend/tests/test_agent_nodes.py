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
