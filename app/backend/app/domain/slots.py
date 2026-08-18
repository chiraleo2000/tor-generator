"""Intake slot keys for Phase 0–1 chat mapping.

Canonical TOR keys (s1–s13) plus Scope subsections (s4.1–s4.14).
"""

from __future__ import annotations

from app.domain.tor_sections import SCOPE_SUBSECTIONS, TOR_SECTION_LABELS, TOR_SECTION_ORDER

INTAKE_SLOT_LABELS: dict[str, str] = {
    **TOR_SECTION_LABELS,
    **SCOPE_SUBSECTIONS,
}

INTAKE_SLOT_ORDER: list[str] = [
    *TOR_SECTION_ORDER,
    *SCOPE_SUBSECTIONS.keys(),
]

# Project facts that legal citations alone cannot fill.
FACT_REQUIRED_SLOTS: frozenset[str] = frozenset(
    {
        "s1",
        "s2",
        "s5",
        "s6",
        "s7",
        "s4.1",
    }
)


def slot_label(key: str) -> str:
    return INTAKE_SLOT_LABELS.get(key, key)


def is_scope_sub(key: str) -> bool:
    return key in SCOPE_SUBSECTIONS
