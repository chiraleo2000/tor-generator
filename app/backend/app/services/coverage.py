"""Coverage map and readiness helpers for the 27 TOR slots."""

from __future__ import annotations

from typing import Any

from app.domain.slots import FACT_REQUIRED_SLOTS, INTAKE_SLOT_LABELS, INTAKE_SLOT_ORDER


def _slot(slot_map: dict[str, Any], key: str) -> dict[str, Any]:
    raw = slot_map.get(key) if isinstance(slot_map, dict) else None
    return raw if isinstance(raw, dict) else {}


def _is_filled(slot: dict[str, Any]) -> bool:
    status = slot.get("status")
    content = str(slot.get("content") or "").strip()
    return status == "filled" and bool(content)


def compute_readiness_score(slot_map: dict[str, Any]) -> float:
    """Fraction of Fact_Required_Slots that are filled with non-empty content."""
    total = len(FACT_REQUIRED_SLOTS)
    if total == 0:
        return 0.0
    filled = sum(1 for key in FACT_REQUIRED_SLOTS if _is_filled(_slot(slot_map, key)))
    return filled / total


def compute_ready(slot_map: dict[str, Any]) -> bool:
    total = len(FACT_REQUIRED_SLOTS)
    if total == 0:
        return False
    filled = sum(1 for key in FACT_REQUIRED_SLOTS if _is_filled(_slot(slot_map, key)))
    return filled == total


def build_coverage_map(slot_map: dict[str, Any]) -> list[dict[str, Any]]:
    """All 27 slots with Thai label, status, and criticality."""
    rows: list[dict[str, Any]] = []
    for key in INTAKE_SLOT_ORDER:
        slot = _slot(slot_map, key)
        status = slot.get("status") or "gap"
        if status not in {"filled", "gap", "reference_only", "error"}:
            status = "gap"
        fact_required = key in FACT_REQUIRED_SLOTS
        critical = fact_required and status in {"gap", "reference_only", "error"}
        rows.append(
            {
                "key": key,
                "label": INTAKE_SLOT_LABELS.get(key, key),
                "status": status,
                "filled": status == "filled",
                "fact_required": fact_required,
                "criticality": "critical" if critical else "non-critical",
                "content": str(slot.get("content") or ""),
                "sources": slot.get("sources") if isinstance(slot.get("sources"), list) else [],
            }
        )
    return rows
