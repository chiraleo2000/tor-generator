"""Question checks for raw-folder chunk JSON.

Kept separate from the 27-file list in test_real_procurement_pdfs.py.
Reads *_tor_extract.json only. Does not OCR. The live retrieval test runs
only when CIRCULAR_LIVE_RETRIEVAL=1 and LM Studio is up.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from tests.repo_paths import knowledge_base_dir, repo_root

RAW_DIR = repo_root() / "documents" / "sources" / "การจัดซื้อจัดจ้าง" / "ข้อมูลดิบ"
KB_DIR = knowledge_base_dir(repo_root())
_THAI_DIGITS = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")
_HEADING_MARKERS = ("เรื่อง", "เรือง")
_DOC_NUMBER = re.compile(r"(?:ว\s*|c)(\d{2,4})", re.IGNORECASE)

# id, question, filename needles (all), chunk keywords (all)
CHAT_QUESTIONS: list[tuple[str, str, tuple[str, ...], tuple[str, ...]]] = [
    (
        "ว56",
        "หนังสือ ว56 แนวทางส่งเสริมหรือสนับสนุนกำหนดแนวทางอย่างไร",
        ("ว56", "ส่งเสริม"),
        ("ส่งเสริม", "สนับสนุน"),
    ),
    (
        "ว124",
        "หนังสือ ว124 การเร่งรัดการปฏิบัติให้ทำอย่างไร",
        ("ว124", "เร่งรัด"),
        ("เร่งรัด",),
    ),
    (
        "ว126",
        "หนังสือ ว126 เหตุบอกเลิกสัญญาหรือข้อตกลงคืออะไร",
        ("ว126", "บอกเลิก"),
        ("บอกเลิก",),
    ),
    (
        "ว645",
        "หนังสือ ว645 มาตรการช่วยเหลือผู้ประกอบการกำหนดอะไร",
        ("ว645", "ช่วยเหลือ"),
        ("ช่วยเหลือ", "ผู้ประกอบการ"),
    ),
    (
        "ว837",
        "หนังสือ ว837 การจัดซื้อจัดจ้างกรณีอุทกภัยให้ทำอย่างไร",
        ("ว837", "อุทกภัย"),
        ("อุทกภัย",),
    ),
    (
        "ธนาคารกรุงไทย",
        "บริษัทธนาคารกรุงไทยจำกัด (มหาชน) และบริษัทในเครือที่เป็นรัฐวิสาหกิจมีอะไรบ้าง",
        ("เกี่ยวกับการพาณิชย์.pdf",),
        ("ธนาคารกรุงไทย", "รัฐวิสาหกิจ"),
    ),
    (
        "แบบสัญญา-3",
        "ประกาศ กนบ. แบบสัญญา ฉบับที่ 3 กำหนดแบบสัญญาไว้อย่างไร",
        ("แบบสัญญา", "ฉบับที่+3"),
        ("แบบสัญญา",),
    ),
    (
        "อุทธรณ์ไม่ได้",
        "กฎกระทรวงเรื่องที่ใช้สิทธิอุทธรณ์ไม่ได้กำหนดเรื่องใด",
        ("อุทธรณ์ไม่ได้",),
        ("อุทธรณ์",),
    ),
    (
        "พัสดุ-2564",
        "กฎกระทรวงกำหนดพัสดุ ฉบับที่ 3 พ.ศ. 2564 กำหนดอะไร",
        ("ฉบับที่+3", "2564", "กำหนดพัสดุ"),
        ("กำหนดพัสดุ", "2564"),
    ),
    (
        "พัสดุ-2566",
        "กฎกระทรวงกำหนดพัสดุ ฉบับที่ 4 พ.ศ. 2566 กำหนดอะไร",
        ("ฉบับที่+4", "2566", "กำหนดพัสดุ"),
        ("กำหนดพัสดุ", "2566"),
    ),
]


def _chunk_text(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    parts: list[str] = []
    focus = payload.get("focus_areas") if isinstance(payload, dict) else None
    if isinstance(focus, dict):
        for sections in focus.values():
            if not isinstance(sections, list):
                continue
            for section in sections:
                if not isinstance(section, dict):
                    continue
                content = str(section.get("content") or "").strip()
                if content:
                    parts.append(content)
    return "\n".join(parts).strip()


def _extract_path(pdf: Path) -> Path:
    return KB_DIR / f"{pdf.stem}_tor_extract.json"


def _match_pdfs(needles: tuple[str, ...]) -> list[Path]:
    return [
        pdf
        for pdf in sorted(RAW_DIR.glob("*.pdf"))
        if all(needle in pdf.name for needle in needles)
    ]


def _forms(token: str) -> tuple[str, ...]:
    thai = token.translate(_THAI_DIGITS)
    if thai == token:
        return (token,)
    return (token, thai)


def _has_token(token: str, text: str) -> bool:
    compact = re.sub(r"\s+", "", text)
    return any(form in text or form in compact for form in _forms(token))


def _heading_phrase(text: str) -> str:
    compact = re.sub(r"\s+", "", text)
    index = -1
    for marker in _HEADING_MARKERS:
        found = compact.find(marker)
        if found >= 0 and (index < 0 or found < index):
            index = found
    if index < 0:
        raise AssertionError("chunk ไม่มีหัวเรื่อง")
    phrase = compact[index : index + 36]
    stop = phrase.find("เรียน")
    if stop > 8:
        phrase = phrase[:stop]
    return phrase


def _kok_and_mof_pdfs() -> list[Path]:
    rows: list[Path] = []
    for pdf in sorted(RAW_DIR.glob("*.pdf")):
        name = pdf.name
        if "กค" in name and "กวจ" in name:
            rows.append(pdf)
        elif "mof" in name.lower() and "2560" in name:
            rows.append(pdf)
    return rows


def test_named_circulars_have_keywords_in_their_chunks():
    failures: list[str] = []
    for label, _question, file_needles, keywords in CHAT_QUESTIONS:
        pdfs = _match_pdfs(file_needles)
        if not pdfs:
            failures.append(f"{label}: ไม่พบ PDF ที่ชื่อมี {file_needles}")
            continue
        for pdf in pdfs:
            extract = _extract_path(pdf)
            if not extract.is_file():
                failures.append(f"{label}: ไม่มี chunk JSON สำหรับ {pdf.name}")
                continue
            text = _chunk_text(extract)
            if not text:
                failures.append(f"{label}: chunk ว่าง {extract.name}")
                continue
            for keyword in keywords:
                if not _has_token(keyword, text):
                    failures.append(f"{label}: chunk ของ {pdf.name} ไม่มี {keyword}")
    if failures:
        pytest.fail("\n".join(failures))


def test_kok_and_mof_2560_numbers_appear_in_chunks():
    pdfs = _kok_and_mof_pdfs()
    assert pdfs, "ไม่พบหนังสือ กค (กวจ) หรือ mof ปี 2560 ในข้อมูลดิบ"
    failures: list[str] = []
    for pdf in pdfs:
        numbers = _DOC_NUMBER.findall(pdf.name)
        if not numbers:
            failures.append(f"{pdf.name}: ชื่อไฟล์ไม่มีเลขหนังสือ")
            continue
        extract = _extract_path(pdf)
        if not extract.is_file():
            failures.append(f"{pdf.name}: ไม่มี chunk JSON")
            continue
        text = _chunk_text(extract)
        if not text:
            failures.append(f"{pdf.name}: chunk ว่าง")
            continue
        missing = [number for number in numbers if not _has_token(number, text)]
        if missing:
            failures.append(f"{pdf.name}: chunk ไม่มีเลข {', '.join(missing)}")
    if failures:
        pytest.fail("\n".join(failures))


def test_opaque_filenames_use_heading_inside_the_chunk():
    for filename in ("8.pdf", "647 จัดซื้อจัดจ้าง.pdf", "13032561.pdf"):
        pdf = RAW_DIR / filename
        assert pdf.is_file(), filename
        text = _chunk_text(_extract_path(pdf))
        assert text, f"chunk ว่าง: {filename}"
        phrase = _heading_phrase(text)
        assert phrase in re.sub(r"\s+", "", text)
        assert len(phrase) >= 12


def _group_pdfs() -> dict[str, Path]:
    circular = (_match_pdfs(("ว56", "ส่งเสริม")) or [None])[0]
    contract = (_match_pdfs(("แบบสัญญา", "ฉบับที่+3")) or [None])[0]
    regulation = (_match_pdfs(("อุทธรณ์ไม่ได้",)) or [None])[0]
    letters = _kok_and_mof_pdfs()
    assert circular
    assert contract
    assert regulation
    assert letters
    return {
        "circular": circular,
        "contract": contract,
        "regulation": regulation,
        "letter": letters[0],
        "opaque": RAW_DIR / "8.pdf",
    }


@pytest.mark.integration
@pytest.mark.live_llm
@pytest.mark.asyncio
async def test_live_retrieve_one_question_per_group():
    """One retrieved chunk per group must come from that group's file. No OCR."""
    if os.environ.get("CIRCULAR_LIVE_RETRIEVAL") != "1":
        pytest.skip("ตั้ง CIRCULAR_LIVE_RETRIEVAL=1 เมื่อบริการฝังเวกเตอร์ว่าง")
    from app.providers.constants import DEFAULT_EMBEDDING_MODEL, EMBEDDING_DIMENSIONS
    from app.providers.embedding.qwen3_provider import Qwen3LocalEmbeddingProvider
    from app.rag.retrieval import RAGRetriever
    from tests.test_live_lm_studio import _require_lm_studio
    from tests.test_property_embedding_round_trip import InMemoryVectorStore

    groups = _group_pdfs()
    base = _require_lm_studio()
    embedding = Qwen3LocalEmbeddingProvider(
        base_url=base,
        model=DEFAULT_EMBEDDING_MODEL,
        timeout=90.0,
    )
    store = InMemoryVectorStore()
    questions: dict[str, str] = {}
    for index, (group, pdf) in enumerate(groups.items()):
        text = _chunk_text(_extract_path(pdf))
        assert text, group
        excerpt = text[:1500]
        vectors = await embedding.embed_documents([excerpt])
        assert vectors
        assert len(vectors[0]) == EMBEDDING_DIMENSIONS
        await store.upsert(
            f"circular-{index}",
            vectors[0],
            {"chunk_text": excerpt, "source_document": pdf.name},
        )
        questions[group] = _heading_phrase(text) if group == "opaque" else excerpt[:80]
    retriever = RAGRetriever(embedding, store)
    allowed = {pdf.name for pdf in groups.values()}
    for group, question in questions.items():
        retrieved = await retriever.retrieve(question, top_k=3)
        assert retrieved.chunks, group
        names = {chunk.source_document for chunk in retrieved.chunks}
        assert names & allowed, group
        assert groups[group].name in names, group
