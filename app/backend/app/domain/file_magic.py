"""Detect upload types from magic bytes instead of trusting the client MIME."""

from __future__ import annotations

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DOC_MIME = "application/msword"
PNG_MIME = "image/png"
JPEG_MIME = "image/jpeg"
GIF_MIME = "image/gif"
WEBP_MIME = "image/webp"

ALLOWED_DOCUMENT_MIMES = frozenset({PDF_MIME, DOCX_MIME, DOC_MIME})
ALLOWED_IMAGE_MIMES = frozenset({PNG_MIME, JPEG_MIME, GIF_MIME, WEBP_MIME})
ALLOWED_UPLOAD_MIMES = ALLOWED_DOCUMENT_MIMES | ALLOWED_IMAGE_MIMES

_ZIP_PREFIX = b"PK\x03\x04"
_OLE_PREFIX = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def detect_mime(content: bytes, claimed_mime: str = "") -> str | None:
    """Return a canonical MIME type from file signatures.

    ``claimed_mime`` is ignored — clients can spoof Content-Type.
    """
    del claimed_mime
    if len(content) < 8:
        return None
    if content.startswith(b"%PDF"):
        return PDF_MIME
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return PNG_MIME
    if content.startswith(b"\xff\xd8\xff"):
        return JPEG_MIME
    if content.startswith((b"GIF87a", b"GIF89a")):
        return GIF_MIME
    if content.startswith(b"RIFF") and len(content) >= 12 and content[8:12] == b"WEBP":
        return WEBP_MIME
    if content.startswith(_ZIP_PREFIX) and b"word/" in content[:8192]:
        return DOCX_MIME
    if content.startswith(_OLE_PREFIX):
        return DOC_MIME
    return None


def require_allowed_upload(content: bytes, claimed_mime: str) -> str:
    """Validate bytes against the allowlist. Raises ValueError on rejection."""
    detected = detect_mime(content, claimed_mime)
    if detected is None or detected not in ALLOWED_UPLOAD_MIMES:
        raise ValueError("ประเภทไฟล์ไม่รองรับ รองรับ PDF, Word และรูปภาพเท่านั้น")
    return detected


def require_kb_upload(content: bytes, claimed_mime: str, filename: str = "") -> str:
    """Allow PDF/DOCX by magic bytes, or UTF-8-ish text. Reject executables."""
    detected = detect_mime(content, claimed_mime)
    if detected in ALLOWED_DOCUMENT_MIMES:
        return detected
    name = (filename or "").lower()
    looks_text = claimed_mime.startswith("text/") or name.endswith(".txt")
    if looks_text and not content.startswith((b"MZ", b"%PDF", b"\x7fELF", b"PK\x03\x04")):
        return "text/plain"
    raise ValueError("ประเภทไฟล์ไม่รองรับ กรุณาอัปโหลดไฟล์ PDF, Word หรือ TXT")
