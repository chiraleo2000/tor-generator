"""Judgment answer quality from chunk JSON. Skips until those JSON files exist.

Does not OCR and does not call a live model. Context is built with the
existing knowledge-base prompt packer.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.domain.corpus import repo_root
from app.rag.kb_qa import build_kb_qa_messages

_CASE_NUMBER = re.compile(r"([0-9]{5}-[0-9]{6})")
_FORBIDDEN_OPENINGS = ("ตามที่", "จากการศึกษา", "จากบริบท")
_JSON_SKIP = (
    "ยังไม่มี chunk JSON ที่ documents/knowledge-base/คำพิพากษา "
    "— ข้ามจนกว่าจะสร้างไฟล์ *_tor_extract.json"
)


def _judgment_json_paths() -> list[Path]:
    root = repo_root()
    if root is None:
        pytest.skip(_JSON_SKIP)
    folder = root / "documents" / "knowledge-base" / "คำพิพากษา"
    if not folder.is_dir():
        pytest.skip(_JSON_SKIP)
    paths = sorted(folder.glob("*_tor_extract.json"))
    if not paths:
        pytest.skip(_JSON_SKIP)
    return paths


def _case_number(filename: str) -> str:
    match = _CASE_NUMBER.search(Path(filename).name)
    if not match:
        raise AssertionError(f"ชื่อไฟล์ไม่มีเลขคดีแบบ 01012-610054: {filename}")
    return match.group(1)


def _chunk_texts(payload: dict) -> list[str]:
    texts: list[str] = []
    focus = payload.get("focus_areas")
    if isinstance(focus, dict):
        for sections in focus.values():
            if not isinstance(sections, list):
                continue
            for section in sections:
                if not isinstance(section, dict):
                    continue
                content = str(section.get("content") or "").strip()
                if content:
                    texts.append(content)
    chunks = payload.get("chunks")
    if isinstance(chunks, list):
        for item in chunks:
            if not isinstance(item, dict):
                continue
            content = str(item.get("content") or item.get("text") or "").strip()
            if content:
                texts.append(content)
    return texts


def _source_name(payload: dict, path: Path) -> str:
    source = str(payload.get("source_file") or "").strip()
    if source:
        return Path(source).name
    stem = path.name.replace("_tor_extract.json", "")
    return stem if stem.lower().endswith(".pdf") else f"{stem}.pdf"


def answer_meets_quality(
    answer: str,
    *,
    case_number: str,
    filename: str,
    has_source: bool,
) -> bool:
    """Substance first, cites this file and this case, and does not invent a source."""
    text = (answer or "").strip().lstrip("\"'« ")
    if not has_source or not text:
        return False
    if text.startswith(_FORBIDDEN_OPENINGS):
        return False
    if filename not in text:
        return False
    without_file = text.replace(filename, "")
    if case_number not in without_file:
        return False
    other_cases = [item for item in _CASE_NUMBER.findall(without_file) if item != case_number]
    if other_cases:
        return False
    body = without_file.replace(case_number, "")
    body = body.strip(" ()-—:：")
    return len(body) >= 8


def reference_answer(chunk_text: str, filename: str, case_number: str) -> str:
    """Cite only words that already appear in the chunk. Do not add a holding."""
    index = chunk_text.find(case_number)
    start = index if index >= 0 else 0
    snippet = " ".join(chunk_text[start : start + 180].split())
    for opening in _FORBIDDEN_OPENINGS:
        if snippet.startswith(opening):
            snippet = snippet[len(opening) :].lstrip(" :，,")
    if not snippet:
        snippet = case_number
    return f"{snippet} ({filename})"


def test_quality_rejects_missing_source_wrong_case_and_forbidden_opening():
    filename = "01012-610054-4f-example.pdf"
    case_number = "01012-610054"
    good = f"คดี {case_number} วินิจฉัยตามข้อความในสำนวน ({filename})"
    assert answer_meets_quality(
        good, case_number=case_number, filename=filename, has_source=True
    )
    assert not answer_meets_quality(
        good, case_number=case_number, filename=filename, has_source=False
    )
    assert not answer_meets_quality(
        f"คดี 01012-999999 คนละสำนวน ({filename})",
        case_number=case_number,
        filename=filename,
        has_source=True,
    )
    assert not answer_meets_quality(
        f"ตามที่ปรากฏในสำนวน {case_number} ({filename})",
        case_number=case_number,
        filename=filename,
        has_source=True,
    )
    assert not answer_meets_quality(
        f"จากการศึกษาสำนวน {case_number} ({filename})",
        case_number=case_number,
        filename=filename,
        has_source=True,
    )
    assert not answer_meets_quality(
        f"จากบริบทของสำนวน {case_number} ({filename})",
        case_number=case_number,
        filename=filename,
        has_source=True,
    )


def test_judgment_chunks_pack_context_and_reference_answers():
    failures: list[str] = []
    for path in _judgment_json_paths():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            failures.append(f"{path.name}: JSON ไม่ใช่วัตถุ")
            continue
        case_number = _case_number(path.name)
        texts = _chunk_texts(payload)
        joined = "\n".join(texts).strip()
        filename = _source_name(payload, path)
        if not joined:
            failures.append(f"{path.name}: chunk ว่าง")
            continue
        if case_number not in joined:
            failures.append(f"{path.name}: chunk ไม่มีเลขคดี {case_number}")
            continue
        chunk = SimpleNamespace(
            text=joined,
            source_document=filename,
            page_number=1,
            section_label=None,
            legal_reference=None,
            score=0.9,
        )
        messages = build_kb_qa_messages(question=case_number, chunks=[chunk], web_sources=[])
        context = messages[-1]["content"]
        if case_number not in context or filename not in context:
            failures.append(f"{path.name}: บริบทไม่มีเลขคดีหรือชื่อไฟล์")
            continue
        answer = reference_answer(joined, filename, case_number)
        normalized_chunk = " ".join(joined.split())
        cited = answer.replace(f"({filename})", "").strip()
        if cited not in normalized_chunk:
            failures.append(f"{path.name}: คำตอบอ้างอิงแต่งข้อความที่ไม่มีใน chunk")
            continue
        if not answer_meets_quality(
            answer, case_number=case_number, filename=filename, has_source=True
        ):
            failures.append(f"{path.name}: คำตอบอ้างอิงไม่ผ่านเกณฑ์คุณภาพ")
    if failures:
        pytest.fail("คุณภาพคำตอบคำพิพากษาไม่ผ่าน:\n" + "\n".join(failures))
