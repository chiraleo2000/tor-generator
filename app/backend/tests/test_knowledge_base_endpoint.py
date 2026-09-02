"""Unit tests for knowledge base management endpoints.

Tests cover:
- GET /api/v1/knowledge-base (list documents)
- POST /api/v1/knowledge-base/upload (upload and trigger ingestion)
- DELETE /api/v1/knowledge-base/{id} (remove document and chunks)
- POST /api/v1/knowledge-base/batch-ingest (full re-ingestion)
- GET /api/v1/knowledge-base/{id}/status (processing status)

Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5
"""

import io
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.deps import get_current_user, get_db, get_minio
from app.main import app
from app.models.knowledge_base_document import KnowledgeBaseDocument
from app.models.user import User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")
DOC_ID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _make_user(user_id=USER_ID, role="admin"):
    """Create a mock User object."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.role = role
    user.email = "admin@example.go.th"
    user.name = "Admin User"
    return user


def _make_kb_document(
    doc_id=DOC_ID,
    name="พ.ร.บ. การจัดซื้อจัดจ้าง 2560",
    category="law",
    file_type="pdf",
    processing_status="completed",
    chunk_count=42,
    error_message=None,
    owner_id=None,
    scope="baseline",
    corpus_group="mandatory_raw",
):
    """Create a mock KnowledgeBaseDocument object."""
    doc = MagicMock(spec=KnowledgeBaseDocument)
    doc.id = doc_id
    doc.name = name
    doc.category = category
    doc.file_type = file_type
    doc.storage_path = f"knowledge-base/{doc_id}/document.{file_type}"
    doc.processing_status = processing_status
    doc.chunk_count = chunk_count
    doc.error_message = error_message
    doc.uploaded_at = datetime(2024, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
    doc.processed_at = datetime(2024, 8, 15, 10, 5, 0, tzinfo=timezone.utc)
    doc.owner_id = owner_id
    doc.scope = scope
    doc.corpus_group = corpus_group
    doc.mongo_gridfs_id = None
    return doc


@pytest.fixture(autouse=True)
def setup_app_state():
    """Setup app state and override dependencies for tests."""
    app.state.db_session_factory = None
    app.state.db_engine = None
    app.state.redis = None
    app.state.minio = MagicMock()

    async def mock_get_db():
        yield AsyncMock()

    def mock_get_minio():
        return MagicMock()

    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_minio] = mock_get_minio
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_admin_user():
    """Override get_current_user to return an admin user."""
    user = _make_user(role="admin")

    async def override():
        return user

    app.dependency_overrides[get_current_user] = override
    return user


@pytest.fixture
def mock_officer_user():
    """Override get_current_user to return an officer user."""
    user = _make_user(role="officer")

    async def override():
        return user

    app.dependency_overrides[get_current_user] = override
    return user


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# GET /knowledge-base — List documents
# ---------------------------------------------------------------------------


class TestListKnowledgeBase:
    """Tests for GET /api/v1/knowledge-base."""

    def test_admin_lists_documents(self, client, mock_admin_user):
        """Admin can list all KB documents with status and chunk count."""
        documents = [
            _make_kb_document(),
            _make_kb_document(
                doc_id=uuid.uuid4(),
                name="กฎกระทรวง",
                category="regulation",
                processing_status="pending",
                chunk_count=0,
            ),
        ]

        mock_db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = documents
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/knowledge-base")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["total"] == 2
        assert len(data["data"]["items"]) == 2
        # Verify fields present
        item = data["data"]["items"][0]
        assert "name" in item
        assert "category" in item
        assert "processing_status" in item
        assert "chunk_count" in item

        slashed = client.get("/api/v1/knowledge-base/")
        assert slashed.status_code == 200
        assert slashed.json()["data"]["total"] == 2

    def test_empty_knowledge_base(self, client, mock_admin_user):
        """Returns empty list when no documents exist."""
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/knowledge-base")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["total"] == 0
        assert data["data"]["items"] == []

    def test_officer_can_list_documents(self, client, mock_officer_user):
        """Officers can browse the knowledge base inventory."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.get("/api/v1/knowledge-base")
        assert response.status_code == 200

    def test_officer_can_get_catalog(self, client, mock_officer_user):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        catalog = client.get("/api/v1/knowledge-base/catalog")
        assert catalog.status_code == 200
        body = catalog.json()["data"]
        assert "raw" in body
        assert "chunked" in body
        assert "groups" in body
        assert "userFiles" in body
        assert client.get("/api/v1/knowledge-base/raw").status_code == 200
        assert client.get("/api/v1/knowledge-base/chunked").status_code == 200

    def test_unauthenticated_returns_401(self, client):
        """Unauthenticated request returns 401."""
        response = client.get("/api/v1/knowledge-base")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /knowledge-base/upload — Upload document
# ---------------------------------------------------------------------------


class TestUploadDocument:
    """Tests for POST /api/v1/knowledge-base/upload."""

    def test_admin_uploads_pdf_success(self, client, mock_admin_user):
        """Admin successfully uploads a PDF document."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock(
            side_effect=lambda doc: _apply_doc_defaults(doc)
        )

        async def override_db():
            yield mock_db

        mock_minio = MagicMock()
        mock_minio.put_object = MagicMock()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_minio] = lambda: mock_minio

        file_content = b"%PDF-1.4 fake pdf content for testing"
        response = client.post(
            "/api/v1/knowledge-base/upload",
            files={"file": ("test_law.pdf", io.BytesIO(file_content), "application/pdf")},
            data={"category": "law", "name": "พ.ร.บ. จัดซื้อจัดจ้าง 2560"},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["processing_status"] == "pending"
        assert data["data"]["category"] == "law"
        assert data["data"]["file_type"] == "pdf"

    def test_admin_uploads_docx_success(self, client, mock_admin_user):
        """Admin successfully uploads a DOCX document."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock(
            side_effect=lambda doc: _apply_doc_defaults(doc)
        )

        async def override_db():
            yield mock_db

        mock_minio = MagicMock()
        mock_minio.put_object = MagicMock()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_minio] = lambda: mock_minio

        file_content = b"PK\x03\x04word/document.xml fake docx content"
        response = client.post(
            "/api/v1/knowledge-base/upload",
            files={
                "file": (
                    "guideline.docx",
                    io.BytesIO(file_content),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            data={"category": "guideline"},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["file_type"] == "docx"
        assert data["data"]["category"] == "guideline"

    def test_admin_uploads_txt_success(self, client, mock_admin_user):
        """Admin successfully uploads a TXT document."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock(
            side_effect=lambda doc: _apply_doc_defaults(doc)
        )

        async def override_db():
            yield mock_db

        mock_minio = MagicMock()
        mock_minio.put_object = MagicMock()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_minio] = lambda: mock_minio

        file_content = "เนื้อหาตัวอย่าง TOR".encode("utf-8")
        response = client.post(
            "/api/v1/knowledge-base/upload",
            files={"file": ("example.txt", io.BytesIO(file_content), "text/plain")},
            data={"category": "example_tor", "name": "ตัวอย่าง TOR ระบบ IT"},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["file_type"] == "txt"
        assert data["data"]["name"] == "ตัวอย่าง TOR ระบบ IT"

    def test_upload_unsupported_file_type_returns_400(self, client, mock_admin_user):
        """Uploading an unsupported file type returns 400."""
        file_content = b"fake image content"
        response = client.post(
            "/api/v1/knowledge-base/upload",
            files={"file": ("image.png", io.BytesIO(file_content), "image/png")},
            data={"category": "manual"},
        )
        assert response.status_code == 400

    def test_upload_oversized_file_returns_400(self, client, mock_admin_user):
        huge = b"%PDF-1.4 " + b"x" * (20 * 1024 * 1024 + 10)
        response = client.post(
            "/api/v1/knowledge-base/upload",
            files={"file": ("big.pdf", io.BytesIO(huge), "application/pdf")},
            data={"category": "manual"},
        )
        assert response.status_code == 400

        """Uploading with an invalid category returns 422."""
        file_content = b"%PDF-1.4 fake pdf"
        response = client.post(
            "/api/v1/knowledge-base/upload",
            files={"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")},
            data={"category": "invalid_category"},
        )
        assert response.status_code == 422

    def test_upload_uses_filename_when_name_not_provided(self, client, mock_admin_user):
        """When name is not provided, uses the filename."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock(
            side_effect=lambda doc: _apply_doc_defaults(doc)
        )

        async def override_db():
            yield mock_db

        mock_minio = MagicMock()
        mock_minio.put_object = MagicMock()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_minio] = lambda: mock_minio

        file_content = b"%PDF-1.4 content"
        response = client.post(
            "/api/v1/knowledge-base/upload",
            files={"file": ("my_document.pdf", io.BytesIO(file_content), "application/pdf")},
            data={"category": "regulation"},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["data"]["name"] == "my_document.pdf"

    def test_officer_cannot_upload(self, client, mock_officer_user):
        """Officers cannot upload KB documents."""
        file_content = b"%PDF-1.4 fake pdf"
        response = client.post(
            "/api/v1/knowledge-base/upload",
            files={"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")},
            data={"category": "law"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /knowledge-base/{id} — Remove document
# ---------------------------------------------------------------------------


class TestDeleteDocument:
    """Tests for DELETE /api/v1/knowledge-base/{id}."""

    def test_admin_deletes_document_success(self, client, mock_admin_user):
        """Admin successfully deletes a document and its chunks."""
        document = _make_kb_document()

        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = document
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.delete = AsyncMock()

        async def override_db():
            yield mock_db

        mock_minio = MagicMock()
        mock_minio.remove_object = MagicMock()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_minio] = lambda: mock_minio

        response = client.delete(f"/api/v1/knowledge-base/{DOC_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["id"] == str(DOC_ID)

    def test_delete_document_not_found(self, client, mock_admin_user):
        """Returns 404 when document doesn't exist."""
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.delete(f"/api/v1/knowledge-base/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_delete_continues_if_minio_fails(self, client, mock_admin_user):
        """Document is deleted even if MinIO file removal fails."""
        document = _make_kb_document()

        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = document
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.delete = AsyncMock()

        async def override_db():
            yield mock_db

        mock_minio = MagicMock()
        mock_minio.remove_object = MagicMock(side_effect=Exception("MinIO unreachable"))

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_minio] = lambda: mock_minio

        response = client.delete(f"/api/v1/knowledge-base/{DOC_ID}")
        # Should still succeed — MinIO failure is non-blocking
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    def test_officer_cannot_delete_document(self, client, mock_officer_user):
        """Officers cannot delete KB documents."""
        response = client.delete(f"/api/v1/knowledge-base/{DOC_ID}")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# POST /knowledge-base/batch-ingest — Batch re-ingestion
# ---------------------------------------------------------------------------


class TestBatchIngest:
    """Tests for POST /api/v1/knowledge-base/batch-ingest."""

    def test_admin_triggers_batch_ingest(self, client, mock_admin_user):
        """Admin successfully triggers batch re-ingestion."""
        documents = [
            _make_kb_document(),
            _make_kb_document(doc_id=uuid.uuid4(), name="กฎกระทรวง"),
        ]

        mock_db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = documents
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.post("/api/v1/knowledge-base/batch-ingest")
        assert response.status_code == 202
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["total_documents"] == 2

    def test_batch_ingest_empty_kb_returns_400(self, client, mock_admin_user):
        """Returns 400 when knowledge base is empty."""
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.post("/api/v1/knowledge-base/batch-ingest")
        assert response.status_code == 400

    def test_officer_cannot_batch_ingest(self, client, mock_officer_user):
        """Officers cannot trigger batch ingestion."""
        response = client.post("/api/v1/knowledge-base/batch-ingest")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /knowledge-base/{id}/status — Processing status
# ---------------------------------------------------------------------------


class TestDocumentStatus:
    """Tests for GET /api/v1/knowledge-base/{id}/status."""

    def test_get_completed_document_status(self, client, mock_admin_user):
        """Get status of a completed document."""
        document = _make_kb_document(processing_status="completed", chunk_count=42)

        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = document
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/knowledge-base/{DOC_ID}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["processing_status"] == "completed"
        assert data["data"]["chunk_count"] == 42

    def test_get_failed_document_status(self, client, mock_admin_user):
        """Get status of a failed document shows error message."""
        document = _make_kb_document(
            processing_status="failed",
            chunk_count=0,
            error_message="Text extraction failed: unsupported format",
        )

        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = document
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/knowledge-base/{DOC_ID}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["processing_status"] == "failed"
        assert data["data"]["error_message"] is not None

    def test_get_pending_document_status(self, client, mock_admin_user):
        """Get status of a pending document."""
        document = _make_kb_document(processing_status="pending", chunk_count=0)
        document.processed_at = None

        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = document
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/knowledge-base/{DOC_ID}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["processing_status"] == "pending"

    def test_document_not_found_returns_404(self, client, mock_admin_user):
        """Returns 404 when document doesn't exist."""
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/knowledge-base/{uuid.uuid4()}/status")
        assert response.status_code == 404

    def test_officer_cannot_get_status(self, client, mock_officer_user):
        """Officers cannot access document status."""
        response = client.get(f"/api/v1/knowledge-base/{DOC_ID}/status")
        assert response.status_code == 403


class TestCatalogGroupingAndAcl:
    def test_catalog_splits_mandatory_and_owner_files(self, client, mock_officer_user):
        other_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
        documents = [
            _make_kb_document(
                name="คู่มือแนวปฏิบัติ_การจัดซื้อจัดจ้างภาครัฐ.pdf",
                category="manual",
                corpus_group="mandatory_handbook",
            ),
            _make_kb_document(
                doc_id=uuid.uuid4(),
                name="พรบ.pdf",
                category="law",
                corpus_group="mandatory_raw",
            ),
            _make_kb_document(
                doc_id=uuid.uuid4(),
                name="ของฉัน.pdf",
                category="example_tor",
                owner_id=USER_ID,
                scope="user",
                corpus_group="user",
            ),
            _make_kb_document(
                doc_id=uuid.uuid4(),
                name="ของคนอื่น.pdf",
                category="example_tor",
                owner_id=other_id,
                scope="user",
                corpus_group="user",
            ),
        ]
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = documents
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.get("/api/v1/knowledge-base/catalog")
        assert response.status_code == 200
        body = response.json()["data"]
        assert "groups" in body
        labels = {row["key"]: row["label"] for row in body["groups"]}
        assert "mandatory_handbook" in labels
        assert "mandatory_raw" in labels
        user_names = {item["name"] for item in body["userFiles"]}
        assert "ของฉัน.pdf" in user_names
        assert "ของคนอื่น.pdf" not in user_names
        user_group = next(row for row in body["groups"] if row["key"] == "user")
        assert user_group["mandatory"] is False
        group_names = {item["name"] for item in user_group["items"]}
        assert "ของคนอื่น.pdf" not in group_names
        raw_example = {item["name"] for item in body["raw"].get("example_tor", [])}
        assert "ของฉัน.pdf" in raw_example
        assert "ของคนอื่น.pdf" not in raw_example
        assert body["totals"]["files"] == 3

    def test_catalog_user_files_match_chat_attachment_owner(self):
        from app.api.v1.endpoints.knowledge_base import _catalog_payload

        attached = _make_kb_document(
            name="reg.pdf",
            category="other",
            owner_id=USER_ID,
            scope="user",
            corpus_group="user",
        )
        other = _make_kb_document(
            doc_id=uuid.uuid4(),
            name="secret.pdf",
            category="other",
            owner_id=uuid.UUID("99999999-9999-9999-9999-999999999999"),
            scope="user",
            corpus_group="user",
        )
        payload = _catalog_payload([attached, other], viewer_id=USER_ID)
        names = {item["name"] for item in payload["userFiles"]}
        assert names == {"reg.pdf"}
        mine = payload["userFiles"][0]
        assert mine["category"] == "other"
        assert mine["processing_status"] == "completed"
        assert "secret.pdf" not in {item["name"] for item in payload["raw"].get("other", [])}


class TestMineUploads:
    def test_officer_can_upload_private_file(self, client, mock_officer_user):
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock(side_effect=_apply_doc_defaults)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        with patch(
            "app.api.v1.endpoints.knowledge_base._run_pageindex_ingestion",
            new_callable=AsyncMock,
        ) as ingest:
            response = client.post(
                "/api/v1/knowledge-base/mine",
                files={"file": ("mine.pdf", io.BytesIO(b"%PDF-1.4 private"), "application/pdf")},
                data={"category": "guideline", "name": "เงื่อนไขโครงการ.pdf"},
            )
        assert response.status_code == 202
        assert ingest.await_count == 1
        kwargs = ingest.await_args.kwargs
        assert kwargs["scope"] == "user"
        assert kwargs["owner_id"] == str(USER_ID)
        saved = mock_db.add.call_args.args[0]
        assert saved.corpus_group == "user"
        assert saved.processing_status == "pending"
        assert response.json()["data"]["name"] == "เงื่อนไขโครงการ.pdf"

    def test_officer_upload_other_category_returns_202(self, client, mock_officer_user):
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock(side_effect=_apply_doc_defaults)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        with patch(
            "app.api.v1.endpoints.knowledge_base._run_pageindex_ingestion",
            new_callable=AsyncMock,
        ) as ingest:
            response = client.post(
                "/api/v1/knowledge-base/mine",
                files={"file": ("notes.pdf", io.BytesIO(b"%PDF-1.4 other"), "application/pdf")},
                data={"category": "other", "name": "บันทึกภายใน.pdf"},
            )
        assert response.status_code == 202
        assert ingest.await_args.kwargs["category"] == "other"
        assert mock_db.add.call_args.args[0].category == "other"
        assert response.json()["data"]["category"] == "other"

    def test_officer_deletes_own_file(self, client, mock_officer_user):
        document = _make_kb_document(
            owner_id=USER_ID, scope="user", corpus_group="user"
        )
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = document
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.delete = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.delete(f"/api/v1/knowledge-base/mine/{DOC_ID}")
        assert response.status_code == 200
        assert response.json()["data"]["id"] == str(DOC_ID)

    def test_officer_cannot_delete_someone_elses_file(self, client, mock_officer_user):
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.delete(f"/api/v1/knowledge-base/mine/{DOC_ID}")
        assert response.status_code == 404


    def test_officer_downloads_own_file(self, client, mock_officer_user):
        document = _make_kb_document(
            owner_id=USER_ID, scope="user", corpus_group="user"
        )
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = document
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        with patch(
            "app.api.v1.endpoints.knowledge_base._kb_original_bytes",
            return_value=b"%PDF-1.4 mine",
        ):
            response = client.get(f"/api/v1/knowledge-base/mine/{DOC_ID}/file")
        assert response.status_code == 200
        assert response.content == b"%PDF-1.4 mine"


    def test_officer_cannot_download_someone_elses_file(self, client, mock_officer_user):
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.get(f"/api/v1/knowledge-base/mine/{DOC_ID}/file")
        assert response.status_code == 404


    def test_admin_downloads_central_file(self, client, mock_admin_user):
        document = _make_kb_document()
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = document
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        with patch(
            "app.api.v1.endpoints.knowledge_base._kb_original_bytes",
            return_value=b"%PDF-1.4 central",
        ):
            response = client.get(f"/api/v1/knowledge-base/{DOC_ID}/file")
        assert response.status_code == 200
        assert response.content == b"%PDF-1.4 central"


    def test_officer_cannot_download_central_file_via_admin_path(
        self, client, mock_officer_user
    ):
        response = client.get(f"/api/v1/knowledge-base/{DOC_ID}/file")
        assert response.status_code == 403


def test_admin_download_missing_document(client, mock_admin_user):
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    response = client.get(f"/api/v1/knowledge-base/{DOC_ID}/file")
    assert response.status_code == 404


def test_kb_original_bytes_from_disk(tmp_path):
    from app.api.v1.endpoints.knowledge_base import (
        _file_download_response,
        _kb_original_bytes,
    )
    from app.exceptions import NotFoundError

    path = tmp_path / "doc.txt"
    path.write_bytes(b"hello-tor")
    doc = MagicMock()
    doc.mongo_gridfs_id = None
    doc.storage_path = str(path)
    doc.name = "doc.txt"
    doc.file_type = "txt"
    with patch(
        "app.api.v1.endpoints.knowledge_base.store_from_client",
        return_value=None,
    ):
        assert _kb_original_bytes(doc) == b"hello-tor"
        response = _file_download_response(doc)
        assert response.media_type == "text/plain"
        missing = MagicMock()
        missing.mongo_gridfs_id = None
        missing.storage_path = str(tmp_path / "missing.txt")
        missing.name = "missing.txt"
        try:
            _kb_original_bytes(missing)
            raise AssertionError("expected NotFoundError")
        except NotFoundError:
            pass


@pytest.mark.asyncio
async def test_purge_aux_stores_swallows_backend_errors():
    from app.api.v1.endpoints.knowledge_base import _purge_aux_stores

    doc = MagicMock()
    doc.id = uuid.uuid4()
    doc.mongo_gridfs_id = "grid-1"
    store = MagicMock()
    store.delete_file.side_effect = RuntimeError("grid miss")
    graph = MagicMock()
    graph.delete_document = AsyncMock(side_effect=RuntimeError("neo miss"))
    with (
        patch("app.api.v1.endpoints.knowledge_base.store_from_client", return_value=store),
        patch("app.api.v1.endpoints.knowledge_base.runtime") as runtime,
        patch("app.api.v1.endpoints.knowledge_base.GraphRAGStore", return_value=graph),
    ):
        runtime.mongo_client = object()
        runtime.neo4j_driver = object()
        await _purge_aux_stores(doc)
    store.delete_file.assert_called_once()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _apply_doc_defaults(doc):
    """Apply defaults to a KnowledgeBaseDocument after flush/refresh."""
    if not hasattr(doc, "id") or doc.id is None:
        doc.id = uuid.uuid4()
    if not hasattr(doc, "uploaded_at") or doc.uploaded_at is None:
        doc.uploaded_at = datetime.now(timezone.utc)
    if not hasattr(doc, "processed_at"):
        doc.processed_at = None
