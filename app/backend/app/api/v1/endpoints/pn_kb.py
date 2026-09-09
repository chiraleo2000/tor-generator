"""PN multi-RAG API: list groups, upload+verify, ingest (Embed 4 → S3 Vectors), search.

Ingest path (easiest): POST /pn/kb/upload?ingest=true  or  POST /pn/kb/ingest
Search path: MCP retrieve with rag_group, or POST /pn/kb/search
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.deps import get_current_user, get_minio
from app.exceptions import ValidationError
from app.models.user import User
from app.pn_rag.config import get_rag_groups_config
from app.pn_rag.ingest import ingest_bytes, ingest_object_key, ingest_result_dict
from app.pn_rag.retrieve import retrieve_pn_chunks
from app.pn_rag.storage import PnS3Storage, upload_result_dict, verify_result_dict
from app.rbac import Role, require_role
from app.schemas.responses import SuccessResponse

logger = logging.getLogger("tor_app.api.pn_kb")

router = APIRouter()


class VerifyBody(BaseModel):
    object_key: str = Field(..., min_length=1)
    rag_group: str | None = None
    expected_sha256: str | None = None


class IngestBody(BaseModel):
    object_key: str = Field(..., min_length=1)
    rag_group: str | None = None
    source_document: str | None = None


class SearchBody(BaseModel):
    query: str = Field(..., min_length=1)
    rag_group: str | None = None
    top_k: int = Field(default=3, ge=1, le=5)


def _storage(minio_client: object) -> PnS3Storage:
    return PnS3Storage(minio_client)  # type: ignore[arg-type]


@router.get(
    "/groups",
    response_model=SuccessResponse,
    summary="List RAG groups on the shared S3 bucket",
)
async def list_pn_rag_groups(
    _user: Annotated[User, Depends(get_current_user)],
    mcp_only: Annotated[bool, Query(description="Only groups exposed to MCP")] = False,
) -> JSONResponse:
    cfg = get_rag_groups_config()
    groups = cfg.mcp_groups() if mcp_only else list(cfg.groups)
    payload = {
        "bucket": cfg.bucket,
        "default_group": cfg.default_group,
        "chunk_target_tokens": cfg.chunk_target_tokens,
        "embedding_model": cfg.embedding_model,
        "groups": [
            {
                "id": g.id,
                "name": g.name,
                "description": g.description,
                "prefix": g.prefix,
                "vector_index": g.vector_index,
                "mcp_enabled": g.mcp_enabled,
            }
            for g in groups
        ],
    }
    return JSONResponse(
        content={"success": True, "data": payload, "message": "ok", "errors": []}
    )


@router.post(
    "/upload",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload file to S3 under a rag_group; optionally ingest into S3 Vectors",
)
async def upload_pn_kb_file(
    file: Annotated[UploadFile, File(description="PDF, DOCX, TXT, or KB JSON")],
    minio_client: Annotated[object, Depends(get_minio)],
    current_user: Annotated[User, Depends(require_role([Role.ADMIN]))],
    rag_group: Annotated[
        str | None, Form(description="RAG group id; default from config")
    ] = None,
    ingest: Annotated[
        bool,
        Form(description="If true, chunk ~4096 + Cohere Embed 4 + put S3 Vectors"),
    ] = False,
) -> JSONResponse:
    """Easiest ingest entry: API upload → S3 sources/ + manifest + optional vector index."""
    raw = await file.read()
    try:
        if ingest:
            result = await ingest_bytes(
                raw,
                filename=file.filename or "document.bin",
                rag_group=rag_group,
                minio_client=minio_client,  # type: ignore[arg-type]
                claimed_mime=file.content_type or "",
                run_embed=True,
            )
            data: dict[str, Any] = ingest_result_dict(result)
            message = "uploaded, verified, and indexed"
        else:
            result_up = _storage(minio_client).upload_and_verify(
                raw,
                filename=file.filename or "document.bin",
                rag_group=rag_group,
                claimed_mime=file.content_type or "",
            )
            data = upload_result_dict(result_up)
            data["next"] = (
                "file stored+verified on S3; POST /pn/kb/ingest with object_key "
                "or re-upload with ingest=true"
            )
            message = "uploaded and verified"
    except ValueError as exc:
        raise ValidationError(message=str(exc), details={}) from exc
    except Exception as exc:
        logger.exception("PN upload failed user=%s", current_user.id)
        raise ValidationError(
            message="อัปโหลดหรือตรวจสอบไฟล์บน S3 ไม่สำเร็จ",
            details={"error": str(exc)},
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "success": True,
            "data": data,
            "message": message,
            "errors": [],
        },
    )


@router.post(
    "/ingest",
    response_model=SuccessResponse,
    summary="Ingest an existing S3 object: chunk → Embed 4 → S3 Vectors",
)
async def ingest_pn_kb_object(
    body: IngestBody,
    minio_client: Annotated[object, Depends(get_minio)],
    current_user: Annotated[User, Depends(require_role([Role.ADMIN]))],
) -> JSONResponse:
    try:
        result = await ingest_object_key(
            body.object_key,
            rag_group=body.rag_group,
            minio_client=minio_client,  # type: ignore[arg-type]
            source_document=body.source_document,
        )
    except ValueError as exc:
        raise ValidationError(message=str(exc), details={}) from exc
    except Exception as exc:
        logger.exception("PN ingest failed user=%s key=%s", current_user.id, body.object_key)
        raise ValidationError(
            message="ingest / embed ไป S3 Vectors ไม่สำเร็จ",
            details={"error": str(exc)},
        ) from exc
    return JSONResponse(
        content={
            "success": True,
            "data": ingest_result_dict(result),
            "message": "indexed",
            "errors": [],
        }
    )


@router.post(
    "/search",
    response_model=SuccessResponse,
    summary="Search one rag_group via S3 Vectors (same path as MCP retrieve)",
)
async def search_pn_kb(
    body: SearchBody,
    minio_client: Annotated[object, Depends(get_minio)],
    _user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    try:
        chunks = await retrieve_pn_chunks(
            body.query,
            rag_group=body.rag_group,
            top_k=body.top_k,
            minio_client=minio_client,  # type: ignore[arg-type]
        )
    except ValueError as exc:
        raise ValidationError(message=str(exc), details={}) from exc
    except Exception as exc:
        logger.exception("PN search failed")
        raise ValidationError(
            message="ค้นหา S3 Vectors ไม่สำเร็จ",
            details={"error": str(exc)},
        ) from exc
    cfg = get_rag_groups_config()
    group = cfg.require(body.rag_group)
    return JSONResponse(
        content={
            "success": True,
            "data": {
                "rag_group": group.id,
                "vector_index": group.vector_index,
                "chunks": chunks,
                "count": len(chunks),
            },
            "message": "ok",
            "errors": [],
        }
    )


@router.post(
    "/verify",
    response_model=SuccessResponse,
    summary="Verify an existing S3 object for a rag_group",
)
async def verify_pn_kb_object(
    body: VerifyBody,
    minio_client: Annotated[object, Depends(get_minio)],
    _user: Annotated[User, Depends(require_role([Role.ADMIN]))],
) -> JSONResponse:
    result = _storage(minio_client).verify_object(
        body.object_key,
        expected_sha256=body.expected_sha256,
        rag_group=body.rag_group,
    )
    return JSONResponse(
        content={
            "success": result.ok,
            "data": verify_result_dict(result),
            "message": result.message,
            "errors": [] if result.ok else [result.message],
        }
    )


@router.get(
    "/objects",
    response_model=SuccessResponse,
    summary="List source object keys under a rag_group",
)
async def list_pn_kb_objects(
    minio_client: Annotated[object, Depends(get_minio)],
    _user: Annotated[User, Depends(require_role([Role.ADMIN]))],
    rag_group: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> JSONResponse:
    try:
        keys = _storage(minio_client).list_source_keys(rag_group, limit=limit)
    except ValueError as exc:
        raise ValidationError(message=str(exc), details={}) from exc
    cfg = get_rag_groups_config()
    group = cfg.require(rag_group)
    return JSONResponse(
        content={
            "success": True,
            "data": {
                "rag_group": group.id,
                "vector_index": group.vector_index,
                "prefix": group.sources_prefix(),
                "keys": keys,
                "count": len(keys),
            },
            "message": "ok",
            "errors": [],
        }
    )
