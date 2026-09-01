"""Pydantic schemas for Knowledge Base management endpoints.

Covers request/response models for:
- GET /knowledge-base (list documents)
- POST /knowledge-base/upload (upload document)
- DELETE /knowledge-base/{id} (remove document)
- POST /knowledge-base/batch-ingest (re-ingest all)
- GET /knowledge-base/{id}/status (processing status)

Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


class KBCategory(StrEnum):
    """Knowledge base document categories.

    Req 11.4: Supported source types for the knowledge base.
    """

    LAW = "law"  # พ.ร.บ. / กฎหมาย
    REGULATION = "regulation"  # กฎกระทรวง
    GUIDELINE = "guideline"  # ระเบียบกระทรวงการคลัง
    CIRCULAR = "circular"  # หนังสือเวียนกรมบัญชีกลาง
    PRICE_ANNOUNCEMENT = "price_announcement"  # ประกาศราคากลาง
    MANUAL = "manual"  # คู่มือปฏิบัติงาน
    EXAMPLE_TOR = "example_tor"  # ตัวอย่าง TOR
    TEMPLATE = "template"  # แม่แบบ
    OTHER = "other"  # อื่น ๆ


class KBFileType(StrEnum):
    """Supported file types for knowledge base documents."""

    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class ProcessingStatus(StrEnum):
    """Processing status for knowledge base documents."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class KBDocumentResponse(BaseModel):
    """A knowledge base document in list/detail views.

    Req 11.3: Display document name, type, upload date, chunk count, and processing status.
    """

    id: uuid.UUID
    name: str
    category: str
    file_type: str
    processing_status: str
    chunk_count: int
    error_message: Optional[str] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    owner_id: Optional[uuid.UUID] = None
    scope: str = "baseline"
    corpus_group: str = "mandatory_raw"

    model_config = {"from_attributes": True}


class KBDocumentListResponse(BaseModel):
    """Response for listing knowledge base documents."""

    items: list[KBDocumentResponse]
    total: int


class KBDocumentStatusResponse(BaseModel):
    """Processing status detail for a single document."""

    id: uuid.UUID
    name: str
    processing_status: str
    chunk_count: int
    error_message: Optional[str] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class KBUploadResponse(BaseModel):
    """Response after uploading a document for ingestion."""

    id: uuid.UUID
    name: str
    category: str
    file_type: str
    processing_status: str = "pending"
    message: str = "เอกสารถูกอัปโหลดเรียบร้อย กำลังดำเนินการประมวลผล"


class KBDeleteResponse(BaseModel):
    """Response after deleting a document."""

    id: uuid.UUID
    message: str = "ลบเอกสารและข้อมูลที่เกี่ยวข้องเรียบร้อย"


class KBBatchIngestResponse(BaseModel):
    """Response for batch ingestion trigger."""

    total_documents: int
    message: str = "เริ่มประมวลผลเอกสารทั้งหมดแล้ว"


class KBSyncMandatoryRequest(BaseModel):
    wipe_baseline: bool = False


class KBSyncMandatoryResponse(BaseModel):
    scanned: int
    wipe_baseline: bool = False
    message: str = "เริ่มซิงก์เอกสารจากโฟลเดอร์ข้อมูลดิบ"


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class KBUploadRequest(BaseModel):
    """Metadata for document upload (sent alongside the file).

    The file itself is uploaded as multipart form data.
    """

    category: KBCategory = Field(
        ...,
        description="Document category such as law, circular, or template",
    )
    name: Optional[str] = Field(
        default=None,
        description="Optional display name. If omitted, uses the uploaded filename.",
    )
