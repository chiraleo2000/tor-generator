"""Extract, chunk, embed, and retrieve real Thai procurement PDFs.

Uses the source PDFs listed for day-to-day TOR work. Text-layer PDFs go through
the production extractor. Scanned CGD letters (no text layer) use companion
`*_tor_extract.json` or `documents/research/raw_text` extracts — not a silent skip.
Broken CID-font PDFs (gazette text layer without legal Thai) fall back to OCR
when the file is small.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import fitz
import pytest

from app.providers.constants import DEFAULT_EMBEDDING_MODEL, EMBEDDING_DIMENSIONS
from app.providers.embedding.qwen3_provider import Qwen3LocalEmbeddingProvider
from app.rag.chunking import chunk_text
from app.rag.extraction import DEFAULT_OCR_TIMEOUT, _ocr_pdf_page, extract_text
from app.rag.ingestion import ingest_document
from app.rag.retrieval import RAGRetriever
from tests.test_live_lm_studio import _require_lm_studio
from tests.test_property_embedding_round_trip import InMemoryVectorStore

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCES = REPO_ROOT / "documents" / "sources"
KB_DIR = REPO_ROOT / "documents" / "knowledge-base"
RAW_TEXT_DIR = REPO_ROOT / "documents" / "research" / "raw_text"
STRUCTURE_DIR = REPO_ROOT / "documents" / "research" / "analysis"
RAW_DIR = SOURCES / "การจัดซื้อจัดจ้าง" / "ข้อมูลดิบ"

PROCUREMENT_PDFS = (
    SOURCES / "คู่มือแนวปฏิบัติ_การจัดซื้อจัดจ้างภาครัฐ.pdf",
    RAW_DIR / "กฎกระทรวงกำหนดพัสดุที่รัฐต้องการส่งเสริมหรือสนับสนุนและกำหนดวิธีการจัดซื้อจัดจ้างพัสดุโดยวิธีคัดเลือกและวิธีเฉพาะเจาะจง พ.ศ. 2560.pdf",
    RAW_DIR / "กฎกระทรวงกำหนดเรื่องการจัดซื้อจัดจ้างกับหน่วยงานของรัฐที่ใช้สิทธิอุทธรณ์ไม่ได้ พ.ศ. 2568.pdf",
    RAW_DIR / "กฎกระทรวงกำหนดเรื่องการจัดซื้อจัดจ้างกับหน่วยงานของรัฐที่ใช้สิทธิอุทธรณ์ไม่ได้ พ.ศ.2560.pdf",
    RAW_DIR / "กฎกระทรวงกำหนดวงเงินการจัดซื้อจัดจ้างพัสดุโดยวิธีเฉพาะเจาะจงวงเงิน.pdf",
    RAW_DIR / "กฎกระทรวงกำหนดหลักเกณฑ์ วิธีการ และเงื่อนไขการขึ้นทะเบียนที่ปรึกษา พ.ศ. 2560.pdf",
    RAW_DIR / "กฎกระทรวงกำหนดหลักเกณฑ์เกี่ยวกับผู้ที่มีสิทธิขึ้นทะเบียนผู้ประกอบการ พ.ศ. 2560.pdf",
    RAW_DIR / "กฎกระทรวงกำหนดให้หน่วยงานอื่นเป็นหน่วยงานของรัฐตามพระราชบัญญัติการจัดซื้อจัดจ้างและ.pdf",
    RAW_DIR / "กฎกระทรวงกำหนดอัตราค่าจ้างผู้ให้บริการงานจ้างออกแบบหรือควบคุมงานก่อสร้าง พ.ศ.2562.pdf",
    RAW_DIR / "การจัดซื้อจัดจ้างโดยรัฐ.pdf",
    RAW_DIR / "การจัดซื้อจัดจ้างที่ไม่ทำข้อตกลงเป็นหนังสือ และวงเงินการจัดซื้อจัดจ้างในการแต่งตั้งผู้ตรวจรับพัสดุ.pdf",
    RAW_DIR / "คู่มือการจัดซื้อจัดจ้างตามพระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560 และ ระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560.pdf",
    RAW_DIR / "คู่มือการปฏิบัติงานการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐสำนักข่าวกรองแห่งชาติ.pdf",
    RAW_DIR / "คู่มือปฏิบัติงานตามระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและบริหารพัสดุ พ.ศ.2560.pdf",
    RAW_DIR / "จัดซื้อจัดจ้าง_2560.pdf",
    RAW_DIR / "พรบ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560.pdf",
    RAW_DIR / "พระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ.2560.pdf",
    RAW_DIR / "ระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560.pdf",
    RAW_DIR / "ระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ.2560.pdf",
    RAW_DIR / "หนังสือกรมบัญชีกลาง ด่วนที่สุด ที่ กค 0405.4ว 322 ลงวันที่ 24 สิงหาคม 2560.pdf",
    RAW_DIR / "หนังสือกรมบัญชีกลาง ที่ กค (กวจ) 0405.2ว 336 ลงวันที่ 4 กันยายน 2560.pdf",
    RAW_DIR / "หนังสือกรมบัญชีกลาง ที่ กค (กวจ) 0405.2ว 346 ลงวันที่ 8 กันยายน 2560.pdf",
    RAW_DIR / "หนังสือกรมบัญชีกลาง ที่ กค (กวจ) 0405.2ว 347 ลงวันที่ 8 กันยายน 2560.pdf",
    RAW_DIR / "หนังสือกรมบัญชีกลาง ที่ กค (กวจ) 0405.2ว 356 ลงวันที่ 13 กันยายน 2560.pdf",
    RAW_DIR / "หนังสือกรมบัญชีกลาง ที่ กค (กวจ) 0405.2ว 360 ลงวันที่ 15 กันยายน 2560.pdf",
    RAW_DIR / "หนังสือกรมบัญชีกลาง ที่ กค (กวพ) 0405.2ว 320 ลงวันที่ 24 สิงหาคม 2560.pdf",
    RAW_DIR / "หนังสือคณะกรรมการวินิจฉัยปัญหาการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐกรมบัญชีกลาง.pdf",
)

_KEYWORDS = (
    "จัดซื้อ",
    "จัดจ้าง",
    "พัสดุ",
    "มาตรา",
    "ระเบียบ",
    "กฎกระทรวง",
    "กรมบัญชีกลาง",
    "เฉพาะเจาะจง",
)

_INGEST_PDF = RAW_DIR / "กฎกระทรวงกำหนดวงเงินการจัดซื้อจัดจ้างพัสดุโดยวิธีเฉพาะเจาะจงวงเงิน.pdf"
_INGEST_DOCUMENT_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_MAX_OCR_PAGES = 6


def _pdf_page_texts(path: Path) -> list[str]:
    document = fitz.open(str(path))
    try:
        return [page.get_text().strip() for page in document]
    finally:
        document.close()


def _direct_pdf_text(path: Path) -> str:
    return "\n\n".join(text for text in _pdf_page_texts(path) if text).strip()


def _all_pages_have_text_layer(path: Path, min_chars: int = 10) -> bool:
    pages = _pdf_page_texts(path)
    return bool(pages) and all(len(text) >= min_chars for text in pages)


def _has_procurement_keywords(text: str) -> bool:
    return any(keyword in text for keyword in _KEYWORDS)


def _companion_file(directory: Path, pdf: Path, suffix: str) -> Path | None:
    if not directory.is_dir():
        return None
    exact = directory / f"{pdf.stem}{suffix}"
    if exact.is_file():
        return exact
    best: Path | None = None
    best_len = 0
    for candidate in directory.glob(f"*{suffix}"):
        key = candidate.name.removesuffix(suffix)
        if pdf.stem.startswith(key) and len(key) > best_len:
            best = candidate
            best_len = len(key)
    return best


def _text_from_json_extract(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    parts: list[str] = []
    for sections in (payload.get("focus_areas") or {}).values():
        if not isinstance(sections, list):
            continue
        for section in sections:
            content = (section or {}).get("content") or ""
            if content.strip():
                parts.append(content)
    return "\n\n".join(parts).strip()


def _read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "utf-16"):
        try:
            return raw.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace").strip()


def _text_from_structure(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    parts: list[str] = []
    for key in ("title", "short_title", "summary", "issuer"):
        value = payload.get(key)
        if value:
            parts.append(str(value))
    for item in payload.get("key_provisions") or []:
        if isinstance(item, dict):
            parts.append(str(item.get("text") or item.get("content") or item))
        elif item:
            parts.append(str(item))
    notes = payload.get("notes")
    if notes:
        parts.append(str(notes))
    return "\n\n".join(part for part in parts if part.strip()).strip()


def _ocr_small_pdf(path: Path) -> str:
    document = fitz.open(str(path))
    warnings: list[str] = []
    try:
        if len(document) > _MAX_OCR_PAGES:
            return ""
        parts = [
            _ocr_pdf_page(document[index], index, DEFAULT_OCR_TIMEOUT, warnings)
            for index in range(len(document))
        ]
        return "\n\n".join(part for part in parts if part).strip()
    finally:
        document.close()


@lru_cache(maxsize=None)
def load_rag_text(pdf: Path) -> tuple[str, str]:
    """Return (text, source) with procurement Thai suitable for chunking."""
    pages = _pdf_page_texts(pdf)
    direct = "\n\n".join(text for text in pages if text).strip()
    if (
        pages
        and all(len(text) >= 10 for text in pages)
        and _has_procurement_keywords(direct)
    ):
        result = extract_text(str(pdf), "application/pdf")
        if result.text.strip() and _has_procurement_keywords(result.text):
            assert result.method == "direct", (
                f"{pdf.name} unexpectedly used OCR ({result.method})"
            )
            return result.text, f"pdf:{result.method}:pages={result.page_count}"
    if len(direct) >= 200 and _has_procurement_keywords(direct):
        return direct, f"pdf:text-layer-only:chars={len(direct)}"

    json_path = _companion_file(KB_DIR, pdf, "_tor_extract.json")
    if json_path is not None:
        text = _text_from_json_extract(json_path)
        if _has_procurement_keywords(text):
            return text, f"json:{json_path.name}"

    raw_path = _companion_file(RAW_TEXT_DIR, pdf, ".txt")
    if raw_path is not None:
        text = _read_text_file(raw_path)
        if _has_procurement_keywords(text):
            return text, f"raw:{raw_path.name}"

    if 0 < len(pages) <= _MAX_OCR_PAGES:
        ocr_text = _ocr_small_pdf(pdf)
        if _has_procurement_keywords(ocr_text):
            return ocr_text, f"ocr:pages={len(pages)}"

    structure_path = _companion_file(STRUCTURE_DIR, pdf, "_structure.json")
    if structure_path is not None:
        text = _text_from_structure(structure_path)
        if _has_procurement_keywords(text):
            return text, f"structure:{structure_path.name}"

    pytest.fail(
        f"No usable RAG text for {pdf.name} (direct PDF chars={len(direct)}; "
        "need a knowledge-base JSON extract, research raw_text, OCR, or structure file)"
    )


def _path_is_regular_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError as exc:
        if getattr(exc, "errno", None) == 36:
            pytest.skip("Linux bind-mount cannot stat long Thai PDF names")
        raise


def test_all_listed_procurement_pdfs_exist():
    missing = [str(path) for path in PROCUREMENT_PDFS if not _path_is_regular_file(path)]
    assert not missing, "Missing procurement PDFs:\n" + "\n".join(missing)
    assert len(PROCUREMENT_PDFS) == 27


def test_extract_and_chunk_all_listed_procurement_pdfs():
    reports: list[str] = []
    for path in PROCUREMENT_PDFS:
        assert _path_is_regular_file(path), f"Missing {path}"
        text, source = load_rag_text(path)
        assert _has_procurement_keywords(text), (
            f"{path.name} ({source}) has no procurement keywords"
        )
        chunked = chunk_text(text, document_id=path.stem[:80])
        assert chunked.total_tokens > 0, f"{path.name} tokenized to 0"
        assert chunked.chunks, f"{path.name} produced no chunks"
        assert all(chunk.text.strip() for chunk in chunked.chunks)
        reports.append(
            f"{path.stem[:48]} source={source} tokens={chunked.total_tokens} "
            f"chunks={len(chunked.chunks)}"
        )
    assert len(reports) == 27
    companion_rows = [
        row
        for row in reports
        if " source=json:" in row or " source=raw:" in row or " source=ocr:" in row
    ]
    assert companion_rows, (
        "Expected scanned or broken-font PDFs to use JSON, raw_text, or OCR"
    )
    print("\n".join(reports))


@pytest.mark.integration
@pytest.mark.live_llm
@pytest.mark.asyncio
async def test_live_embeddinggemma_excerpts_from_each_procurement_pdf():
    base = _require_lm_studio()
    provider = Qwen3LocalEmbeddingProvider(
        base_url=base,
        model=DEFAULT_EMBEDDING_MODEL,
        timeout=60.0,
    )
    for path in PROCUREMENT_PDFS:
        text, source = load_rag_text(path)
        excerpt = text[:800].strip()
        vector = await provider.embed_query(excerpt)
        assert len(vector) == EMBEDDING_DIMENSIONS, (
            f"{path.name} ({source}) embedding dim {len(vector)} != {EMBEDDING_DIMENSIONS}"
        )


@pytest.mark.integration
@pytest.mark.live_llm
@pytest.mark.asyncio
async def test_live_ingest_and_retrieve_specific_method_threshold():
    assert _INGEST_PDF.is_file(), f"Missing {_INGEST_PDF}"
    assert _all_pages_have_text_layer(_INGEST_PDF), (
        f"{_INGEST_PDF.name} has scanned pages; ingest_document would OCR and hang"
    )
    base = _require_lm_studio()
    embedding = Qwen3LocalEmbeddingProvider(
        base_url=base,
        model=DEFAULT_EMBEDDING_MODEL,
        timeout=60.0,
    )
    store = InMemoryVectorStore()
    result = await ingest_document(
        document_id=_INGEST_DOCUMENT_ID,
        document_name=_INGEST_PDF.stem,
        file_path=str(_INGEST_PDF),
        mime_type="application/pdf",
        embedding_provider=embedding,
        vector_store_provider=store,
        session=None,
    )
    assert result.success, result.error_message
    assert result.embedded_chunks >= 1
    retrieved = await RAGRetriever(embedding, store).retrieve(
        "วงเงินจัดซื้อจัดจ้างโดยวิธีเฉพาะเจาะจง",
        top_k=3,
    )
    assert retrieved.actual_count >= 1
    blob = " ".join(chunk.text for chunk in retrieved.chunks)
    assert "เฉพาะเจาะจง" in blob or "วงเงิน" in blob
    assert retrieved.chunks[0].score > 0.15
