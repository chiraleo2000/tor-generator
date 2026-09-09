"""Intake slot keys for Phase 0–1 chat mapping.

Keys come from Section_Profile of the project's Procurement_Category.
"""

from __future__ import annotations

from app.domain.section_profile import (
    CATEGORIES_WITHOUT_CURRENT_SYSTEM,
    category_for_project,
    is_scope_storage_key,
    profile_for_project,
)
from app.domain.tor_sections import SCOPE_SUBSECTIONS, TOR_SECTION_LABELS, TOR_SECTION_ORDER

_DEFAULT = profile_for_project("buy_goods")

INTAKE_SLOT_LABELS: dict[str, str] = {
    **TOR_SECTION_LABELS,
    **SCOPE_SUBSECTIONS,
}

INTAKE_SLOT_ORDER: list[str] = list(_DEFAULT.slot_order())

FACT_REQUIRED_SLOTS: frozenset[str] = frozenset(_DEFAULT.fact_required_keys())

FIRST_SCOPE_KEYS: frozenset[str] = frozenset(
    profile_for_project(key).required_scope_keys()[0]
    for key in (
        "hire_develop",
        "hire_maintain",
        "lease_service",
        "buy_goods",
        "construction",
        "hire_consult",
        "hire_service",
    )
    if profile_for_project(key).required_scope_keys()
)


def slot_label(key: str, category: str | None = None) -> str:
    if category:
        labels = profile_for_project(category).slot_labels()
        if key in labels:
            return labels[key]
    return INTAKE_SLOT_LABELS.get(key, key)


def is_scope_sub(key: str) -> bool:
    return is_scope_storage_key(key) or key in SCOPE_SUBSECTIONS


def slot_key_aliases(key: str) -> tuple[str, ...]:
    """Legacy s4.1 maps onto the first required scope subsection of any profile."""
    if key == "s4.1" or key in FIRST_SCOPE_KEYS:
        return ("s4.1", *sorted(FIRST_SCOPE_KEYS))
    if key == "s4.2":
        return ("s4.2", "s1")
    return (key,)


def fact_required_slots(category: str | None = None) -> frozenset[str]:
    return frozenset(profile_for_project(category).fact_required_keys())


def intake_slot_order(category: str | None = None) -> list[str]:
    return profile_for_project(category).slot_order()


def intake_slot_labels(category: str | None = None) -> dict[str, str]:
    labels = dict(INTAKE_SLOT_LABELS)
    labels.update(profile_for_project(category).slot_labels())
    return labels


def empty_slot_keys(category: str | None = None) -> list[str]:
    """Profile keys plus legacy catalog so marked (s4.1) packs still land in the map."""
    return list(
        dict.fromkeys(
            [
                *intake_slot_order(category),
                *TOR_SECTION_ORDER,
                *SCOPE_SUBSECTIONS.keys(),
            ]
        )
    )


def remap_extracted_slots(
    found: dict[str, str], category: str | None = None
) -> dict[str, str]:
    """Copy legacy s4.1/s4.2 onto the profile's first scope / background as needed."""
    profile = profile_for_project(category)
    out = dict(found)
    required = profile.required_scope_keys()
    first_scope = required[0] if required else None
    summary = str(found.get("s4.1") or "").strip()
    if first_scope and summary and not str(out.get(first_scope) or "").strip():
        out[first_scope] = summary
    as_is = str(found.get("s4.2") or "").strip()
    cat = category_for_project(category)
    if as_is and cat in CATEGORIES_WITHOUT_CURRENT_SYSTEM:
        background = str(out.get("s1") or "").strip()
        if as_is not in background:
            out["s1"] = f"{background}\n{as_is}".strip() if background else as_is
    return out
