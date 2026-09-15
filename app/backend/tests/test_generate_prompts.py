"""Canonical prompt generator is idempotent and fans out markers."""

from __future__ import annotations

import importlib.util
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
MODULE_PATH = BACKEND / "scripts" / "generate_prompts.py"


def _load():
    spec = importlib.util.spec_from_file_location("generate_prompts", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generate_prompts_idempotent_and_marks_targets():
    mod = _load()
    first = mod.main()
    assert first == 0
    generated = (BACKEND / "app" / "domain" / "generated_prompts.py").read_text(encoding="utf-8")
    second = mod.main()
    assert second == 0
    again = (BACKEND / "app" / "domain" / "generated_prompts.py").read_text(encoding="utf-8")
    assert generated == again
    assert "CORE_SYSTEM_PROMPT" in generated
    assert "ภาษาราชการ" in generated
    assert "Gemma" not in generated
    assert "enable_thinking" not in generated
    assert "131_072" not in generated
    compose = (
        BACKEND.parent
        / "infra"
        / "quick"
        / "agents-skills"
        / "skills"
        / "tor-draft-compose"
        / "SKILL.md"
    )
    text = compose.read_text(encoding="utf-8")
    assert mod.BEGIN in text
    assert "แหล่งความจริงเดียว" in text
    rules = (BACKEND.parents[1] / "documents" / "prompts" / "chatgpt_system_prompt.md").read_text(
        encoding="utf-8"
    )
    assert mod.BEGIN in rules
