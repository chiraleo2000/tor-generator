"""ExportService retry and MinIO upload unit tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.export_service import ExportJob, ExportService, ProjectExportSnapshot


def _snapshot() -> ProjectExportSnapshot:
    return ProjectExportSnapshot(
        id=uuid.uuid4(),
        name="โครงการทดสอบ",
        ministry="กระทรวงดิจิทัลฯ",
        budget=1_000_000,
        project_type="it",
    )


@pytest.fixture(autouse=True)
def _clear_jobs():
    ExportService._jobs.clear()
    ExportService._jobs_by_id.clear()
    yield
    ExportService._jobs.clear()
    ExportService._jobs_by_id.clear()


@pytest.mark.asyncio
async def test_retry_succeeds_on_second_attempt():
    job = ExportJob(uuid.uuid4(), uuid.uuid4())
    calls = {"n": 0}

    async def fake_generate(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("minio unavailable")
        job.status = "completed"

    with (
        patch.object(ExportService, "_generate_and_upload", side_effect=fake_generate),
        patch("app.services.export_service.asyncio.sleep", new_callable=AsyncMock),
    ):
        await ExportService._attempt_export_with_retry(
            AsyncMock(), MagicMock(), _snapshot(), job
        )

    assert calls["n"] == 2
    assert job.retry_count == 1
    assert job.status == "completed"


@pytest.mark.asyncio
async def test_retry_fails_after_second_attempt(monkeypatch: pytest.MonkeyPatch):
    job = ExportJob(uuid.uuid4(), uuid.uuid4())

    async def always_fail(*_args, **_kwargs):
        raise RuntimeError("still down")

    monkeypatch.setattr(ExportService, "_generate_and_upload", always_fail)
    monkeypatch.setattr("app.services.export_service.asyncio.sleep", AsyncMock())
    db = AsyncMock()
    minio = MagicMock()
    snap = _snapshot()
    with pytest.raises(RuntimeError, match="still down"):
        await ExportService._attempt_export_with_retry(db, minio, snap, job)

    assert job.retry_count == 1
    assert job.status == "failed"
    assert job.error_message is not None


def test_upload_to_minio_puts_object():
    client = MagicMock()
    ExportService._upload_to_minio(
        client,
        "tor-documents",
        "exports/a/tor_document.docx",
        b"docx-bytes",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    client.put_object.assert_called_once()
    args, kwargs = client.put_object.call_args
    assert args[0] == "tor-documents"
    assert args[1] == "exports/a/tor_document.docx"
    assert kwargs["length"] == len(b"docx-bytes")


@pytest.mark.asyncio
async def test_generate_and_upload_completes_job():
    db = AsyncMock()
    main = MagicMock()
    main.sub_key = None
    main.section_key = "s1"
    main.content = "ความเป็นมา"
    sub = MagicMock()
    sub.sub_key = "s4.1"
    sub.section_key = "s4"
    sub.content = "ขอบเขต"
    result = MagicMock()
    result.scalars.return_value.all.return_value = [main, sub]
    db.execute = AsyncMock(return_value=result)

    minio = MagicMock()
    minio.presigned_get_object.return_value = "https://minio.example/file"
    job = ExportJob(uuid.uuid4(), uuid.uuid4())
    docx = MagicMock()
    docx.generate.return_value = b"docx-bytes"

    with (
        patch("app.services.export_service.DOCXGenerator", return_value=docx),
        patch.object(ExportService, "_generate_pdf", new_callable=AsyncMock, return_value=b"pdf-bytes"),
        patch.object(ExportService, "_upload_to_minio"),
    ):
        await ExportService._generate_and_upload(db, minio, _snapshot(), job)

    assert job.status == "completed"
    assert [item.format for item in job.files] == ["docx", "pdf"]


@pytest.mark.asyncio
async def test_run_export_marks_timeout_and_unexpected_errors():
    job = ExportJob(uuid.uuid4(), uuid.uuid4())

    async def timeout_wait(coro, timeout=None):
        coro.close()
        raise TimeoutError()

    async def error_wait(coro, timeout=None):
        coro.close()
        raise RuntimeError("disk full")

    with patch("app.services.export_service.asyncio.wait_for", side_effect=timeout_wait):
        await ExportService._run_export_with_retry(
            AsyncMock(), MagicMock(), _snapshot(), job, session_factory=None
        )
    assert job.status == "failed"
    assert job.error_message is not None

    job2 = ExportJob(uuid.uuid4(), uuid.uuid4())
    with patch("app.services.export_service.asyncio.wait_for", side_effect=error_wait):
        await ExportService._run_export_with_retry(
            AsyncMock(), MagicMock(), _snapshot(), job2, session_factory=None
        )
    assert job2.status == "failed"
    assert "disk full" in (job2.error_message or "")
