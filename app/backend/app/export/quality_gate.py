"""Export quality and human-review gates (Req 9)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.section_profile import SEMANTIC_TO_STORAGE, category_for_project
from app.domain.tor_taxonomy import (
    CRITICAL_SECTIONS_MIN_LENGTH,
    MANDATORY_HUMAN_REVIEW_SECTIONS,
)

BASELINE_MIN_LENGTH = dict(CRITICAL_SECTIONS_MIN_LENGTH)
BASELINE_HITL = frozenset(MANDATORY_HUMAN_REVIEW_SECTIONS)


class GateWeakenedError(ValueError):
    """Raised when standardization would weaken min-length or HITL sets."""


@dataclass
class GateResult:
    ok: bool
    errors: list[str] = field(default_factory=list)

    def raise_if_blocked(self) -> None:
        if self.ok:
            return
        raise ValueError("; ".join(self.errors))


def _char_count(content, semantic: str) -> int:
    storage = SEMANTIC_TO_STORAGE.get(semantic, semantic)
    text = str((getattr(content, "sections", None) or {}).get(storage) or "")
    if semantic == "scope":
        subs = (getattr(content, "sub_sections", None) or {}).get("s4") or {}
        text += "".join(str(value or "") for value in subs.values())
    return len(text.strip())


def check_export_gates(content, approvals: dict[str, bool] | None = None) -> GateResult:
    """Block export when critical sections are short or HITL is unsigned."""
    approvals = approvals or {}
    errors: list[str] = []
    category = category_for_project(getattr(content, "project_type", None))
    from app.domain.tor_taxonomy import section_order

    present = set(section_order(category))
    for semantic, minimum in CRITICAL_SECTIONS_MIN_LENGTH.items():
        if semantic not in present:
            continue
        count = _char_count(content, semantic)
        if count < minimum:
            errors.append(
                f"หมวด {semantic} มี {count} อักขระ ต่ำกว่าเกณฑ์ขั้นต่ำ {minimum}"
            )
    for semantic in MANDATORY_HUMAN_REVIEW_SECTIONS:
        if semantic not in present:
            continue
        storage = SEMANTIC_TO_STORAGE.get(semantic, semantic)
        approved = bool(approvals.get(semantic) or approvals.get(storage))
        if not approved:
            errors.append(f"หมวด {semantic} ยังรอการอนุมัติจากผู้ตรวจ")
    return GateResult(ok=not errors, errors=errors)


def assert_gates_not_weakened(
    before_min: dict[str, int] | None = None,
    after_min: dict[str, int] | None = None,
    before_hitl: set[str] | frozenset[str] | None = None,
    after_hitl: set[str] | frozenset[str] | None = None,
) -> None:
    """Reject standardization that drops members or lowers thresholds (Req 9.5)."""
    before_min = before_min or BASELINE_MIN_LENGTH
    after_min = after_min or dict(CRITICAL_SECTIONS_MIN_LENGTH)
    before_hitl = set(before_hitl or BASELINE_HITL)
    after_hitl = set(after_hitl or MANDATORY_HUMAN_REVIEW_SECTIONS)
    dropped_min = sorted(set(before_min) - set(after_min))
    if dropped_min:
        raise GateWeakenedError(f"min-length members removed: {dropped_min}")
    lowered = [
        key for key, value in before_min.items() if int(after_min.get(key, 0)) < int(value)
    ]
    if lowered:
        raise GateWeakenedError(f"min-length lowered for: {lowered}")
    dropped_hitl = sorted(before_hitl - after_hitl)
    if dropped_hitl:
        raise GateWeakenedError(f"HITL members removed: {dropped_hitl}")
