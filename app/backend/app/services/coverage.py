"""Coverage map and readiness helpers for Section_Profile intake slots."""

from __future__ import annotations

from typing import Any

from app.domain.slots import fact_required_slots, intake_slot_labels, intake_slot_order, slot_key_aliases


def _slot(slot_map: dict[str, Any], key: str) -> dict[str, Any]:
    raw = slot_map.get(key) if isinstance(slot_map, dict) else None
    return raw if isinstance(raw, dict) else {}


def _is_filled(slot_map: dict[str, Any], key: str) -> bool:
    for alias in slot_key_aliases(key):
        slot = _slot(slot_map, alias)
        status = slot.get("status")
        content = str(slot.get("content") or "").strip()
        if status == "filled" and bool(content):
            return True
    return False


def compute_readiness_score(slot_map: dict[str, Any], category: str | None = None) -> float:
    required = fact_required_slots(category)
    total = len(required)
    if total == 0:
        return 0.0
    filled = sum(1 for key in required if _is_filled(slot_map, key))
    return filled / total


def compute_ready(slot_map: dict[str, Any], category: str | None = None) -> bool:
    required = fact_required_slots(category)
    if not required:
        return False
    return all(_is_filled(slot_map, key) for key in required)


def _slot_with_content(slot_map: dict[str, Any], key: str) -> dict[str, Any]:
    slot = _slot(slot_map, key)
    if str(slot.get("content") or "").strip():
        return slot
    for alias in slot_key_aliases(key):
        alt = _slot(slot_map, alias)
        if str(alt.get("content") or "").strip():
            return alt
    return slot


def _coverage_status(slot: dict[str, Any]) -> str:
    status = slot.get("status") or "gap"
    if status not in {"filled", "gap", "reference_only", "error"}:
        return "gap"
    return status


def _coverage_row(
    slot_map: dict[str, Any],
    key: str,
    labels: dict[str, str],
    required: set[str] | list[str],
) -> dict[str, Any]:
    slot = _slot_with_content(slot_map, key)
    status = _coverage_status(slot)
    fact_required = key in required
    critical = fact_required and status in {"gap", "reference_only", "error"}
    return {
        "key": key,
        "label": labels.get(key, key),
        "status": status,
        "filled": status == "filled",
        "fact_required": fact_required,
        "criticality": "critical" if critical else "non-critical",
        "content": str(slot.get("content") or ""),
        "sources": slot.get("sources") if isinstance(slot.get("sources"), list) else [],
    }


def build_coverage_map(slot_map: dict[str, Any], category: str | None = None) -> list[dict[str, Any]]:
    labels = intake_slot_labels(category)
    required = fact_required_slots(category)
    return [
        _coverage_row(slot_map, key, labels, required)
        for key in intake_slot_order(category)
    ]
