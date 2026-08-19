"""Property 9: ingestion file count and per-file size validation."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.agent_intake_service import (
    MAX_FILE_SIZE_BYTES,
    MAX_FILES_PER_REQUEST,
    BatchTooLargeError,
    IntakeIngestionService,
    validate_file_count,
)


@pytest.mark.property
@settings(max_examples=30, deadline=None)
@given(st.integers(min_value=21, max_value=80))
def test_more_than_20_files_rejected(count: int):
    with pytest.raises(BatchTooLargeError):
        validate_file_count(count)


@pytest.mark.property
@settings(max_examples=20, deadline=None)
@given(st.integers(min_value=0, max_value=20))
def test_upto_20_files_accepted(count: int):
    validate_file_count(count)


@pytest.mark.asyncio
async def test_oversized_file_rejected_others_proceed():
    service = IntakeIngestionService()
    big = SimpleNamespace(
        filename="big.pdf",
        content_type="application/pdf",
        read=lambda: b"x" * (MAX_FILE_SIZE_BYTES + 1),
    )
    small = SimpleNamespace(
        filename="ok.txt",
        content_type="text/plain",
        read=lambda: b"hello project",
    )
    result = await service.process_batch(
        project_id="11111111-1111-1111-1111-111111111111",
        files=[big, small],
        free_text=None,
        storage_backend="local",
    )
    statuses = {item.name: item.status for item in result.files}
    assert statuses["big.pdf"] == "error"
    assert result.files[0].error == "file_too_large"
    assert statuses["ok.txt"] == "ok"


def test_max_files_constant():
    assert MAX_FILES_PER_REQUEST == 20
    assert MAX_FILE_SIZE_BYTES == 50 * 1024 * 1024
