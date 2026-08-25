"""Shared pytest fixtures for model unit tests.

These fixtures provide sample model instances for testing instantiation
and field defaults without requiring a real database connection.
"""

import os
import sys
import uuid
from datetime import datetime

import pytest
from hypothesis import settings as hypothesis_settings

hypothesis_settings.register_profile("coverage", max_examples=8, deadline=None)
if os.environ.get("COVERAGE_FILE") or any(arg.startswith("--cov") for arg in sys.argv):
    hypothesis_settings.load_profile("coverage")


@pytest.fixture
def sample_user_id() -> uuid.UUID:
    """A fixed UUID for user references in tests."""
    return uuid.UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def sample_project_id() -> uuid.UUID:
    """A fixed UUID for project references in tests."""
    return uuid.UUID("abcdefab-abcd-abcd-abcd-abcdefabcdef")


@pytest.fixture
def sample_template_id() -> uuid.UUID:
    """A fixed UUID for template references in tests."""
    return uuid.UUID("11111111-2222-3333-4444-555555555555")


@pytest.fixture
def sample_document_id() -> uuid.UUID:
    """A fixed UUID for knowledge base document references in tests."""
    return uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


@pytest.fixture
def sample_timestamp() -> datetime:
    """A fixed timestamp for testing."""
    return datetime(2024, 8, 15, 10, 30, 0)


@pytest.fixture(autouse=True)
def _clear_ai_runtime_overlay():
    """Keep get_settings() tests isolated from admin overlay mutations."""
    from app.config import clear_runtime_overlay

    clear_runtime_overlay()
    yield
    clear_runtime_overlay()


@pytest.fixture(autouse=True)
def _disable_sglang_auto_promote(monkeypatch):
    """Unit tests must not probe the live SGLang container."""
    monkeypatch.setattr(
        "app.providers.factory.probe_sglang_health_sync",
        lambda _url="": False,
    )


@pytest.fixture
def sample_snapshot_data() -> dict:
    """Sample JSONB data for project version snapshots."""
    return {
        "step_1": {"name": "โครงการพัฒนาระบบ", "budget": 5000000},
        "step_2": {"problem": "ระบบเดิมไม่รองรับ"},
    }


@pytest.fixture
def sample_section_structure() -> dict:
    """Sample JSONB data for template section structure."""
    return {
        "sections": [
            {"key": "s1", "title": "ความเป็นมา", "required": True},
            {"key": "s2", "title": "วัตถุประสงค์", "required": True},
            {"key": "s3", "title": "คุณสมบัติผู้เสนอราคา", "required": True},
        ]
    }


@pytest.fixture
def sample_placeholder_guidance() -> dict:
    """Sample JSONB data for template placeholder guidance."""
    return {
        "s1": "อธิบายความเป็นมาและเหตุผลของโครงการ",
        "s2": "ระบุวัตถุประสงค์ของการจัดซื้อจัดจ้าง",
    }
