"""KB fan-out must copy full sections, not truncated stubs."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "skills" / "Draft-TORs-Skills" / "convert_kb_to_markdown.py"


def _load():
    spec = importlib.util.spec_from_file_location("convert_kb_to_markdown", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_convert_kb_keeps_long_sections_and_no_copy_stub():
    mod = _load()
    blob = "ก" * 2500
    markdown = mod.convert_to_markdown(
        {
            "sources": ["act.pdf"],
            "sections": [
                {"section_id": "ม.8", "content": blob},
                {"section_id": "ม.9", "content": "เนื้อหาเต็มของกฎ"},
            ],
        },
        "guarantee",
        "หลักประกัน",
    )
    assert "[...truncated...]" not in markdown
    assert blob in markdown
    assert "Copy full content" not in markdown


def test_skill_decision_rules_are_not_stubs():
    path = (
        ROOT
        / "skills"
        / "Draft-TORs-Skills"
        / "claude"
        / "tor-procurement"
        / "references"
        / "method_selection.json"
    )
    text = path.read_text(encoding="utf-8")
    assert "Copy full content" not in text
    assert "rules" in text
