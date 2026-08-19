"""Knowledge Base management API endpoints.

GET /knowledge-base — List documents with status and chunk count
POST /knowledge-base/upload — Upload document and trigger async ingestion
DELETE /knowledge-base/{id} — Remove document and its chunks
POST /knowledge-base/batch-ingest — Full KB re-ingestion
GET /knowledge-base/{id}/status — Processing status for a single document

All authenticated users can list shared documents plus their own uploads.
Admin upload/delete/batch-ingest remain global. Officers use POST /mine
and DELETE /mine/{id} for private files (chunked and embedded, owner-only).

Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import infra as runtime
from app.api.constants import MIME_DOCX, MIME_PDF, MIME_TXT
from app.deps import get_current_user, get_db, get_minio
from app.domain.corpus import (
    GROUP_LABELS,
    GROUP_MANDATORY_HANDBOOK,
    GROUP_MANDATORY_RAW,
    GROUP_ORDER,
    GROUP_USER,
    group_for_filename,
)
from app.domain.file_magic import require_kb_upload
from app.exceptions import NotFoundError, ValidationError
from app.io_temp import unlink_path, write_temp_bytes
from app.models.kb_chunk import KBChunk
from app.models.knowledge_base_document import KnowledgeBaseDocument
from app.models.user import User
from app.rag.document_pipeline import ingest_file_bytes
from app.rag.graph_store import GraphRAGStore
from app.rbac import Role, require_role
from app.schemas.knowledge_base import (
    KBBatchIngestResponse,
    KBCategory,
    KBDeleteResponse,
    KBDocumentListResponse,
    KBDocumentResponse,
    KBDocumentStatusResponse,
    KBUploadResponse,
)
from app.schemas.responses import MetaInfo, SuccessResponse
from app.storage.mongo_store import store_from_client

logger = logging.getLogger("tor_app.knowledge_base")

router = APIRouter()

# Allowed MIME types and their corresponding file_type values
ALLOWED_MIME_TYPES = {
    MIME_PDF: "pdf",
    MIME_DOCX: "docx",
    MIME_TXT: "txt",
}

# Maximum file size: 20MB
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024


def _validate_kb_bytes(file_content: bytes, claimed_mime: str, filename: str) -> str:
    if len(file_content) > MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            message=f"ไฟล์มีขนาดใหญ่เกินไป (สูงสุด {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB)",
            field="file",
        )
    try:
        content_type = require_kb_upload(file_content, claimed_mime, filename)
    except ValueError as exc:
        raise ValidationError(message=str(exc), field="file") from exc
    if content_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            message="ไฟล์ประเภทนี้ไม่รองรับ กรุณาอัปโหลดไฟล์ PDF, DOCX, หรือ TXT",
            field="file",
        )
    return content_type


async def _purge_aux_stores(document: KnowledgeBaseDocument) -> None:
    store = store_from_client(runtime.mongo_client)
    if store is not None:
        try:
            store.delete_file(document.mongo_gridfs_id)
        except Exception:
            logger.warning("Mongo delete missed for document %s", document.id)
    if runtime.neo4j_driver is not None:
        try:
            await GraphRAGStore(runtime.neo4j_driver).delete_document(str(document.id))
        except Exception:
            logger.warning("Neo4j delete missed for document %s", document.id)


def _build_success_response(
    request: Request, data: object, status_code: int = 200
) -> JSONResponse:
    """Build a standard success envelope response."""
    request_id = getattr(request.state, "request_id", "unknown")
    response = SuccessResponse(
        ok=True,
        data=data,
        meta=MetaInfo(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(mode="json"),
    )


# ---------------------------------------------------------------------------
# GET /knowledge-base — List KB documents
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="List knowledge base documents",
    description="List all knowledge base documents with status, chunk count, and metadata.",
)
@router.get("/")
async def list_knowledge_base_documents(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """List all KB documents ordered by uploaded_at descending.

    Returns: document name, category, file_type, processing status, chunk count.
    Req 11.3: Display current KB inventory.
    """
    documents = await _load_kb_docs(db, current_user)

    items = [KBDocumentResponse.model_validate(doc) for doc in documents]

    response_data = KBDocumentListResponse(
        items=items,
        total=len(items),
    ).model_dump(mode="json")

    return _build_success_response(request, response_data)


def _doc_group(doc: KnowledgeBaseDocument) -> str:
    group = getattr(doc, "corpus_group", None)
    if group:
        return group
    if getattr(doc, "owner_id", None) is not None:
        return GROUP_USER
    return group_for_filename(getattr(doc, "name", "") or "")


def _catalog_item(doc: KnowledgeBaseDocument) -> dict:
    group = _doc_group(doc)
    owner = getattr(doc, "owner_id", None)
    return {
        "id": str(doc.id),
        "name": doc.name,
        "file_type": doc.file_type,
        "category": doc.category,
        "chunk_count": doc.chunk_count or 0,
        "processing_status": doc.processing_status,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else "",
        "corpus_group": group,
        "owner_id": str(owner) if owner else None,
        "mandatory": group in {GROUP_MANDATORY_HANDBOOK, GROUP_MANDATORY_RAW},
    }


def _catalog_payload(documents: list, viewer_id: uuid.UUID | None = None) -> dict:
    grouped: dict[str, list[dict]] = {}
    chunked: dict[str, dict] = {}
    by_group: dict[str, list[dict]] = {}
    for doc in documents:
        item = _catalog_item(doc)
        grouped.setdefault(doc.category, []).append(item)
        bucket = chunked.setdefault(
            doc.category,
            {"key": doc.category, "name": doc.category, "files": 0, "chunks": 0},
        )
        bucket["files"] += 1
        bucket["chunks"] += doc.chunk_count or 0
        if item["corpus_group"] == GROUP_USER:
            if viewer_id is None or doc.owner_id != viewer_id:
                continue
        by_group.setdefault(item["corpus_group"], []).append(item)

    groups = []
    extra_keys = [key for key in by_group if key not in GROUP_ORDER]
    for key in list(GROUP_ORDER) + extra_keys:
        items = by_group.get(key) or []
        if not items:
            continue
        groups.append(
            {
                "key": key,
                "label": GROUP_LABELS.get(key, key),
                "mandatory": key != GROUP_USER,
                "files": len(items),
                "chunks": sum(row.get("chunk_count") or 0 for row in items),
                "items": items,
            }
        )

    user_files = [
        _catalog_item(doc)
        for doc in documents
        if getattr(doc, "owner_id", None) is not None
        and viewer_id is not None
        and doc.owner_id == viewer_id
    ]
    return {
        "raw": grouped,
        "chunked": list(chunked.values()),
        "groups": groups,
        "userFiles": user_files,
        "totals": {
            "files": len(documents),
            "chunks": sum(doc.chunk_count or 0 for doc in documents),
        },
    }


async def _load_kb_docs(db: AsyncSession, user: User | None = None) -> list:
    stmt = select(KnowledgeBaseDocument).order_by(
        KnowledgeBaseDocument.uploaded_at.desc()
    )
    if user is not None and user.role != "admin":
        stmt = stmt.where(
            or_(
                KnowledgeBaseDocument.owner_id.is_(None),
                KnowledgeBaseDocument.owner_id == user.id,
            )
        )
    return (await db.execute(stmt)).scalars().all()


@router.get(
    "/catalog",
    response_model=SuccessResponse,
    summary="Knowledge base grouped for the officer UI",
)
async def knowledge_base_catalog(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """Return raw documents grouped by category and chunked RAG totals."""
    documents = await _load_kb_docs(db, _current_user)
    return _build_success_response(
        request, _catalog_payload(documents, viewer_id=_current_user.id)
    )


@router.get("/raw", response_model=SuccessResponse, summary="Raw KB documents by category")
async def knowledge_base_raw(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    payload = _catalog_payload(
        await _load_kb_docs(db, _current_user), viewer_id=_current_user.id
    )
    return _build_success_response(
        request,
        {
            "raw": payload["raw"],
            "groups": payload["groups"],
            "totals": payload["totals"],
        },
    )


@router.get("/chunked", response_model=SuccessResponse, summary="Chunked RAG inventory")
async def knowledge_base_chunked(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    payload = _catalog_payload(
        await _load_kb_docs(db, _current_user), viewer_id=_current_user.id
    )
    return _build_success_response(
        request,
        {
            "chunked": payload["chunked"],
            "groups": payload["groups"],
            "totals": payload["totals"],
        },
    )


# ---------------------------------------------------------------------------
# POST /knowledge-base/upload — Upload and trigger ingestion
# ---------------------------------------------------------------------------


@router.post(
    "/upload",
    response_model=SuccessResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload document for ingestion",
    description="Upload PDF, DOCX, or TXT and ingest into the knowledge base. Admin only.",
)
async def upload_knowledge_base_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(..., description="Document file (PDF, DOCX, or TXT)")],
    category: Annotated[KBCategory, Form(..., description="Document category")],
    db: Annotated[AsyncSession, Depends(get_db)],
    minio_client: Annotated[object, Depends(get_minio)],
    current_user: Annotated[User, Depends(require_role([Role.ADMIN]))],
    name: Annotated[str | None, Form(description="Optional display name")] = None,
) -> JSONResponse:
    """Upload a document and trigger async RAG ingestion.

    Req 11.2: When a new document is uploaded, automatically process it
    (extract text, chunk, embed, store) and report completion status.
    Req 11.5: If processing fails, log error and mark as failed.
    """
    file_content = await file.read()
    content_type = _validate_kb_bytes(
        file_content, file.content_type or "", file.filename or ""
    )
    file_type = ALLOWED_MIME_TYPES[content_type]
    doc_name = name or file.filename or "Untitled Document"
    doc_id = uuid.uuid4()
    storage_path = f"knowledge-base/{doc_id}"

    from app.config import get_settings
    settings = get_settings()

    try:
        import io
        minio_client.put_object(
            settings.minio_bucket,
            storage_path,
            io.BytesIO(file_content),
            length=len(file_content),
            content_type=content_type,
        )
    except Exception as e:
        logger.exception("Failed to upload file to MinIO")
        raise ValidationError(
            message="ไม่สามารถอัปโหลดไฟล์ได้ กรุณาลองใหม่อีกครั้ง",
            details={"error": str(e)},
        )

    # Create document record in database
    corpus_group = group_for_filename(doc_name, owner_id=None)
    document = KnowledgeBaseDocument(
        id=doc_id,
        name=doc_name,
        category=category,
        file_type=file_type,
        storage_path=storage_path,
        processing_status="pending",
        chunk_count=0,
        owner_id=None,
        scope="baseline",
        corpus_group=corpus_group,
    )
    db.add(document)
    await db.flush()
    await db.refresh(document)

    # Trigger async ingestion in background
    background_tasks.add_task(
        _run_ingestion,
        document_id=str(doc_id),
        document_name=doc_name,
        file_content=file_content,
        mime_type=content_type,
        app=request.app,
        extra_metadata={
            "corpus_group": corpus_group,
            "scope": "baseline",
        },
    )

    response_data = KBUploadResponse(
        id=doc_id,
        name=doc_name,
        category=category,
        file_type=file_type,
        processing_status="pending",
    ).model_dump(mode="json")

    logger.info(
        "KB document uploaded: %s (id=%s, category=%s) by user %s",
        doc_name, doc_id, category, current_user.id,
    )

    return _build_success_response(request, response_data, status_code=202)


# ---------------------------------------------------------------------------
# POST /knowledge-base/mine — Officer (or any user) private ingest
# ---------------------------------------------------------------------------


@router.post(
    "/mine",
    response_model=SuccessResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a private knowledge-base document",
    description="Chunk and embed a file visible only to the uploading user.",
)
async def upload_my_knowledge_base_document(
    request: Request,
    file: Annotated[UploadFile, File(..., description="Document file (PDF, DOCX, or TXT)")],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    category: Annotated[KBCategory | None, Form(description="Optional category")] = None,
    name: Annotated[str | None, Form(description="Optional display name")] = None,
) -> JSONResponse:
    file_content = await file.read()
    content_type = _validate_kb_bytes(
        file_content, file.content_type or "", file.filename or ""
    )
    file_type = ALLOWED_MIME_TYPES[content_type]
    doc_name = name or file.filename or "Untitled Document"
    factory = getattr(request.app.state, "db_session_factory", None) or runtime.session_factory
    doc = await ingest_file_bytes(
        db=db,
        filename=doc_name,
        content=file_content,
        mime_type=content_type,
        scope="user",
        owner_id=current_user.id,
        session_factory=factory,
        corpus_group=GROUP_USER,
        category=category.value if category is not None else None,
    )
    response_data = KBUploadResponse(
        id=doc.id,
        name=doc.name,
        category=doc.category,
        file_type=file_type,
        processing_status=doc.processing_status,
        message="เอกสารถูกอัปโหลดเฉพาะบัญชีของคุณ กำลังประมวลผลเข้า RAG",
    ).model_dump(mode="json")
    logger.info(
        "Private KB document uploaded: %s (id=%s) by user %s",
        doc.name,
        doc.id,
        current_user.id,
    )
    return _build_success_response(request, response_data, status_code=202)


@router.delete(
    "/mine/{document_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove my private knowledge-base document",
)
async def delete_my_knowledge_base_document(
    request: Request,
    document_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    stmt = select(KnowledgeBaseDocument).where(
        KnowledgeBaseDocument.id == document_id,
        KnowledgeBaseDocument.owner_id == current_user.id,
    )
    document = (await db.execute(stmt)).scalar_one_or_none()
    if document is None:
        raise NotFoundError(message="ไม่พบเอกสารที่ต้องการลบ")
    await db.execute(delete(KBChunk).where(KBChunk.document_id == document_id))
    await _purge_aux_stores(document)
    await db.delete(document)
    return _build_success_response(
        request, KBDeleteResponse(id=document_id).model_dump(mode="json")
    )


# ---------------------------------------------------------------------------
# DELETE /knowledge-base/{id} — Remove document and chunks
# ---------------------------------------------------------------------------


@router.delete(
    "/{document_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove KB document",
    description="Remove a document and its RAG chunks. Admin only.",
)
async def delete_knowledge_base_document(
    request: Request,
    document_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    minio_client: Annotated[object, Depends(get_minio)],
    current_user: Annotated[User, Depends(require_role([Role.ADMIN]))],
) -> JSONResponse:
    """Delete a KB document and its chunks.

    Removes the document record, all associated KB chunks (cascade),
    and the stored file from MinIO.
    """
    stmt = select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.id == document_id)
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if document is None:
        raise NotFoundError(message="ไม่พบเอกสารที่ต้องการลบ")

    # Delete chunks first (explicit for clarity, cascade also handles this)
    await db.execute(
        delete(KBChunk).where(KBChunk.document_id == document_id)
    )
    await _purge_aux_stores(document)

    # Try to delete file from MinIO (non-blocking on failure)
    try:
        from app.config import get_settings
        settings = get_settings()
        minio_client.remove_object(settings.minio_bucket, document.storage_path)
    except Exception as e:
        logger.warning(
            "Failed to remove file from MinIO for document %s: %s",
            document_id, str(e),
        )

    # Delete the document record
    await db.delete(document)

    response_data = KBDeleteResponse(
        id=document_id,
    ).model_dump(mode="json")

    logger.info(
        "KB document deleted: %s (id=%s) by user %s",
        document.name, document_id, current_user.id,
    )

    return _build_success_response(request, response_data)


# ---------------------------------------------------------------------------
# POST /knowledge-base/batch-ingest — Full KB re-ingestion
# ---------------------------------------------------------------------------


@router.post(
    "/batch-ingest",
    response_model=SuccessResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger full KB re-ingestion",
    description="Re-ingest all knowledge-base documents through the RAG pipeline. Admin only.",
)
async def batch_ingest(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([Role.ADMIN]))],
) -> JSONResponse:
    """Trigger batch re-ingestion of all KB documents.

    Resets all documents to 'pending' status and triggers the full
    ingestion pipeline in the background.
    Req 3.7: Batch ingestion endpoint that processes the full knowledge base.
    """
    # Get all documents
    stmt = select(KnowledgeBaseDocument)
    result = await db.execute(stmt)
    documents = result.scalars().all()

    total_documents = len(documents)

    if total_documents == 0:
        raise ValidationError(
            message="ไม่มีเอกสารในฐานความรู้ กรุณาอัปโหลดเอกสารก่อนดำเนินการ"
        )

    # Reset all documents to pending
    for doc in documents:
        doc.processing_status = "pending"
        doc.chunk_count = 0
        doc.error_message = None
        doc.processed_at = None

    await db.flush()

    # Trigger batch ingestion in background
    doc_ids = [str(doc.id) for doc in documents]
    background_tasks.add_task(
        _run_batch_ingestion,
        document_ids=doc_ids,
        app=request.app,
    )

    response_data = KBBatchIngestResponse(
        total_documents=total_documents,
    ).model_dump(mode="json")

    logger.info(
        "Batch KB re-ingestion triggered: %d documents by user %s",
        total_documents, current_user.id,
    )

    return _build_success_response(request, response_data, status_code=202)


# ---------------------------------------------------------------------------
# GET /knowledge-base/{id}/status — Processing status
# ---------------------------------------------------------------------------


@router.get(
    "/{document_id}/status",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Get document processing status",
    description="Get the current processing status of a knowledge base document. Admin only.",
)
async def get_document_status(
    request: Request,
    document_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([Role.ADMIN]))],
) -> JSONResponse:
    """Get processing status for a specific KB document.

    Returns: status, chunk count, error message (if failed).
    """
    stmt = select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.id == document_id)
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if document is None:
        raise NotFoundError(message="ไม่พบเอกสารที่ต้องการ")

    response_data = KBDocumentStatusResponse.model_validate(document).model_dump(mode="json")

    return _build_success_response(request, response_data)


# ---------------------------------------------------------------------------
# Background task helpers
# ---------------------------------------------------------------------------


async def _run_ingestion(
    document_id: str,
    document_name: str,
    file_content: bytes,
    mime_type: str,
    app,
    extra_metadata: dict | None = None,
) -> None:
    """Background task: run the full RAG ingestion pipeline for a single document.

    Writes file content to a temp file, then invokes the ingestion pipeline.
    Updates document status in the database upon completion or failure.
    """
    from app.config import get_settings
    from app.providers.factory import ProviderFactory
    from app.rag.ingestion import ingest_document

    settings = get_settings()
    tmp_path = None

    try:
        # Write file to a temp location for the extraction step
        suffix = f".{ALLOWED_MIME_TYPES.get(mime_type, 'bin')}"
        tmp_path = await write_temp_bytes(file_content, suffix)

        # Get providers
        factory = ProviderFactory(settings)
        embedding_provider = factory.get_embedding()
        vector_store_provider = factory.get_vector_store()

        # Get a fresh DB session for the background task
        session_factory = app.state.db_session_factory
        if session_factory is None:
            logger.error("DB session factory not available for ingestion task")
            return

        async with session_factory() as session:
            result = await ingest_document(
                document_id=document_id,
                document_name=document_name,
                file_path=tmp_path,
                mime_type=mime_type,
                embedding_provider=embedding_provider,
                vector_store_provider=vector_store_provider,
                session=session,
                extra_metadata=extra_metadata,
            )

            if result.success:
                logger.info(
                    "Ingestion completed for document %s: %d/%d chunks embedded",
                    document_id, result.embedded_chunks, result.total_chunks,
                )
            else:
                logger.warning(
                    "Ingestion failed for document %s: %s",
                    document_id, result.error_message,
                )

    except Exception as e:
        logger.exception(
            "Unexpected error during ingestion of document %s",
            document_id,
        )
        # Try to update document status to failed
        try:
            session_factory = app.state.db_session_factory
            if session_factory:
                async with session_factory() as session:
                    from app.rag.ingestion import _update_document_status
                    await _update_document_status(
                        session, document_id, "failed",
                        error_message=f"Unexpected error: {type(e).__name__}: {e}",
                    )
        except Exception:
            pass

    finally:
        if tmp_path:
            await unlink_path(tmp_path)


async def _run_batch_ingestion(
    document_ids: list[str],
    app,
) -> None:
    """Background task: re-ingest all specified documents.

    Processes documents sequentially through the ingestion pipeline.
    Downloads each file from MinIO before processing.
    """
    from app.config import get_settings
    from app.providers.factory import ProviderFactory
    from app.rag.ingestion import ingest_document

    settings = get_settings()

    try:
        factory = ProviderFactory(settings)
        embedding_provider = factory.get_embedding()
        vector_store_provider = factory.get_vector_store()
    except Exception:
        logger.exception("Failed to initialize providers for batch ingestion")
        return

    session_factory = app.state.db_session_factory
    if session_factory is None:
        logger.error("DB session factory not available for batch ingestion task")
        return

    minio_client = app.state.minio

    for doc_id in document_ids:
        tmp_path = None
        extra_metadata: dict | None = None
        try:
            async with session_factory() as session:
                # Fetch document record
                doc_uuid = uuid.UUID(doc_id)
                doc = await session.get(KnowledgeBaseDocument, doc_uuid)
                if doc is None:
                    logger.warning("Document %s not found for batch ingestion", doc_id)
                    continue

                extra_metadata = {
                    "corpus_group": getattr(doc, "corpus_group", None),
                    "scope": getattr(doc, "scope", None),
                    "owner_id": str(doc.owner_id) if doc.owner_id else None,
                }

                # Download file from MinIO
                try:
                    response = minio_client.get_object(
                        settings.minio_bucket, doc.storage_path
                    )
                    file_content = response.read()
                    response.close()
                    response.release_conn()
                except Exception as e:
                    logger.exception(
                        "Failed to download %s from MinIO", doc.storage_path
                    )
                    doc.processing_status = "failed"
                    doc.error_message = f"File download failed: {str(e)}"
                    await session.commit()
                    continue

                # Write to temp file
                mime_map = {"pdf": MIME_PDF, "docx": MIME_DOCX, "txt": MIME_TXT}
                mime_type = mime_map.get(doc.file_type, "application/octet-stream")
                suffix = f".{doc.file_type}"
                tmp_path = await write_temp_bytes(file_content, suffix)

                # Delete existing chunks before re-ingestion
                await session.execute(
                    delete(KBChunk).where(KBChunk.document_id == doc_uuid)
                )
                await session.commit()

            # Run ingestion with a fresh session
            async with session_factory() as session:
                result = await ingest_document(
                    document_id=doc_id,
                    document_name=doc.name,
                    file_path=tmp_path,
                    mime_type=mime_type,
                    embedding_provider=embedding_provider,
                    vector_store_provider=vector_store_provider,
                    session=session,
                    extra_metadata=extra_metadata,
                )

                if result.success:
                    logger.info(
                        "Batch ingestion: document %s completed (%d chunks)",
                        doc_id, result.embedded_chunks,
                    )
                else:
                    logger.warning(
                        "Batch ingestion: document %s failed: %s",
                        doc_id, result.error_message,
                    )

        except Exception:
            logger.exception(
                "Unexpected error in batch ingestion for document %s",
                doc_id,
            )
        finally:
            if tmp_path:
                await unlink_path(tmp_path)

    logger.info("Batch re-ingestion complete for %d documents", len(document_ids))
