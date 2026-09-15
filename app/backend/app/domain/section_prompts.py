"""Canonical TOR system prompt consumed by compose and drafting agents."""

from __future__ import annotations

from app.domain.generated_prompts import (
    CANONICAL_RULES,
    CORE_SYSTEM_PROMPT,
    SECTION_SNIPPETS,
)


def core_system_prompt() -> str:
    return CORE_SYSTEM_PROMPT


def canonical_rules() -> dict:
    return dict(CANONICAL_RULES)


def section_prompt(category: str | None, semantic_or_key: str) -> str:
    key = (semantic_or_key or "").strip()
    cat = (category or "").strip()
    shared = str(SECTION_SNIPPETS.get("_shared") or "")
    if cat and key:
        found = SECTION_SNIPPETS.get(f"{cat}/{key}")
        if found:
            return f"{shared}\n{found}".strip()
    found = SECTION_SNIPPETS.get(key)
    if found:
        return f"{shared}\n{found}".strip()
    return shared
