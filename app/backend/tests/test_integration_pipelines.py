"""Pipeline tests that do not need live Docker services."""

from __future__ import annotations

import io

import pytest
from docx import Document

from app.domain.tor_sections import sample_complete_sections
from app.export.docx_generator import FONT_NAME, DOCXGenerator, TORContent
from app.orchestrator.agents.registry import AGENT_REGISTRY, REVIEW_AGENT
from app.orchestrator.graph import _create_rule_engine
from app.rag.chunking import chunk_text, tokenize_thai

pytestmark = pytest.mark.integration


def test_rag_thai_chunk_round_trip_fixture():
    text = "พระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560 ใช้บังคับกับหน่วยงานของรัฐ"
    tokens = tokenize_thai(text)
    assert len(tokens) > 3
    result = chunk_text(text=text, document_id="fixture-thai")
    assert result.chunks
    assert any("จัดซื้อ" in chunk.text or "พัสดุ" in chunk.text for chunk in result.chunks)


def test_orchestrator_registry_covers_legal_keys_without_llm():
    for key in [f"s{i}" for i in range(1, 14)]:
        assert key in AGENT_REGISTRY
    assert REVIEW_AGENT is not None


def test_export_docx_contains_thirteen_labels():
    sections = sample_complete_sections()
    docx_bytes = DOCXGenerator().generate(
        TORContent(
            project_name="โครงการทดสอบ",
            ministry="กระทรวงทดสอบ",
            budget=1_000_000,
            sections=sections,
        )
    )
    assert docx_bytes
    document = Document(io.BytesIO(docx_bytes))
    joined = "\n".join(p.text for p in document.paragraphs)
    assert "ความเป็นมา" in joined
    assert "เงื่อนไขอื่น" in joined
    assert FONT_NAME


def test_rule_engine_on_complete_sample():
    engine = _create_rule_engine()
    result = engine.validate(sample_complete_sections())
    assert 0 <= result.quality_score <= 100
