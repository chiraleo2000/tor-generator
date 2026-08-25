"""Thai register / collation / chunking verification (task 19)."""

from app.orchestrator.agents.base import THAI_FORMAL_REGISTER_PREAMBLE
from app.rag.chunking import tokenize_thai


def test_pythainlp_newmm_splits_procurement_phrase():
    tokens = tokenize_thai("การจัดซื้อจัดจ้างภาครัฐ")
    assert len(tokens) > 1


def test_agent_preamble_requires_formal_thai():
    assert "ภาษาราชการ" in THAI_FORMAL_REGISTER_PREAMBLE


def test_alembic_mentions_thai_collation():
    from pathlib import Path

    migration = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20250101_000000_001_initial_schema.py"
    )
    text = migration.read_text(encoding="utf-8")
    assert "th_TH.UTF-8" in text or "ICU" in text
