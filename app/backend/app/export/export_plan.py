"""Build a numbered RenderPlan from TORContent (Req 3, 4, 6, 8)."""

from __future__ import annotations

from app.domain.section_profile import (
    SEMANTIC_TO_STORAGE,
    STORAGE_TO_SEMANTIC,
    category_for_project,
    export_main_plan,
    subsection_export_plan,
)
from app.domain.tor_taxonomy import resolve_legacy, to_thai_numeral
from app.export.render_plan import (
    ArchiveRecord,
    NumberingScheme,
    RenderAppendix,
    RenderPlan,
    RenderSection,
    RenderSubsection,
    coerce_numbering_scheme,
)


def _filled(text: object) -> bool:
    return bool(str(text or "").strip())


def _format_int(value: int, use_thai: bool) -> str:
    raw = str(value)
    return to_thai_numeral(raw) if use_thai else raw


def _heading_number(index: int, scheme: NumberingScheme, use_thai: bool) -> str:
    if scheme is not NumberingScheme.NUMBERED_CONSECUTIVE:
        return ""
    return _format_int(index, use_thai)


def _child_number(parent: str, index: int, scheme: NumberingScheme, use_thai: bool) -> str:
    if scheme is not NumberingScheme.NUMBERED_CONSECUTIVE or not parent:
        return ""
    return f"{parent}.{_format_int(index, use_thai)}"


def _filled_subs(raw: dict[str, str] | None) -> dict[str, str]:
    return {key: text for key, text in (raw or {}).items() if _filled(text)}


def _merge_text(existing: str, extra: str) -> str:
    if not extra:
        return existing
    if not existing:
        return extra
    return f"{existing.rstrip()}\n\n{extra}"


def _plan_with_legacy_extras(
    project_type: str,
    sections: dict[str, str],
) -> list[tuple[str, str]]:
    plan = list(export_main_plan(project_type))
    keys = {key for key, _title in plan}
    if "s13" not in keys and _filled(sections.get("s13")):
        insert_at = next((i for i, (key, _title) in enumerate(plan) if key == "s17"), len(plan))
        plan.insert(insert_at, ("s13", "เงื่อนไขอื่น ๆ และข้อสงวนสิทธิ์"))
    return plan


def _fold_storage_row(
    storage_key: str,
    text: str,
    project_type: str,
    plan_keys: set[str],
    merged_sections: dict[str, str],
    merged_subs: dict[str, dict[str, str]],
    archived: list[ArchiveRecord],
) -> None:
    if not _filled(text) or storage_key in plan_keys:
        return
    resolved = resolve_legacy(storage_key, None, project_type)
    if resolved is None:
        archived.append(ArchiveRecord(storage_key, None, str(text)))
        merged_sections.pop(storage_key, None)
        return
    parent, sub = resolved
    parent_storage = SEMANTIC_TO_STORAGE.get(parent, parent)
    if not sub:
        merged_sections[parent_storage] = _merge_text(
            merged_sections.get(parent_storage, ""), str(text)
        )
        if storage_key != parent_storage:
            merged_sections.pop(storage_key, None)
        return
    bucket = merged_subs.setdefault(parent_storage, {})
    short = sub.split(".")[-1] if sub.startswith("scope.") else sub
    bucket[short] = _merge_text(bucket.get(short, ""), str(text))
    merged_sections.pop(storage_key, None)


def _fold_sub_row(
    section_key: str,
    sub_key: str,
    text: str,
    project_type: str,
    merged_subs: dict[str, dict[str, str]],
    archived: list[ArchiveRecord],
) -> None:
    if not _filled(text):
        return
    if section_key == "s4" and not str(sub_key).startswith("s4."):
        return
    if resolve_legacy(section_key, sub_key, project_type) is not None:
        return
    archived.append(ArchiveRecord(section_key, sub_key, str(text)))
    merged_subs.get(section_key, {}).pop(sub_key, None)


def _fold_legacy_rows(
    project_type: str,
    sections: dict[str, str],
    sub_sections: dict[str, dict[str, str]],
) -> tuple[dict[str, str], dict[str, dict[str, str]], list[ArchiveRecord]]:
    """Map leftover storage keys onto semantic parents; archive None targets."""
    merged_sections = dict(sections)
    merged_subs = {key: dict(value) for key, value in sub_sections.items()}
    archived: list[ArchiveRecord] = []
    plan_keys = {key for key, _title in _plan_with_legacy_extras(project_type, sections)}

    for storage_key, text in tuple(sections.items()):
        _fold_storage_row(
            storage_key,
            text,
            project_type,
            plan_keys,
            merged_sections,
            merged_subs,
            archived,
        )
    for section_key, subs in tuple(sub_sections.items()):
        for sub_key, text in tuple(subs.items()):
            _fold_sub_row(
                section_key, sub_key, text, project_type, merged_subs, archived
            )
    return merged_sections, merged_subs, archived


def _build_subsections(
    section_key: str,
    project_type: str,
    sub_map: dict[str, str],
    parent_number: str,
    scheme: NumberingScheme,
    use_thai: bool,
) -> tuple[RenderSubsection, ...]:
    plan = subsection_export_plan(section_key, project_type, sub_map)
    rows: list[RenderSubsection] = []
    child_n = 0
    for _key, title, text in plan:
        if not _filled(text):
            continue
        child_n += 1
        rows.append(
            RenderSubsection(
                number=_child_number(parent_number, child_n, scheme, use_thai),
                label=title,
                content=str(text),
            )
        )
    return tuple(rows)


def build_render_plan(content) -> RenderPlan:
    """Number only displayed sections; archive unresolved legacy rows."""
    scheme = coerce_numbering_scheme(getattr(content, "numbering_scheme", NumberingScheme.NONE))
    use_thai = bool(getattr(content, "use_thai_numerals", True))
    project_type = category_for_project(getattr(content, "project_type", None))
    sections, sub_sections, archived = _fold_legacy_rows(
        project_type,
        dict(getattr(content, "sections", None) or {}),
        dict(getattr(content, "sub_sections", None) or {}),
    )
    body: list[RenderSection] = []
    index = 0
    for storage_key, title in _plan_with_legacy_extras(project_type, sections):
        text = sections.get(storage_key, "")
        sub_map = _filled_subs(sub_sections.get(storage_key))
        if not _filled(text) and not sub_map:
            continue
        index += 1
        number = _heading_number(index, scheme, use_thai)
        body.append(
            RenderSection(
                semantic_key=STORAGE_TO_SEMANTIC.get(storage_key, storage_key),
                storage_key=storage_key,
                number=number,
                label=title,
                content=str(text) if _filled(text) else "",
                subsections=_build_subsections(
                    storage_key, project_type, sub_map, number, scheme, use_thai
                ),
            )
        )

    appendices: list[RenderAppendix] = []
    for app_index, item in enumerate(getattr(content, "appendices", None) or [], start=1):
        title = str(getattr(item, "title", "") or "")
        body_text = str(getattr(item, "content", "") or "")
        if not _filled(title) and not _filled(body_text):
            continue
        label = f"ภาคผนวก {_format_int(app_index, use_thai)}"
        appendices.append(RenderAppendix(number=label, title=title, content=body_text))

    return RenderPlan(body=tuple(body), appendices=tuple(appendices), archived=tuple(archived))
