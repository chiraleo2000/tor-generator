"""Targeted coverage for remaining high-miss helpers (mocked I/O)."""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exceptions import AuthenticationError, NotFoundError, ValidationError
from app.schemas.auth import RegisterRequest
from app.services.auth_service import AuthService
from app.services.intake_service import empty_slot_map


class _Result:
    def __init__(self, value=None, rows=None):
        self._value = value
        self._rows = rows or []

    def scalar_one_or_none(self):
        return self._value

    def scalar_one(self):
        return self._value

    def scalars(self):
        mock = MagicMock()
        mock.all.return_value = self._rows
        return mock


class FakeSession:
    def __init__(self, value=None, rows=None):
        self.value = value
        self.rows = rows or []
        self.added: list = []
        self.committed = False

    async def execute(self, _stmt):
        return _Result(self.value, self.rows)

    async def get(self, _cls, _id):
        return self.value

    def add(self, obj):
        self.added.append(obj)

    async def delete(self, obj):
        self.added.append(("delete", obj))

    async def commit(self):
        self.committed = True

    async def flush(self):
        return None

    async def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False


# ---------------------------------------------------------------------------
# Azure Foundry / Bedrock providers
# ---------------------------------------------------------------------------


def test_azure_foundry_requires_key_endpoint_deployment():
    from app.providers.llm.azure_foundry_provider import AzureFoundryLLMProvider

    with pytest.raises(ValueError, match="API key"):
        AzureFoundryLLMProvider(api_key="", endpoint="https://e", deployment="d")
    with pytest.raises(ValueError, match="endpoint"):
        AzureFoundryLLMProvider(api_key="k", endpoint="", deployment="d")
    with pytest.raises(ValueError, match="deployment"):
        AzureFoundryLLMProvider(api_key="k", endpoint="https://e", deployment="")


def test_azure_foundry_constructs_client():
    from app.providers.llm.azure_foundry_provider import AzureFoundryLLMProvider

    with patch("app.providers.llm.azure_foundry_provider.AsyncAzureOpenAI") as client:
        provider = AzureFoundryLLMProvider(
            api_key="k", endpoint="https://e.openai.azure.com", deployment="gpt"
        )
    client.assert_called_once()
    assert provider._model_name == "gpt"


@pytest.mark.asyncio
async def test_bedrock_llm_invoke_and_stream_fallback():
    from app.providers.llm.bedrock_provider import BedrockLLMProvider

    client = MagicMock()
    client.converse.return_value = {
        "output": {"message": {"content": [{"text": "สวัสดี"}]}},
        "usage": {"inputTokens": 1, "outputTokens": 2, "totalTokens": 3},
        "stopReason": "end_turn",
    }
    client.converse_stream.side_effect = RuntimeError("no stream")
    with patch(
        "app.providers.bedrock_client.bedrock_runtime_client", return_value=client
    ):
        provider = BedrockLLMProvider(region="ap-southeast-1", model_id="m")
        response = await provider.invoke(
            [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}],
            max_tokens=16,
            temperature=0.1,
        )
        tokens = [token async for token in provider.stream([{"role": "user", "content": "x"}])]
    assert "สวัสดี" in response.content
    assert response.usage["total_tokens"] == 3
    assert tokens == ["สวัสดี"]


@pytest.mark.asyncio
async def test_bedrock_llm_timeout_and_connection_error():
    from app.providers.llm.bedrock_provider import BedrockLLMProvider

    client = MagicMock()
    client.converse.side_effect = RuntimeError("offline")
    with patch(
        "app.providers.bedrock_client.bedrock_runtime_client", return_value=client
    ):
        provider = BedrockLLMProvider(region="ap-southeast-1", model_id="m", timeout=1.0)
        with pytest.raises(ConnectionError, match="unreachable"):
            await provider.invoke([{"role": "user", "content": "x"}])

    client.converse.side_effect = None
    with patch(
        "app.providers.bedrock_client.bedrock_runtime_client", return_value=client
    ), patch("asyncio.wait_for", AsyncMock(side_effect=TimeoutError())):
        provider = BedrockLLMProvider(region="ap-southeast-1", model_id="m", timeout=1.0)
        with pytest.raises(TimeoutError, match="did not respond"):
            await provider.invoke([{"role": "user", "content": "x"}])


@pytest.mark.asyncio
async def test_bedrock_embedding_fit_and_batch():
    from app.providers.constants import EMBEDDING_DIMENSIONS
    from app.providers.embedding.bedrock_provider import (
        BedrockEmbeddingProvider,
        _fit_dimensions,
    )

    assert _fit_dimensions([1.0, 2.0], size=4) == [1.0, 2.0, 0.0, 0.0]
    assert _fit_dimensions([0.0] * 10, size=4) == [0.0, 0.0, 0.0, 0.0]

    client = MagicMock()
    body = MagicMock()
    body.read.return_value = json.dumps({"embedding": [0.2] * 4}).encode()
    client.invoke_model.return_value = {"body": body}
    with patch(
        "app.providers.bedrock_client.bedrock_runtime_client", return_value=client
    ):
        provider = BedrockEmbeddingProvider(region="ap-southeast-1", model_id="titan")
        vector = await provider.embed_query("วงเงิน")
        empty = await provider.embed_documents([])
        batch = await provider.embed_documents(["ก", "ข"])
    assert len(vector) == EMBEDDING_DIMENSIONS
    assert empty == []
    assert len(batch) == 2

    body.read.return_value = json.dumps({"embeddingsByType": {"float": [0.1]}}).encode()
    with patch(
        "app.providers.bedrock_client.bedrock_runtime_client", return_value=client
    ):
        provider = BedrockEmbeddingProvider(region="ap-southeast-1", model_id="titan")
        assert await provider.embed_query("x")

    body.read.return_value = json.dumps({}).encode()
    with patch(
        "app.providers.bedrock_client.bedrock_runtime_client", return_value=client
    ):
        provider = BedrockEmbeddingProvider(region="ap-southeast-1", model_id="titan")
        with pytest.raises(ValueError, match="missing vector"):
            await provider.embed_query("x")


def test_bedrock_runtime_client_with_keys_and_bearer():
    from app.providers.bedrock_client import bedrock_runtime_client

    fake_boto = MagicMock()
    client = MagicMock()
    fake_boto.client.return_value = client
    with patch.dict("sys.modules", {"boto3": fake_boto}):
        out = bedrock_runtime_client(
            region="ap-southeast-1",
            aws_access_key_id="AKIATEST",
            aws_secret_access_key="secret",
        )
        assert out is client
        bearer = bedrock_runtime_client(
            region="ap-southeast-1", bearer_token="tok-xyz"
        )
        assert bearer is client
        client.meta.events.register.assert_called()


def test_vector_store_lazy_qdrant_import():
    from app.providers import vector_store

    assert vector_store.QdrantProvider is not None
    with pytest.raises(AttributeError):
        getattr(vector_store, "NoSuchProvider")


# ---------------------------------------------------------------------------
# Review job store / auth service
# ---------------------------------------------------------------------------


def test_store_review_original_none_and_error():
    from app.services.review_job_store import store_review_original

    with patch("app.services.review_job_store.store_from_client", return_value=None):
        assert store_review_original(None, raw=b"x", filename="a.pdf", mime="application/pdf", owner_id=uuid.uuid4()) is None

    store = MagicMock()
    store.put_file.side_effect = RuntimeError("gridfs down")
    with patch("app.services.review_job_store.store_from_client", return_value=store):
        assert (
            store_review_original(
                MagicMock(),
                raw=b"x",
                filename="",
                mime="application/pdf",
                owner_id=uuid.uuid4(),
            )
            is None
        )

    store.put_file.side_effect = None
    store.put_file.return_value = {"gridfs_id": "abc"}
    with patch("app.services.review_job_store.store_from_client", return_value=store):
        assert (
            store_review_original(
                MagicMock(),
                raw=b"x",
                filename="a.pdf",
                mime="application/pdf",
                owner_id=uuid.uuid4(),
            )
            == "abc"
        )


@pytest.mark.asyncio
async def test_review_job_save_fetch_result():
    from app.models.review_job import ReviewJob
    from app.services.review_job_store import fetch_review_job, save_review_job, save_review_result

    job = ReviewJob()
    job.id = uuid.uuid4()
    job.owner_id = uuid.uuid4()
    session = FakeSession(value=job)
    saved = await save_review_job(session, job)
    assert saved is job
    assert session.committed is True
    found = await fetch_review_job(session, job.id, job.owner_id)
    assert found is job
    await save_review_result(session, job, {"ok": True})
    assert job.status == "completed"
    assert job.result_json == {"ok": True}


@pytest.mark.asyncio
async def test_auth_register_login_logout_paths():
    db = FakeSession(value=None)
    data = RegisterRequest(
        name="สมชาย",
        email="somchai@example.go.th",
        password="alllower1!",
        organization="กรม",
    )
    with pytest.raises(ValidationError, match="รหัสผ่าน"):
        await AuthService.register_user(db, data)

    data = RegisterRequest(
        name="สมชาย",
        email="somchai@example.go.th",
        password="SecureP@ss1",
        organization="กรม",
    )
    db.value = SimpleNamespace(email=data.email)
    with pytest.raises(ValidationError, match="อีเมลนี้ถูกใช้งานแล้ว"):
        await AuthService.register_user(db, data)

    db.value = None
    user = await AuthService.register_user(db, data)
    assert user.email == data.email
    assert db.added

    redis = MagicMock()
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    db.value = None
    with pytest.raises(AuthenticationError):
        await AuthService.login(db, redis, "missing@example.go.th", "SecureP@ss1")

    hashed = AuthService.hash_password("SecureP@ss1")
    live = SimpleNamespace(
        id=uuid.uuid4(),
        email=data.email,
        password_hash=hashed,
        role="officer",
    )
    db.value = live
    user, token = await AuthService.login(db, redis, data.email, "SecureP@ss1")
    assert user is live
    assert token
    redis.set.assert_awaited()

    db.value = live
    with pytest.raises(AuthenticationError):
        await AuthService.login(db, redis, data.email, "WrongP@ss1")

    await AuthService.logout(redis, token)
    redis.delete.assert_awaited()
    await AuthService.logout(None, token)


def test_auth_verify_password_bad_hash():
    assert AuthService.verify_password("x", "not-a-hash") is False


# ---------------------------------------------------------------------------
# Knowledge base helpers
# ---------------------------------------------------------------------------


def test_validate_kb_bytes_too_large_and_bad_type():
    from app.api.v1.endpoints.knowledge_base import MAX_FILE_SIZE_BYTES, _validate_kb_bytes

    with pytest.raises(ValidationError, match="ใหญ่เกินไป"):
        _validate_kb_bytes(b"x" * (MAX_FILE_SIZE_BYTES + 1), "application/pdf", "a.pdf")
    with patch(
        "app.api.v1.endpoints.knowledge_base.require_kb_upload",
        side_effect=ValueError("bad"),
    ):
        with pytest.raises(ValidationError, match="bad"):
            _validate_kb_bytes(b"%PDF", "application/pdf", "a.pdf")
    with patch(
        "app.api.v1.endpoints.knowledge_base.require_kb_upload",
        return_value="image/png",
    ):
        with pytest.raises(ValidationError, match="ไม่รองรับ"):
            _validate_kb_bytes(b"png", "image/png", "a.png")


def test_catalog_helpers():
    from app.api.v1.endpoints.knowledge_base import (
        _catalog_item,
        _catalog_payload,
        _catalog_visible,
        _doc_group,
    )
    from app.domain.corpus import GROUP_USER

    owned = SimpleNamespace(
        id=uuid.uuid4(),
        name="ของฉัน.pdf",
        file_type="pdf",
        category="other",
        chunk_count=2,
        processing_status="ready",
        error_message=None,
        uploaded_at=None,
        corpus_group=None,
        owner_id=uuid.uuid4(),
        scope="user",
    )
    shared = SimpleNamespace(
        id=uuid.uuid4(),
        name="กฎหมาย.pdf",
        file_type="pdf",
        category="law",
        chunk_count=1,
        processing_status="ready",
        error_message=None,
        uploaded_at=None,
        corpus_group="mandatory_handbook",
        owner_id=None,
        scope="global",
    )
    assert _doc_group(owned) == GROUP_USER
    assert _catalog_visible(shared, None) is True
    assert _catalog_visible(owned, None) is False
    assert _catalog_visible(owned, owned.owner_id) is True
    item = _catalog_item(owned)
    assert item["owner_id"] == str(owned.owner_id)
    payload = _catalog_payload([owned, shared], owned.owner_id)
    assert payload["totals"]["files"] == 2


@pytest.mark.asyncio
async def test_run_ingestion_success_and_no_factory():
    from app.api.v1.endpoints import knowledge_base as kb

    app = MagicMock()
    app.state.db_session_factory = None
    with patch.object(kb, "write_temp_bytes", AsyncMock(return_value="/tmp/x.pdf")), patch.object(
        kb, "unlink_path", AsyncMock()
    ), patch("app.providers.factory.ProviderFactory") as factory_cls:
        factory_cls.return_value.get_embedding.return_value = MagicMock()
        factory_cls.return_value.get_vector_store.return_value = MagicMock()
        await kb._run_ingestion(str(uuid.uuid4()), "a.pdf", b"%PDF", "application/pdf", app)

    session = FakeSession()
    app.state.db_session_factory = lambda: session
    result = SimpleNamespace(success=True, embedded_chunks=2, total_chunks=2, error_message=None)
    with patch.object(kb, "write_temp_bytes", AsyncMock(return_value="/tmp/x.pdf")), patch.object(
        kb, "unlink_path", AsyncMock()
    ), patch("app.providers.factory.ProviderFactory") as factory_cls, patch(
        "app.rag.ingestion.ingest_document", AsyncMock(return_value=result)
    ):
        factory_cls.return_value.get_embedding.return_value = MagicMock()
        factory_cls.return_value.get_vector_store.return_value = MagicMock()
        await kb._run_ingestion(str(uuid.uuid4()), "a.pdf", b"%PDF", "application/pdf", app)

    fail = SimpleNamespace(success=False, embedded_chunks=0, total_chunks=0, error_message="bad")
    with patch.object(kb, "write_temp_bytes", AsyncMock(return_value="/tmp/x.pdf")), patch.object(
        kb, "unlink_path", AsyncMock()
    ), patch("app.providers.factory.ProviderFactory") as factory_cls, patch(
        "app.rag.ingestion.ingest_document", AsyncMock(return_value=fail)
    ):
        factory_cls.return_value.get_embedding.return_value = MagicMock()
        factory_cls.return_value.get_vector_store.return_value = MagicMock()
        await kb._run_ingestion(str(uuid.uuid4()), "a.pdf", b"%PDF", "application/pdf", app)

    with patch.object(kb, "write_temp_bytes", AsyncMock(side_effect=RuntimeError("disk"))), patch.object(
        kb, "unlink_path", AsyncMock()
    ), patch("app.rag.ingestion._update_document_status", AsyncMock()):
        await kb._run_ingestion(str(uuid.uuid4()), "a.pdf", b"%PDF", "application/pdf", app)


@pytest.mark.asyncio
async def test_run_sync_mandatory_and_batch():
    from app.api.v1.endpoints import knowledge_base as kb

    app = MagicMock()
    app.state.db_session_factory = None
    app.state.mongo = MagicMock()
    await kb._run_sync_mandatory(wipe_baseline=True, app=app)

    session = FakeSession()
    app.state.db_session_factory = lambda: session
    stats = SimpleNamespace(as_dict=lambda: {"n": 1})
    with patch("app.rag.seed_corpus.sync_mandatory_sources", AsyncMock(return_value=stats)), patch(
        "app.storage.mongo_store.OriginalDocumentStore"
    ) as store_cls:
        store_cls.return_value.wipe_baseline.side_effect = RuntimeError("wipe")
        await kb._run_sync_mandatory(wipe_baseline=True, app=app)

    with patch.object(kb, "_batch_ingest_providers", return_value=(None, None, None)):
        await kb._run_batch_ingestion(["a"], app)

    settings = SimpleNamespace(minio_bucket="kb")
    with patch.object(
        kb, "_batch_ingest_providers", return_value=(settings, MagicMock(), MagicMock())
    ), patch.object(kb, "_ingest_one_batch_document", AsyncMock()):
        app.state.minio = MagicMock()
        await kb._run_batch_ingestion(["doc-1"], app)


def test_batch_ingest_providers_and_minio_read():
    from app.api.v1.endpoints import knowledge_base as kb

    with patch("app.providers.factory.ProviderFactory", side_effect=RuntimeError("no")):
        assert kb._batch_ingest_providers() == (None, None, None)

    minio = MagicMock()
    response = MagicMock()
    response.read.return_value = b"bytes"
    minio.get_object.return_value = response
    payload, err = kb._read_minio_object(minio, "b", "path")
    assert payload == b"bytes"
    assert err is None
    minio.get_object.side_effect = RuntimeError("missing")
    payload, err = kb._read_minio_object(minio, "b", "path")
    assert payload is None
    assert err


@pytest.mark.asyncio
async def test_ingest_one_batch_document_branches():
    from app.api.v1.endpoints import knowledge_base as kb

    settings = SimpleNamespace(minio_bucket="kb")
    session = FakeSession(value=None)

    def factory():
        return session

    await kb._ingest_one_batch_document(
        str(uuid.uuid4()), settings, MagicMock(), MagicMock(), factory, MagicMock()
    )

    doc = SimpleNamespace(
        name="a.pdf",
        file_type="pdf",
        storage_path="kb/a.pdf",
        corpus_group=None,
        scope="global",
        owner_id=None,
        processing_status="pending",
        error_message=None,
    )
    session.value = doc
    with patch.object(kb, "_read_minio_object", return_value=(None, "fail")):
        await kb._ingest_one_batch_document(
            str(uuid.uuid4()), settings, MagicMock(), MagicMock(), factory, MagicMock()
        )
        assert doc.processing_status == "failed"

    with patch.object(kb, "_read_minio_object", return_value=(b"%PDF", None)), patch.object(
        kb, "write_temp_bytes", AsyncMock(return_value="/tmp/a.pdf")
    ), patch.object(kb, "unlink_path", AsyncMock()), patch(
        "app.rag.ingestion.ingest_document",
        AsyncMock(
            return_value=SimpleNamespace(
                success=True, embedded_chunks=1, total_chunks=1, error_message=None
            )
        ),
    ):
        await kb._ingest_one_batch_document(
            str(uuid.uuid4()), settings, MagicMock(), MagicMock(), factory, MagicMock()
        )

    with patch.object(kb, "_read_minio_object", return_value=(b"%PDF", None)), patch.object(
        kb, "write_temp_bytes", AsyncMock(return_value="/tmp/a.pdf")
    ), patch.object(kb, "unlink_path", AsyncMock()), patch(
        "app.rag.ingestion.ingest_document",
        AsyncMock(
            return_value=SimpleNamespace(
                success=False, embedded_chunks=0, total_chunks=0, error_message="x"
            )
        ),
    ):
        await kb._ingest_one_batch_document(
            str(uuid.uuid4()), settings, MagicMock(), MagicMock(), factory, MagicMock()
        )

    with patch.object(kb, "_read_minio_object", side_effect=RuntimeError("boom")), patch.object(
        kb, "unlink_path", AsyncMock()
    ):
        await kb._ingest_one_batch_document(
            str(uuid.uuid4()), settings, MagicMock(), MagicMock(), factory, MagicMock()
        )


# ---------------------------------------------------------------------------
# Draft chat helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_draft_chat_job_and_status_helpers():
    import asyncio

    from app.api.v1.endpoints import draft_chat as dc
    from app.domain.tor_sections import TOR_SECTION_ORDER

    dc._DRAFT_JOBS.clear()
    pid = uuid.uuid4()
    session = FakeSession()

    def factory():
        return session

    async def existing(_factory, _pid, key):
        return "มีแล้ว" if key != "s13" else None

    with patch.object(dc, "_existing_section_text", side_effect=existing), patch.object(
        dc, "_draft_missing_section", AsyncMock(return_value=True)
    ), patch.object(dc, "set_job", AsyncMock()), patch.object(
        dc, "bump_progress", AsyncMock()
    ), patch.object(dc, "mark_status", AsyncMock()), patch.object(
        dc, "get_job", AsyncMock(return_value=None)
    ):
        job = dc._SeqDraft(
            session_factory=factory,
            project_id=pid,
            slot_map={},
            user_id=uuid.uuid4(),
            request_id="r",
            redis=None,
        )
        count = await dc._run_sequential_draft(job, remaining_passes=0)
        assert count == len(TOR_SECTION_ORDER)

    with patch.object(dc, "_existing_section_text", AsyncMock(return_value=None)), patch.object(
        dc, "_draft_missing_section", AsyncMock(side_effect=TimeoutError())
    ):
        job = dc._SeqDraft(factory, pid, {}, uuid.uuid4(), "r", None)
        assert await dc._try_draft_one_section(job, "s1") is False

    with patch.object(dc, "_existing_section_text", AsyncMock(return_value=None)), patch.object(
        dc, "_draft_missing_section", AsyncMock(side_effect=RuntimeError("x"))
    ):
        job = dc._SeqDraft(factory, pid, {}, uuid.uuid4(), "r", None)
        assert await dc._try_draft_one_section(job, "s1") is False

    hanging = asyncio.create_task(asyncio.sleep(60))
    dc._DRAFT_JOBS[str(pid)] = hanging
    again = await dc._ensure_draft_job(factory, pid, {}, uuid.uuid4(), "r", None)
    assert again is hanging
    hanging.cancel()
    dc._DRAFT_JOBS.clear()

    with patch.object(
        dc, "get_job", AsyncMock(return_value={"status": "running", "drafted_count": 1, "total": 13})
    ):
        assert await dc._ensure_draft_job(factory, pid, {}, uuid.uuid4(), "r", None) is None

    with patch.object(dc, "get_job", AsyncMock(return_value=None)), patch.object(
        dc, "set_job", AsyncMock()
    ), patch.object(dc, "_run_sequential_draft", AsyncMock(return_value=1)):
        created = await dc._ensure_draft_job(factory, pid, {}, uuid.uuid4(), "r", None)
        assert created is not None
        await created
        dc._DRAFT_JOBS.clear()


@pytest.mark.asyncio
async def test_draft_chat_streams_and_accept():
    import asyncio

    from app.api.v1.endpoints import draft_chat as dc

    pid = uuid.uuid4()
    session = FakeSession(value=None)

    def factory():
        return session

    events = [event async for event in dc._stream_accept_intent(factory, pid, None)]
    assert "error" in events[0]

    events = [event async for event in dc._stream_accept_intent(factory, pid, "s1")]
    assert "ยังไม่มีร่าง" in events[0]

    row = SimpleNamespace(is_approved=False)
    session.value = row
    events = [event async for event in dc._stream_accept_intent(factory, pid, "s1")]
    assert "accepted" in events[0]
    assert row.is_approved is True

    async def ping():
        return 2

    job = asyncio.create_task(ping())
    with patch.object(dc, "_emit_newly_done_sections", return_value=_empty_aiter()):
        out = [event async for event in dc._stream_attached_job_progress(job, factory, pid, set())]
    assert any("all_done" in event for event in out)

    with patch.object(
        dc, "get_job", AsyncMock(return_value={"status": "done", "drafted_count": 3})
    ), patch.object(dc, "_emit_newly_done_sections", return_value=_empty_aiter()):
        out = [
            event
            async for event in dc._stream_background_job_progress(None, factory, pid, set())
        ]
    assert any("all_done" in event for event in out)

    request = MagicMock()
    stream = dc._ChatStream(
        request=request,
        project_id=pid,
        section_key=None,
        intent="edit",
        detail="",
        slot_map={},
        user_id=uuid.uuid4(),
        request_id="r",
        session_factory=factory,
    )
    out = [event async for event in dc._stream_draft_chat_message(stream)]
    assert "กรุณาระบุหมวด" in out[0]

    stream.intent = "accept"
    stream.section_key = "s1"
    with patch.object(dc, "_stream_accept_intent", return_value=_sse_aiter("event: accepted\n\n")):
        out = [event async for event in dc._stream_draft_chat_message(stream)]
    assert out

    assert dc.section_draft_timeout("s4") > dc.section_draft_timeout("s1")
    with patch.dict("os.environ", {"DRAFT_SECTION_TIMEOUT_SECONDS": "nope"}):
        assert dc._section_timeout_seconds() == 180

    async def one():
        yield "a"
        yield "b"

    assert await dc._consume_sse(one()) == 2

    row = SimpleNamespace(content="เนื้อหา", ai_draft="ร่าง", is_approved=True)
    data, drafted = dc._draft_status_row("s1", row, s4_ready=False, s4_subs={})
    assert drafted is True
    assert data["human_confirmed"] is True
    data, drafted = dc._draft_status_row(
        "s4", None, s4_ready=True, s4_subs={"s4.1": "ขอบเขต"}
    )
    assert drafted is True


async def _empty_aiter():
    if False:
        yield ""


async def _sse_aiter(text: str):
    yield text


@pytest.mark.asyncio
async def test_draft_missing_section_and_s4_incomplete():
    from app.api.v1.endpoints import draft_chat as dc

    pid = uuid.uuid4()
    session = FakeSession(rows=[])

    def factory():
        return session

    job = dc._SeqDraft(factory, pid, {}, uuid.uuid4(), "r", None)
    with patch.object(dc, "_consume_sse", AsyncMock(return_value=0)):
        assert await dc._draft_missing_section(job, "s1") is False

    with patch.object(dc, "_consume_sse", AsyncMock(return_value=1)), patch.object(
        dc, "_iter_llm_section_sse", return_value=_empty_aiter()
    ):
        job = dc._SeqDraft(factory, pid, {}, uuid.uuid4(), "r", None)
        # parts stay empty → False
        assert await dc._draft_missing_section(job, "s2") is False

    with patch.object(dc, "_load_s4_rows", AsyncMock(return_value=[])), patch.object(
        dc, "_consume_sse", AsyncMock()
    ), patch.object(dc, "_s4_complete", return_value=False):
        assert await dc._draft_missing_s4(job) is False


@pytest.mark.asyncio
async def test_save_section_and_s4_bundle():
    from app.api.v1.endpoints import draft_chat as dc

    session = FakeSession(value=None)
    with patch(
        "app.domain.section_fields.persist_section_fields", side_effect=lambda _k, text: text
    ):
        await dc._save_section(session, uuid.uuid4(), "s1", "เนื้อหาหมวดหนึ่ง")
    assert session.added

    existing = SimpleNamespace(content="", ai_draft="")
    session.value = existing
    with patch(
        "app.domain.section_fields.persist_section_fields", side_effect=lambda _k, text: text
    ):
        await dc._save_section(session, uuid.uuid4(), "s1", "ใหม่")
    assert existing.content == "ใหม่"

    with patch(
        "app.api.v1.endpoints.draft_chat.split_scope_subsection_draft",
        return_value={"s4.1": "ขอบเขตงานหลัก"},
    ), patch.object(dc, "_upsert_sub", AsyncMock()), patch.object(
        dc, "_get_section", AsyncMock(return_value=None)
    ):
        await dc._save_s4_bundle(session, uuid.uuid4(), "เนื้อหา s4")


@pytest.mark.asyncio
async def test_draft_new_s4_sub_timeout_and_error():
    from contextlib import asynccontextmanager

    from app.api.v1.endpoints import draft_chat as dc
    from app.llm_admission import AdmissionTimeoutError

    work = dc._S4Work(
        redis=None,
        request_id="r",
        slot_map={},
        user_id=uuid.uuid4(),
        collected={},
        errors=[],
    )

    @asynccontextmanager
    async def timeout_admit(*_a, **_k):
        raise AdmissionTimeoutError("หมดเวลา")
        yield "rid"

    with patch.object(dc, "admit", timeout_admit):
        events = [event async for event in dc._draft_new_s4_sub(work, "s4.1", "ขอบเขต")]
    assert work.errors
    assert "section_error" in events[-1]

    work.errors.clear()

    async def boom(*_a, **_k):
        raise RuntimeError("llm")
        yield "x"

    @asynccontextmanager
    async def ok_admit(*_a, **_k):
        yield "rid"

    with patch.object(dc, "admit", ok_admit), patch.object(dc, "draft_scope_subsection", boom):
        events = [event async for event in dc._draft_new_s4_sub(work, "s4.1", "ขอบเขต")]
    assert "llm" in work.errors[0]


# ---------------------------------------------------------------------------
# Intake helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_intake_legal_and_llm_paths():
    from app.api.v1.endpoints import intake as intake_mod
    from app.rag.retrieval import RetrievalResult, RetrievedChunk

    empty, cites, degraded = await intake_mod._retrieve_legal_context("q", uuid.uuid4(), "both", False)
    assert empty == ""
    assert cites == []
    assert degraded is False

    chunk = RetrievedChunk(id="1", text="กฎหมาย", score=0.9, source_document="พ.ร.บ.")
    with patch(
        "app.api.v1.endpoints.intake.hybrid_retrieve",
        AsyncMock(return_value=(RetrievalResult(chunks=[chunk], query="q", top_k=3, actual_count=1), [{"type": "local"}], False, False)),
    ):
        context, citations, degraded = await intake_mod._retrieve_legal_context(
            "งวด", uuid.uuid4(), "weird", True
        )
    assert "กฎหมาย" in context
    assert citations

    prompt = intake_mod._intake_llm_user_prompt({"current_asking_slot": "s1"}, empty_slot_map(), "ตอบ", "")
    assert "ความเป็นมา" in prompt or "s1" in prompt

    with patch.object(intake_mod, "_persist_intake_assistant", AsyncMock()), patch(
        "app.api.v1.endpoints.intake.fill_reference_slot", AsyncMock(return_value="มาตรฐาน")
    ), patch("app.api.v1.endpoints.intake.apply_reference_to_slot", return_value="filled"):
        events = [
            event
            async for event in intake_mod._stream_reference_fill(
                session_maker=lambda: FakeSession(),
                project_id=uuid.uuid4(),
                room_id=uuid.uuid4(),
                slot_map=empty_slot_map(),
                analysis={"current_asking_slot": "s1"},
                ref_key="s10",
                filled_keys=["s10"],
                user_id=uuid.uuid4(),
            )
        ]
    assert any("done" in event for event in events)

    with patch.object(intake_mod, "_persist_intake_assistant", AsyncMock()), patch(
        "app.api.v1.endpoints.intake.apply_reference_to_slot", return_value="skipped"
    ), patch("app.api.v1.endpoints.intake.fill_reference_slot", AsyncMock(return_value="x")):
        events = [
            event
            async for event in intake_mod._stream_reference_fill(
                session_maker=lambda: FakeSession(),
                project_id=uuid.uuid4(),
                room_id=uuid.uuid4(),
                slot_map=empty_slot_map(),
                analysis={},
                ref_key="s10",
                filled_keys=[],
                user_id=uuid.uuid4(),
            )
        ]
    assert any("ข้อเท็จจริงอยู่แล้ว" in event for event in events)

    with patch.object(intake_mod, "_persist_intake_assistant", AsyncMock()):
        events = [
            event
            async for event in intake_mod._stream_reference_prompt(
                session_maker=lambda: FakeSession(),
                project_id=uuid.uuid4(),
                room_id=uuid.uuid4(),
                slot_map=empty_slot_map(),
                analysis={},
            )
        ]
    assert any("ดึงอ้างอิง" in event for event in events)

    with patch.object(intake_mod, "_persist_intake_assistant", AsyncMock()), patch.object(
        intake_mod, "_attach_legal_to_filled", AsyncMock(return_value="อ้างอิง\n")
    ):
        events = [
            event
            async for event in intake_mod._stream_filled_ack(
                session_maker=lambda: FakeSession(),
                project_id=uuid.uuid4(),
                room_id=uuid.uuid4(),
                slot_map=empty_slot_map(),
                filled_keys=["s1"],
                asking="s2",
                user_id=uuid.uuid4(),
                attach_legal=True,
            )
        ]
    assert any("done" in event for event in events)


@pytest.mark.asyncio
async def test_intake_llm_job_success_timeout_and_error():
    import asyncio

    from app.api.v1.endpoints.intake import _IntakeLlmWork, _run_intake_llm_job
    from app.llm_admission import AdmissionTimeoutError

    request = MagicMock()
    request.app.state.redis = None
    request.app.state.db_session_factory = lambda: FakeSession()
    work = _IntakeLlmWork(
        request=request,
        project=SimpleNamespace(id=uuid.uuid4(), analysis_json={}),
        room=SimpleNamespace(id=uuid.uuid4()),
        analysis={"current_asking_slot": "s1"},
        slot_map=empty_slot_map(),
        filled_keys=[],
        asking_key="s1",
        all_filled_now=False,
        request_id="rid",
        attached="",
        citations=[],
        degraded=False,
        user_prompt="ถาม",
    )
    queue: asyncio.Queue = asyncio.Queue()

    class _LLM:
        async def stream(self, *_a, **_k):
            yield "คำตอบ"

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def admit_ok(*_a, **_k):
        yield "rid"

    with patch("app.api.v1.endpoints.intake.admit", admit_ok), patch(
        "app.api.v1.endpoints.intake.ProviderFactory"
    ) as factory, patch(
        "app.api.v1.endpoints.intake._persist_llm_reply", AsyncMock()
    ):
        factory.return_value.get_llm.return_value = _LLM()
        await _run_intake_llm_job(work, queue)
    events = []
    while not queue.empty():
        events.append(await queue.get())
    assert any(item and item[0] == "done" for item in events)

    queue = asyncio.Queue()
    with patch("app.api.v1.endpoints.intake.admit", admit_ok), patch(
        "app.api.v1.endpoints.intake.ProviderFactory"
    ) as factory, patch(
        "app.api.v1.endpoints.intake._persist_llm_reply", AsyncMock()
    ):
        llm = MagicMock()

        async def boom(*_a, **_k):
            raise TimeoutError("llm")
            yield "x"

        llm.stream = boom
        factory.return_value.get_llm.return_value = llm
        await _run_intake_llm_job(work, queue)

    queue = asyncio.Queue()

    @asynccontextmanager
    async def admit_timeout(*_a, **_k):
        raise AdmissionTimeoutError("คิวเต็ม")
        yield "rid"

    with patch("app.api.v1.endpoints.intake.admit", admit_timeout), patch(
        "app.api.v1.endpoints.intake._persist_llm_reply", AsyncMock()
    ):
        await _run_intake_llm_job(work, queue)

    queue = asyncio.Queue()
    with patch("app.api.v1.endpoints.intake.admit", admit_ok), patch(
        "app.api.v1.endpoints.intake.ProviderFactory", side_effect=RuntimeError("no llm")
    ):
        await _run_intake_llm_job(work, queue)


# ---------------------------------------------------------------------------
# Drafting / wizard / files / extraction / custom RAG / agent intake
# ---------------------------------------------------------------------------


def test_drafting_helpers():
    from app.api.v1.endpoints.drafting import (
        _as_slot_map,
        _draft_from_state,
        _persist_keys_for_section,
        _template_payload,
        _user_input_for_draft,
    )

    assert _persist_keys_for_section("s4.1") == ("s4", "s4.1")
    assert _persist_keys_for_section("4.2")[0] == "s4"
    assert _persist_keys_for_section("s1") == ("s1", None)
    assert _as_slot_map({"slot_map": {"s1": {"content": "x"}}})["s1"]["content"] == "x"
    assert _as_slot_map({"slot_map": "nope"}) == {}
    assert _as_slot_map("nope") == {}
    project = SimpleNamespace(template_id=None, template=None, name="ป", ministry="ก", budget=1, project_type="it")
    assert _template_payload(project) == {}
    project.template_id = uuid.uuid4()
    project.template = SimpleNamespace(section_structure={"s1": {}}, placeholder_guidance={})
    assert "section_structure" in _template_payload(project)
    body = SimpleNamespace(section_key="s4", additional_context={"note": "x"})
    slots = empty_slot_map()
    slots["s4.1"] = {"content": "ขอบเขต", "status": "filled", "sources": []}
    user_input = _user_input_for_draft(project, [], body, slots, {})
    assert "scope_subslots" in user_input
    content, score, findings, rag_failed, error = _draft_from_state(
        {"best_draft_content": "สำรอง", "best_draft_score": 80, "rag_retrieval_failed": False}
    )
    assert content == "สำรอง"
    assert score == 80
    content, *_rest = _draft_from_state({"draft_content": "หลัก", "quality_score": 70})
    assert content == "หลัก"


@pytest.mark.asyncio
async def test_save_draft_section_and_persist_s4():
    from app.api.v1.endpoints.drafting import _persist_s4_from_draft, _save_draft_section

    session = FakeSession(value=None)
    with patch(
        "app.domain.section_fields.persist_section_fields", side_effect=lambda _k, text: text
    ):
        await _save_draft_section(session, uuid.uuid4(), "s1", None, "ร่าง", 80, [{"x": 1}])
    assert session.added

    existing = SimpleNamespace(ai_draft="", content="", quality_score=None, validation_findings=None)
    session.value = existing
    with patch(
        "app.domain.section_fields.persist_section_fields", side_effect=lambda _k, text: text
    ):
        await _save_draft_section(session, uuid.uuid4(), "s1", None, "ใหม่", 70, [])
    assert existing.content == "ใหม่"

    with patch(
        "app.api.v1.endpoints.drafting.split_scope_subsection_draft", return_value={}
    ), patch(
        "app.api.v1.endpoints.drafting._save_draft_section", AsyncMock()
    ) as save:
        await _persist_s4_from_draft(session, uuid.uuid4(), "ร่าง s4", 70, [], {})
        save.assert_awaited()

    with patch(
        "app.api.v1.endpoints.drafting.split_scope_subsection_draft",
        return_value={"s4.1": "ขอบเขต", "nope": "x"},
    ), patch(
        "app.api.v1.endpoints.drafting.scope_overview_from_subs", return_value="สรุป"
    ), patch(
        "app.api.v1.endpoints.drafting._save_draft_section", AsyncMock()
    ) as save:
        overview = await _persist_s4_from_draft(session, uuid.uuid4(), "ร่าง", 70, [], {})
        assert overview == "สรุป"
        assert save.await_count >= 2


@pytest.mark.asyncio
async def test_wizard_helpers():
    from app.api.v1.endpoints.wizard import (
        _build_snapshot_data,
        _get_next_version_number,
        _get_owned_project,
        _validate_step,
    )

    _validate_step(1)
    with pytest.raises(ValidationError, match="ขั้นตอน"):
        _validate_step(99)

    user = SimpleNamespace(id=uuid.uuid4())
    session = FakeSession(value=None)
    with pytest.raises(NotFoundError):
        await _get_owned_project(uuid.uuid4(), user, session)

    other = SimpleNamespace(owner_id=uuid.uuid4())
    session.value = other
    with pytest.raises(NotFoundError):
        await _get_owned_project(uuid.uuid4(), user, session)

    owned = SimpleNamespace(owner_id=user.id)
    session.value = owned
    assert await _get_owned_project(uuid.uuid4(), user, session) is owned

    session.value = 50
    assert await _get_next_version_number(uuid.uuid4(), session) == 50
    session.value = None
    assert await _get_next_version_number(uuid.uuid4(), session) == 1

    section = SimpleNamespace(
        section_key="s4",
        sub_key="s4.1",
        content="ค",
        ai_draft="ค",
        quality_score=70,
        is_approved=False,
        version=1,
    )
    session.rows = [section]
    snap = await _build_snapshot_data(uuid.uuid4(), session)
    assert "s4.s4.1" in snap or "s4.1" in snap or any("s4" in key for key in snap)


@pytest.mark.asyncio
async def test_extract_text_from_content_statuses(tmp_path):
    from app.api.v1.endpoints.files import _extract_text_from_content
    from app.rag.extraction import ExtractionResult

    path = tmp_path / "a.pdf"
    path.write_bytes(b"%PDF")
    with patch("app.api.v1.endpoints.files.write_temp_bytes", AsyncMock(return_value=str(path))), patch(
        "app.api.v1.endpoints.files.unlink_path", AsyncMock()
    ), patch(
        "app.rag.extraction.extract_text",
        return_value=ExtractionResult(text="ข้อความ", page_count=1, method="direct", warnings=[]),
    ):
        text, status, warnings = await _extract_text_from_content(b"%PDF", "application/pdf", "a.pdf")
    assert status == "completed"
    assert text

    with patch("app.api.v1.endpoints.files.write_temp_bytes", AsyncMock(return_value=str(path))), patch(
        "app.api.v1.endpoints.files.unlink_path", AsyncMock()
    ), patch(
        "app.rag.extraction.extract_text",
        return_value=ExtractionResult(text="", page_count=1, method="ocr", warnings=["OCR timed out"]),
    ):
        _text, status, _w = await _extract_text_from_content(b"%PDF", "application/pdf", "a.pdf")
    assert status == "timeout"

    with patch("app.api.v1.endpoints.files.write_temp_bytes", AsyncMock(return_value=str(path))), patch(
        "app.api.v1.endpoints.files.unlink_path", AsyncMock()
    ), patch(
        "app.rag.extraction.extract_text",
        return_value=ExtractionResult(text="", page_count=1, method="ocr", warnings=[]),
    ):
        _text, status, _w = await _extract_text_from_content(b"%PDF", "application/pdf", "a.pdf")
    assert status == "failed"

    with patch("app.api.v1.endpoints.files.write_temp_bytes", AsyncMock(side_effect=RuntimeError("disk"))):
        _text, status, warnings = await _extract_text_from_content(b"%PDF", "application/pdf", "a.pdf")
    assert status == "failed"
    assert warnings


def test_extraction_json_and_image(tmp_path):
    from app.rag.extraction import (
        extract_combined_kb_json,
        extract_text,
        extract_text_file,
        extract_tor_extract_json,
        flatten_decision_rules_json,
    )

    combined = tmp_path / "pack_combined.json"
    combined.write_text(
        json.dumps({"name": "ชุดกฎหมาย", "sections": [{"content": "วงเงินเฉพาะเจาะจง"}, "skip"]}),
        encoding="utf-8",
    )
    result = extract_combined_kb_json(str(combined))
    assert "วงเงิน" in result.text

    empty = tmp_path / "empty_combined.json"
    empty.write_text("{}", encoding="utf-8")
    assert extract_combined_kb_json(str(empty)).warnings

    rules_dir = tmp_path / "04-decision-rules"
    rules_dir.mkdir()
    rules = rules_dir / "rules.json"
    rules.write_text(
        json.dumps({"เงื่อนไขหลัก": {"result": "ใช้วิธีประกาศเชิญชวน", "code": "R1"}}),
        encoding="utf-8",
    )
    flat = flatten_decision_rules_json(str(rules))
    assert "ประกาศเชิญชวน" in flat.text

    extract = tmp_path / "doc_tor_extract.json"
    extract.write_text(
        json.dumps(
            {
                "source_file": "พ.ร.บ.pdf",
                "focus_areas": {"a": [{"content": "หลักเกณฑ์การจัดซื้อ"}, "x"]},
            }
        ),
        encoding="utf-8",
    )
    tor = extract_tor_extract_json(str(extract))
    assert "หลักเกณฑ์" in tor.text

    png = tmp_path / "scan.png"
    png.write_bytes(b"png")
    with patch("app.rag.extraction.ocr_page", return_value="จากรูป"):
        image = extract_text(str(png), "image/png")
    assert image.method == "ocr"
    with patch("app.rag.extraction.ocr_page", side_effect=FileNotFoundError):
        image = extract_text(str(png), "image/png")
    assert image.warnings
    with patch("app.rag.extraction.ocr_page", side_effect=RuntimeError("bad")):
        image = extract_text(str(png), "image/png")
    assert image.warnings

    txt = tmp_path / "note.txt"
    txt.write_text("สวัสดี", encoding="utf-8")
    assert "สวัสดี" in extract_text_file(str(txt)).text
    thai = tmp_path / "tis.txt"
    thai.write_bytes("สวัสดี".encode("cp874"))
    decoded = extract_text_file(str(thai))
    assert decoded.warnings

    with pytest.raises(ValueError, match="Unsupported"):
        extract_text(str(txt), "application/zip")
    with pytest.raises(FileNotFoundError):
        extract_text(str(tmp_path / "missing.pdf"), "application/pdf")

    routed = extract_text(str(combined), "application/json")
    assert routed.text


@pytest.mark.asyncio
async def test_custom_rag_client_builders_and_nested():
    from app.rag.custom_rag_client import (
        CustomRagClient,
        _chunk_from_item,
        _raw_chunk_list,
        build_custom_rag_client,
        resolve_custom_rag_url,
    )

    assert resolve_custom_rag_url("http://x", "http://abs/search") == "http://abs/search"
    assert resolve_custom_rag_url("http://x", "search") == "http://x/search"
    assert _raw_chunk_list({"data": [{"text": "ก"}]})
    assert _raw_chunk_list("no") == []
    assert _chunk_from_item({"text": ""}, 0) is None
    chunk = _chunk_from_item({"body": "ข้อความ", "score": "bad"}, 1)
    assert chunk is not None
    assert chunk.score == 0.0

    disabled = MagicMock(custom_rag_enabled=False, custom_rag_base_url="http://x")
    with patch("app.rag.custom_rag_client.get_settings", return_value=disabled):
        assert build_custom_rag_client() is None
    empty_url = MagicMock(custom_rag_enabled=True, custom_rag_base_url="  ")
    with patch("app.rag.custom_rag_client.get_settings", return_value=empty_url):
        assert build_custom_rag_client() is None
    enabled = MagicMock(
        custom_rag_enabled=True,
        custom_rag_base_url="http://rag.test",
        custom_rag_api_key="k",
        custom_rag_top_k=8,
        custom_rag_timeout_seconds=5.0,
        custom_rag_retrieve_path="",
    )
    with patch("app.rag.custom_rag_client.get_settings", return_value=enabled):
        client = build_custom_rag_client()
        assert isinstance(client, CustomRagClient)

    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"data": {"hits": [{"text": "จาก nested"}]}}
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    with patch("app.rag.custom_rag_client.httpx.AsyncClient", return_value=mock_client):
        got = await CustomRagClient(base_url="http://rag.test").retrieve("q")
    assert got[0].text == "จาก nested"


@pytest.mark.asyncio
async def test_agent_intake_process_and_store(tmp_path, monkeypatch):
    from app.config import Settings
    from app.services.agent_intake_service import (
        IntakeIngestionService,
        guess_mime,
        validate_file_count,
        BatchTooLargeError,
    )

    assert guess_mime("a.pdf", None) == "application/pdf"
    assert guess_mime("a.bin", "text/plain") == "text/plain"
    assert guess_mime("a.bin", "nope") is None
    with pytest.raises(BatchTooLargeError):
        validate_file_count(99)

    cache = MagicMock()
    cache.get_extraction = AsyncMock(return_value=None)
    cache.set_extraction = AsyncMock()
    service = IntakeIngestionService(cache=cache)

    class Upload:
        filename = "note.txt"
        content_type = "text/plain"

        async def read(self):
            return b"hello intake"

    with patch.object(service, "_extract_bytes", AsyncMock(return_value="hello intake")), patch.object(
        service, "_store_raw", AsyncMock()
    ):
        result = await service.process_batch(
            uuid.uuid4(), [Upload()], "ข้อความผู้ใช้", storage_backend="local"
        )
    assert result.total_chars > 0

    huge = SimpleNamespace(filename="big.pdf", content_type="application/pdf")

    async def huge_read():
        return b"x" * (50 * 1024 * 1024 + 1)

    huge.read = huge_read
    status = await service._process_one(uuid.uuid4(), huge, "local", None, None, None)
    assert status.error == "file_too_large"

    bad = SimpleNamespace(filename="x.bin", content_type="application/octet-stream")

    async def small():
        return b"x"

    bad.read = small
    status = await service._process_one(uuid.uuid4(), bad, "local", None, None, None)
    assert status.error == "unsupported_format"

    cached_upload = SimpleNamespace(filename="a.txt", content_type="text/plain")
    cached_upload.read = small
    cache.get_extraction = AsyncMock(return_value={"text": "cached"})
    status = await service._process_one(uuid.uuid4(), cached_upload, "local", None, None, None)
    assert status.text == "cached"

    cache.get_extraction = AsyncMock(return_value=None)
    with patch.object(service, "_extract_bytes", AsyncMock(side_effect=RuntimeError("ocr"))):
        status = await service._process_one(uuid.uuid4(), cached_upload, "local", None, None, None)
    assert status.error == "extraction_failed"

    settings = Settings(_env_file=None, agent_local_storage_dir=str(tmp_path), minio_bucket="b")
    monkeypatch.setattr("app.services.agent_intake_service.get_settings", lambda: settings)
    await service._store_raw(uuid.uuid4(), "a.txt", b"abc", "text/plain", "local", None)
    minio = MagicMock()
    minio.put_object.side_effect = RuntimeError("minio")
    await service._store_raw(uuid.uuid4(), "a.txt", b"abc", "text/plain", "minio", minio)
    minio.put_object.side_effect = None
    await service._store_raw(uuid.uuid4(), "a.txt", b"abc", "text/plain", "minio", minio)


@pytest.mark.asyncio
async def test_review_generate_suggestions_and_gap_generic():
    from app.api.v1.endpoints.review import (
        _finding_response,
        _findings_response,
        _generate_suggestions,
        persist_analysis_json,
    )
    from app.rule_engine.engine import Finding, Severity

    persist_analysis_json(SimpleNamespace(), {"ok": True})
    finding = Finding(Severity.WARNING, "R1", "s1", "ตรวจ", "แก้")
    wrapped = _finding_response(finding)
    assert wrapped.affected_section == "s1"
    assert _findings_response([finding])
    from app.services.gap_detector import GapDetector

    suggestion = SimpleNamespace(
        section_key="s1",
        category="clarity",
        current_text="เก่า",
        suggested_text="ใหม่",
        predicted_score_improvement=5,
    )
    review_result = SimpleNamespace(suggestions=[suggestion], overall_assessment="ดี")
    pending = SimpleNamespace()
    session = FakeSession(rows=[pending])
    with patch("app.providers.factory.ProviderFactory") as factory, patch(
        "app.orchestrator.agents.review_agent.ReviewAgent"
    ) as agent_cls:
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def admit_ok(*_a, **_k):
            yield "rid"

        factory.return_value.get_llm.return_value = MagicMock()
        agent_cls.return_value.review = AsyncMock(return_value=review_result)
        with patch("app.api.v1.endpoints.review.admit", admit_ok):
            count, assessment = await _generate_suggestions(
                uuid.uuid4(), {"s1": "ข้อความ"}, {"name": "ป"}, session
            )
    assert count == 1
    assert assessment == "ดี"

    detector = GapDetector(llm=None)
    gaps = detector.detect_gaps(empty_slot_map())
    assert gaps
    questions = detector.generic_questions(gaps)
    assert questions
    with patch("app.providers.factory.ProviderFactory", side_effect=RuntimeError("no")):
        got = await detector.generate_questions(gaps[:1], {"name": "ป"})
    assert got
    empty = await detector.generate_questions([], None)
    assert empty == []

    class _LLM:
        pass

    detector = GapDetector(llm=_LLM())
    with patch(
        "app.services.gap_detector.invoke_with_schema",
        AsyncMock(side_effect=RuntimeError("schema")),
    ):
        got = await detector.generate_questions(gaps[:1])
    assert got
    with patch(
        "app.services.gap_detector.invoke_with_schema",
        AsyncMock(return_value={"questions": ["ถามวงเงินเท่าใด"]}),
    ):
        got = await detector.generate_questions(gaps[:1])
    assert got[0].startswith("ถาม")
    with patch(
        "app.services.gap_detector.invoke_with_schema",
        AsyncMock(return_value={"questions": []}),
    ):
        got = await detector.generate_questions(gaps[:1])
    assert got


# ---------------------------------------------------------------------------
# Remaining high-miss helpers
# ---------------------------------------------------------------------------


def test_infra_setters_round_trip():
    from app import infra as runtime

    previous = (
        runtime.session_factory,
        runtime.mongo_client,
        runtime.neo4j_driver,
        runtime.redis_client,
        runtime.minio_client,
    )
    runtime.set_session_factory("sf")
    runtime.set_mongo_client("mongo")
    runtime.set_neo4j_driver("neo4j")
    runtime.set_redis_client("redis")
    runtime.set_minio_client("minio")
    assert runtime.session_factory == "sf"
    assert runtime.mongo_client == "mongo"
    assert runtime.neo4j_driver == "neo4j"
    assert runtime.redis_client == "redis"
    assert runtime.minio_client == "minio"
    runtime.set_session_factory(previous[0])
    runtime.set_mongo_client(previous[1])
    runtime.set_neo4j_driver(previous[2])
    runtime.set_redis_client(previous[3])
    runtime.set_minio_client(previous[4])


def test_slot_label_and_scope_sub():
    from app.domain.slots import is_scope_sub, slot_label

    assert slot_label("nope") == "nope"
    assert is_scope_sub("s4.1") is True
    assert is_scope_sub("s1") is False


def test_section_plain_text_empty_and_extra_keys():
    from app.domain.section_text import section_plain_text

    assert section_plain_text("  ") == ""
    assert section_plain_text(None) == ""
    raw = '{"history":"ระบบเดิม","extra":"เพิ่ม"}'
    text = section_plain_text(raw, "s1")
    assert "ระบบเดิม" in text
    unknown = section_plain_text('{"body":"เนื้อหา","note":"หมายเหตุ"}', "s99")
    assert "เนื้อหา" in unknown or "หมายเหตุ" in unknown


def test_persist_unknown_section_body_only():
    from app.domain.section_fields import persist_section_fields

    assert persist_section_fields("s99", '{"body": "เนื้อหาก้อน"}') == "เนื้อหาก้อน"
    assert persist_section_fields("s1", "  ") == ""


def test_file_magic_remaining_signatures():
    from app.domain.file_magic import detect_mime, require_kb_upload

    assert detect_mime(b"short") is None
    assert detect_mime(b"\xff\xd8\xffXXXXXXX") == "image/jpeg"
    assert detect_mime(b"GIF89aXXXXXX") == "image/gif"
    assert detect_mime(b"RIFF....WEBPXXXX") == "image/webp"
    assert detect_mime(b"PK\x03\x04" + b"word/" + b"x" * 20) == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert detect_mime(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1XXXX") == "application/msword"
    assert require_kb_upload(b"%PDF-1.4 rest", "application/pdf", "a.pdf") == "application/pdf"
    assert require_kb_upload("สวัสดี".encode("utf-8") + b" extra", "text/plain", "note.txt") == "text/plain"
    with pytest.raises(ValueError, match="ไม่รองรับ"):
        require_kb_upload(b"MZ\x90\x00not-text", "text/plain", "note.txt")


def test_assemble_skips_empty_content():
    from app.services.tor_assemble import assemble_review_document

    document, parents = assemble_review_document(
        [SimpleNamespace(section_key="s1", sub_key=None, content="   ")]
    )
    assert document == {}
    assert parents == {}


def test_custom_rag_url_and_non_dict_items():
    from app.rag.custom_rag_client import resolve_custom_rag_url

    assert resolve_custom_rag_url("http://x/v1/retrieve", "") == "http://x/v1/retrieve"
    assert resolve_custom_rag_url("http://x/api/search", "") == "http://x/api/search"


@pytest.mark.asyncio
async def test_custom_rag_retrieve_skips_non_dict_and_sends_bearer():
    from app.rag.custom_rag_client import CustomRagClient

    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"chunks": ["skip", {"text": "กฎหมาย", "title": "พ.ร.บ."}]}
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    with patch("app.rag.custom_rag_client.httpx.AsyncClient", return_value=mock_client):
        got = await CustomRagClient(base_url="http://rag.test", api_key="tok").retrieve("q")
    assert got[0].text == "กฎหมาย"
    assert got[0].source_document == "พ.ร.บ."
    headers = mock_client.post.await_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer tok"


@pytest.mark.asyncio
async def test_session_cache_read_delete_and_invalid_json():
    from app.services.session_cache import SessionCacheService

    redis = MagicMock()
    redis.get = AsyncMock(side_effect=RuntimeError("down"))
    redis.delete = AsyncMock(side_effect=RuntimeError("down"))
    cache = SessionCacheService(redis=redis)
    assert await cache.get_draft("p1", "s1") is None
    await cache.invalidate_project("p1")

    redis.get = AsyncMock(return_value="")
    redis.delete = AsyncMock()
    assert await cache.get_slot_map("p1") is None
    redis.get = AsyncMock(return_value="not-json")
    assert await cache.get_session_state("sid") == "not-json"
    redis.set = AsyncMock()
    await cache.set_draft("p1", "s1", "ร่าง")
    await cache.set_session_state("sid", {"phase": "idle"})
    await cache.set_kb_history("sid", [])
    await cache.invalidate_project("p1")
    redis.delete.assert_awaited()

    empty = SessionCacheService(redis=None)
    await empty.invalidate_project("p1")
    await empty.set_kb_history("sid", [])


@pytest.mark.asyncio
async def test_extract_graph_parse_failure_and_non_list():
    from app.rag.graph_extract import extract_graph_from_text

    llm = MagicMock()
    with patch(
        "app.rag.graph_extract.invoke_with_schema",
        AsyncMock(side_effect=ValueError("bad json")),
    ):
        nodes, rels = await extract_graph_from_text(llm, "กฎหมาย", document_name="ด.pdf")
    assert nodes == []
    assert rels == []

    with patch(
        "app.rag.graph_extract.invoke_with_schema",
        AsyncMock(return_value={"nodes": "nope", "rels": None}),
    ):
        nodes, rels = await extract_graph_from_text(llm, "กฎหมาย", document_name="ด.pdf")
    assert nodes == []
    assert rels == []


def test_parse_json_lenient_without_close_and_plain():
    from app.rag.graph_extract import parse_json_lenient

    assert parse_json_lenient('{"ok": true}')["ok"] is True
    payload = parse_json_lenient('```json\n{"ok": true}')
    assert payload["ok"] is True


@pytest.mark.asyncio
async def test_kb_chat_truncate_metadata_and_naive_time():
    from datetime import datetime

    from app.rag.retrieval import RetrievalResult, RetrievedChunk
    from app.services.kb_chat_service import KnowledgeChatService, bound_history

    items = [{"role": "assistant", "content": "a"}] + [
        {"role": "user" if index % 2 else "assistant", "content": str(index)}
        for index in range(50)
    ]
    trimmed = bound_history(items)
    assert trimmed[0]["role"] == "user"

    cache = MagicMock()
    cache.set_kb_history = AsyncMock()
    llm = MagicMock()
    llm.invoke = AsyncMock(return_value=MagicMock(content="คำตอบ"))
    service = KnowledgeChatService(cache=cache, llm=llm)
    chunk = RetrievedChunk(
        id="1",
        text="ก",
        score=0.8,
        source_document=None,
        metadata={"source_document": "จากเมตา"},
    )
    result = RetrievalResult(chunks=[chunk], query="q", top_k=1, actual_count=1)
    with patch(
        "app.services.kb_chat_service.hybrid_retrieve",
        AsyncMock(return_value=(result, [], False, False)),
    ):
        response = await service.answer(uuid.uuid4(), uuid.uuid4(), "x" * 1200)
    assert len(response.history[0]["content"]) <= 1000
    assert response.citations[0]["document"] == "จากเมตา"

    db = AsyncMock()
    missing = MagicMock()
    missing.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=missing)
    await service.answer(uuid.uuid4(), uuid.uuid4(), "ถาม", db=db)

    row = MagicMock()
    row.user_id = uuid.uuid4()
    row.last_active_at = datetime.now().replace(tzinfo=None)
    found = MagicMock()
    found.scalar_one_or_none.return_value = row
    db.execute = AsyncMock(return_value=found)
    assert await service.load_session(db, uuid.uuid4(), row.user_id) is row


@pytest.mark.asyncio
async def test_kb_chat_synthesize_via_factory():
    from app.rag.retrieval import RetrievalResult, RetrievedChunk
    from app.services.kb_chat_service import KnowledgeChatService

    cache = MagicMock()
    cache.set_kb_history = AsyncMock()
    service = KnowledgeChatService(cache=cache)
    llm = MagicMock()
    llm.invoke = AsyncMock(return_value=MagicMock(content=""))
    chunk = RetrievedChunk(id="1", text="ก", score=0.9)
    result = RetrievalResult(chunks=[chunk], query="q", top_k=1, actual_count=1)
    with patch(
        "app.services.kb_chat_service.hybrid_retrieve",
        AsyncMock(return_value=(result, [], False, False)),
    ), patch("app.services.kb_chat_service.ProviderFactory") as factory:
        factory.return_value.get_llm.return_value = llm
        response = await service.answer(uuid.uuid4(), uuid.uuid4(), "ถาม")
    assert response.answer == ""


@pytest.mark.asyncio
async def test_agent_workflow_persist_load_and_routes():
    from app.services import agent_workflow as wf

    session_id = uuid.uuid4()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    state = wf.default_state(session_id, project_id, user_id, {"name": "ป"})
    assert state["phase"] == "idle"
    merged = wf.merge_state(state, {"phase": "mapping"})
    assert merged["phase"] == "mapping"

    row = SimpleNamespace(
        id=session_id,
        project_id=project_id,
        user_id=user_id,
        phase="gap_filling",
        slot_map={"s1": {}},
        gap_iteration=2,
        graph_state="nope",
        messages=[{"role": "user"}],
        warnings=["w"],
    )
    loaded = wf.load_state(row)
    assert loaded["phase"] == "gap_filling"
    assert loaded["gap_iteration"] == 2

    session = FakeSession()
    with patch("app.services.agent_workflow.SessionCacheService") as cache_cls:
        cache_cls.return_value.set_session_state = AsyncMock()
        await wf.persist_state(session, row, merged)
    assert session.added

    with patch.object(wf, "ingest_node", AsyncMock(return_value={"phase": "error"})):
        stopped = await wf.run_start(state)
    assert stopped["phase"] == "error"

    with (
        patch.object(wf, "ingest_node", AsyncMock(return_value={"phase": "mapping"})),
        patch.object(wf, "map_sections_node", AsyncMock(return_value={"phase": "gap_filling"})),
        patch.object(wf, "detect_gaps_node", AsyncMock(return_value={"phase": "confirming"})),
    ):
        started = await wf.run_start(state)
    assert started["phase"] == "confirming"

    with (
        patch.object(wf, "fill_slot_node", AsyncMock(return_value={"phase": "gap_filling"})),
        patch.object(wf, "detect_gaps_node", AsyncMock(return_value={"phase": "confirming"})),
    ):
        answered = await wf.run_answer(state, "งบ 5 ล้าน")
    assert answered["phase"] == "confirming"

    with patch.object(wf, "detect_gaps_node", AsyncMock(return_value={"phase": "confirming"})):
        declined = await wf.run_confirm(state, False)
    assert declined["phase"] == "confirming"

    with (
        patch.object(wf, "draft_all_node", AsyncMock(return_value={"phase": "validating"})),
        patch.object(wf, "validate_draft_node", AsyncMock(return_value={"phase": "human_review"})),
    ):
        confirmed = await wf.run_confirm({**state, "phase": "confirming"}, True)
    assert confirmed["phase"] == "human_review"

    waiting = await wf.run_review(state, False, None, [])
    assert waiting["phase"] == "human_review"

    with (
        patch.object(wf, "draft_all_node", AsyncMock(return_value={"phase": "validating"})),
        patch.object(wf, "validate_draft_node", AsyncMock(return_value={"phase": "human_review"})),
    ):
        redrafted = await wf.run_review(state, False, "แก้ s1", ["s3"])
    assert redrafted["phase"] == "human_review"

    with patch.object(
        wf, "export_node", AsyncMock(return_value={"phase": "complete"})
    ):
        exported = await wf.run_review(
            {**state, "sections_acknowledged": []}, True, None, ["s3"]
        )
    assert exported["phase"] == "complete"


@pytest.mark.asyncio
async def test_rate_limit_ai_allows_and_rejects():
    from app.exceptions import RateLimitError
    from app.rate_limiter import rate_limit_ai

    request = MagicMock()
    request.app.state.redis = None
    await rate_limit_ai(request)

    redis = AsyncMock()
    redis.incr.return_value = 31
    redis.ttl.return_value = 12
    request.app.state.redis = redis
    request.headers = {}
    request.client.host = "10.0.0.1"
    with patch("app.rate_limiter.get_settings") as settings:
        settings.return_value = MagicMock(rate_limit_ai_per_minute=30)
        with pytest.raises(RateLimitError):
            await rate_limit_ai(request)


@pytest.mark.asyncio
async def test_gemini_embedding_timeout_and_http_error():
    import httpx

    from app.providers.embedding.gemini_provider import GeminiEmbeddingProvider

    provider = GeminiEmbeddingProvider(api_key="fake", dimensions=4)
    timeout_client = AsyncMock()
    timeout_client.post = AsyncMock(side_effect=httpx.TimeoutException("slow"))
    timeout_client.__aenter__ = AsyncMock(return_value=timeout_client)
    timeout_client.__aexit__ = AsyncMock(return_value=None)
    with patch(
        "app.providers.embedding.gemini_provider.httpx.AsyncClient",
        return_value=timeout_client,
    ):
        with pytest.raises(TimeoutError, match="timed out"):
            await provider.embed_query("วงเงิน")

    err_client = AsyncMock()
    err_client.post = AsyncMock(side_effect=httpx.HTTPError("down"))
    err_client.__aenter__ = AsyncMock(return_value=err_client)
    err_client.__aexit__ = AsyncMock(return_value=None)
    with patch(
        "app.providers.embedding.gemini_provider.httpx.AsyncClient",
        return_value=err_client,
    ):
        with pytest.raises(ConnectionError, match="unreachable"):
            await provider.embed_documents(["ก"])


@pytest.mark.asyncio
async def test_ingestion_status_update_missing_and_rollback():
    from app.rag.ingestion import _update_document_status

    session = MagicMock()
    session.get = AsyncMock(return_value=None)
    session.commit = AsyncMock()
    await _update_document_status(session, str(uuid.uuid4()), "completed", chunk_count=1)
    session.commit.assert_not_awaited()

    session.get = AsyncMock(side_effect=RuntimeError("db"))
    session.rollback = AsyncMock(side_effect=RuntimeError("rollback"))
    await _update_document_status(session, str(uuid.uuid4()), "failed", error_message="x")


@pytest.mark.asyncio
async def test_draft_chat_existing_text_and_upsert():
    from app.api.v1.endpoints import draft_chat as dc

    pid = uuid.uuid4()
    session = FakeSession(value=None)

    def factory():
        return session

    with (
        patch.object(dc, "_load_s4_rows", AsyncMock(return_value=[])),
        patch.object(dc, "_s4_ai_map", return_value={"s4.1": "ขอบเขต"}),
        patch.object(dc, "_s4_complete", return_value=True),
        patch.object(dc, "build_merged_scope", return_value="รวม s4"),
    ):
        assert await dc._existing_section_text(factory, pid, "s4") == "รวม s4"

    with (
        patch.object(dc, "_load_s4_rows", AsyncMock(return_value=[])),
        patch.object(dc, "_s4_ai_map", return_value={}),
        patch.object(dc, "_s4_complete", return_value=False),
    ):
        assert await dc._existing_section_text(factory, pid, "s4") is None

    session.value = SimpleNamespace(ai_draft="  ", content="")
    assert await dc._existing_section_text(factory, pid, "s1") is None
    session.value = SimpleNamespace(ai_draft="ร่าง", content="เนื้อหา")
    assert await dc._existing_section_text(factory, pid, "s1") == "เนื้อหา"

    session.value = None
    await dc._upsert_sub(session, pid, "s4.1", "ขอบเขต")
    assert session.added
    existing = SimpleNamespace(content="", ai_draft="")
    session.value = existing
    await dc._upsert_sub(session, pid, "s4.1", "ใหม่")
    assert existing.content == "ใหม่"

    session.rows = [SimpleNamespace(sub_key="s4.1", content="ขอบเขต")]
    assert await dc._load_s4_subs(session, pid) == {"s4.1": "ขอบเขต"}
    session.value = SimpleNamespace(ai_draft="ร่าง", content="เนื้อหา")
    assert await dc._load_section_draft(factory, pid, "s1") == "เนื้อหา"
    with patch.object(dc, "build_merged_scope", return_value="รวม"):
        assert await dc._load_section_draft(factory, pid, "s4") == "รวม"


@pytest.mark.asyncio
async def test_draft_chat_service_rag_failure_and_only_missing():
    from app.domain.tor_sections import SCOPE_SUBSECTIONS
    from app.services.draft_chat_service import (
        collect_scope_subsection_drafts,
        draft_single_section,
    )

    with patch(
        "app.services.draft_chat_service.hybrid_retrieve",
        AsyncMock(side_effect=RuntimeError("rag")),
    ), patch(
        "app.services.draft_chat_service._stream_llm_prompt",
        return_value=_sse_aiter("token"),
    ):
        tokens = [item async for item in draft_single_section("s1", {})]
    assert tokens == ["token"]

    existing = {key: "มีแล้ว" for key in SCOPE_SUBSECTIONS}
    out = await collect_scope_subsection_drafts({}, only_missing=True, existing=existing)
    assert out == existing


@pytest.mark.asyncio
async def test_run_sequential_draft_retries_and_marks_failed():
    from app.api.v1.endpoints import draft_chat as dc

    pid = uuid.uuid4()
    session = FakeSession()

    def factory():
        return session

    job = dc._SeqDraft(factory, pid, {}, uuid.uuid4(), "r", None)
    with (
        patch.object(dc, "set_job", AsyncMock()),
        patch.object(dc, "bump_progress", AsyncMock()),
        patch.object(dc, "mark_status", AsyncMock()) as mark,
        patch.object(dc, "_try_draft_one_section", AsyncMock(return_value=False)),
        patch("app.api.v1.endpoints.draft_chat.TOR_SECTION_ORDER", ["s1"]),
    ):
        count = await dc._run_sequential_draft(job, remaining_passes=1)
    assert count == 0
    assert mark.await_count >= 1

    with (
        patch.object(dc, "set_job", AsyncMock()),
        patch.object(dc, "mark_status", AsyncMock()),
        patch.object(dc, "_try_draft_one_section", AsyncMock(side_effect=RuntimeError("boom"))),
        patch("app.api.v1.endpoints.draft_chat.TOR_SECTION_ORDER", ["s1"]),
    ):
        with pytest.raises(RuntimeError, match="boom"):
            await dc._run_sequential_draft(job, remaining_passes=0)
