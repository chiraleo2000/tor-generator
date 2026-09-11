"""Intake slot keys for Phase 0–1 chat mapping.

Keys come from Section_Profile of the project's Procurement_Category.
"""

from __future__ import annotations

from app.domain.section_profile import (
    CATEGORIES_WITHOUT_CURRENT_SYSTEM,
    category_for_project,
    is_scope_storage_key,
    profile_for_project,
    scope_storage_key,
)
from app.domain.tor_sections import (
    EXTRA_SECTION_ORDER,
    SCOPE_SUBSECTIONS,
    TOR_SECTION_LABELS,
    TOR_SECTION_ORDER,
)
from app.domain.tor_taxonomy import LEGACY_SCOPE_MAP

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

# Legacy s4.x → profile storage keys (functional, deliverable_docs, …).
_LEGACY_SCOPE_STORAGE: dict[str, str] = {
    legacy: scope_storage_key(semantic)
    for legacy, semantic in LEGACY_SCOPE_MAP.items()
    if semantic
}


def slot_label(key: str, category: str | None = None) -> str:
    if category:
        labels = profile_for_project(category).slot_labels()
        if key in labels:
            return labels[key]
    return INTAKE_SLOT_LABELS.get(key, key)


def is_scope_sub(key: str) -> bool:
    return is_scope_storage_key(key) or key in SCOPE_SUBSECTIONS


def slot_key_aliases(key: str) -> tuple[str, ...]:
    """Map legacy s4.x ↔ first-scope / semantic storage keys for fill checks."""
    aliases: list[str] = [key]
    if key == "s4.1" or key in FIRST_SCOPE_KEYS:
        aliases.extend(["s4.1", *sorted(FIRST_SCOPE_KEYS)])
    if key == "s4.2":
        aliases.extend(["s4.2", "s1"])
    storage = _LEGACY_SCOPE_STORAGE.get(key)
    if storage:
        aliases.append(storage)
    for legacy, mapped in _LEGACY_SCOPE_STORAGE.items():
        if key == mapped:
            aliases.append(legacy)
    return tuple(dict.fromkeys(aliases))


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
                *EXTRA_SECTION_ORDER,
                *SCOPE_SUBSECTIONS.keys(),
                *_LEGACY_SCOPE_STORAGE.keys(),
            ]
        )
    )


def extract_key_allowlist(category: str | None = None) -> frozenset[str]:
    """Keys the heuristic may write — all profiles + legacy s4.x codes."""
    keys: list[str] = list(empty_slot_keys(category))
    for cat in (
        "hire_develop",
        "hire_maintain",
        "lease_service",
        "buy_goods",
        "construction",
        "hire_consult",
        "hire_service",
    ):
        keys.extend(profile_for_project(cat).slot_order())
    keys.extend(_LEGACY_SCOPE_STORAGE.keys())
    keys.extend(_LEGACY_SCOPE_STORAGE.values())
    return frozenset(keys)


def _fill_if_blank(out: dict[str, str], key: str, body: str) -> bool:
    text = (body or "").strip()
    if not text or str(out.get(key) or "").strip():
        return False
    out[key] = text
    return True


def _apply_legacy_scope_remap(
    found: dict[str, str], out: dict[str, str], allowed_scope: set[str]
) -> None:
    for legacy, storage in _LEGACY_SCOPE_STORAGE.items():
        if storage not in allowed_scope:
            continue
        _fill_if_blank(out, storage, str(found.get(legacy) or ""))


def _apply_mother_s4(
    found: dict[str, str], out: dict[str, str], required: list[str], first_scope: str | None
) -> None:
    mother = str(found.get("s4") or "").strip()
    if not mother:
        return
    if first_scope and _fill_if_blank(out, first_scope, mother):
        return
    for key in required:
        if _fill_if_blank(out, key, mother):
            return


def _fold_as_is_into_background(
    found: dict[str, str], out: dict[str, str], category: str | None
) -> None:
    as_is = str(found.get("s4.2") or "").strip()
    if not as_is or category_for_project(category) not in CATEGORIES_WITHOUT_CURRENT_SYSTEM:
        return
    background = str(out.get("s1") or "").strip()
    if as_is in background:
        return
    out["s1"] = f"{background}\n{as_is}".strip() if background else as_is


def remap_extracted_slots(
    found: dict[str, str], category: str | None = None
) -> dict[str, str]:
    """Map legacy s4.x / s4 blobs onto the profile's semantic scope storage keys."""
    profile = profile_for_project(category)
    out = dict(found)
    required = profile.required_scope_keys()
    first_scope = required[0] if required else None
    _apply_legacy_scope_remap(found, out, set(profile.scope_storage_keys()))
    if first_scope:
        _fill_if_blank(out, first_scope, str(found.get("s4.1") or ""))
    _apply_mother_s4(found, out, required, first_scope)
    _fold_as_is_into_background(found, out, category)
    return out