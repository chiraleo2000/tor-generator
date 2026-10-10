"""Convert between wizard step form objects and TOR section payloads."""

from __future__ import annotations

import json
from typing import Any

from app.domain.tor_sections import SCOPE_SUBSECTIONS, STEP_SECTION_MAP


def _bullet_line(item: Any) -> str | None:
    if not isinstance(item, dict):
        text = str(item).strip()
        return f"- {text}" if text else None
    title = str(item.get("title") or item.get("item") or "").strip()
    details = str(
        item.get("details") or item.get("amount") or item.get("deliverable") or ""
    ).strip()
    if title and details:
        return f"- {title}: {details}"
    if title:
        return f"- {title}"
    if details:
        return f"- {details}"
    return None


def _list_as_text(value: list[Any]) -> str:
    lines = [line for item in value if (line := _bullet_line(item))]
    return "\n".join(lines)


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return _list_as_text(value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _duration_sentence(duration: Any) -> str:
    return f"ระยะเวลาดำเนินการ {duration} วัน นับจากวันลงนามในสัญญา"


def _normalize_step_1(payload: dict[str, Any], data: dict[str, Any]) -> None:
    duration = data.get("duration_days")
    location = data.get("location") or data.get("s7") or ""
    if duration:
        payload["s5"] = _duration_sentence(duration)
    elif data.get("s5"):
        payload["s5"] = _as_text(data.get("s5"))
    if location:
        payload["s7"] = _as_text(location)


def _normalize_step_2(payload: dict[str, Any], data: dict[str, Any]) -> None:
    payload["s1"] = _as_text(
        data.get("s1") or data.get("description") or data.get("problemDescription")
    )


def _normalize_step_3(payload: dict[str, Any], data: dict[str, Any]) -> None:
    payload["s2"] = _as_text(data.get("s2") or data.get("objectives"))


def _scope_item_text(index: int, item: Any) -> str:
    sub_key = f"s4.{index}"
    if not isinstance(item, dict):
        return str(item)
    title = str(item.get("title") or SCOPE_SUBSECTIONS.get(sub_key, "")).strip()
    details = str(item.get("details") or "").strip()
    return f"{title}\n{details}".strip() if details else title


def _apply_scope_items(payload: dict[str, Any], data: dict[str, Any]) -> None:
    scope_items = data.get("scope_items") or data.get("scope") or []
    if not isinstance(scope_items, list) or not scope_items:
        return
    payload["s4"] = _as_text(scope_items)
    for index, item in enumerate(scope_items[:14], start=1):
        payload[f"s4.{index}"] = _scope_item_text(index, item)


def _apply_deliverables(payload: dict[str, Any], data: dict[str, Any]) -> None:
    deliverables = data.get("deliverables") or []
    if not deliverables:
        return
    payload["s4.8"] = _as_text(deliverables)
    existing = payload.get("s4", "")
    payload["s4"] = f"{existing}\n\nผลงานส่งมอบ:\n{_as_text(deliverables)}".strip()


def _normalize_step_4(payload: dict[str, Any], data: dict[str, Any]) -> None:
    _apply_scope_items(payload, data)
    _apply_deliverables(payload, data)
    if data.get("s4") and "s4" not in payload:
        payload["s4"] = _as_text(data["s4"])


def _normalize_step_5(payload: dict[str, Any], data: dict[str, Any]) -> None:
    quals = data.get("qualifications") or data.get("s3")
    capital = data.get("paid_up_capital")
    text = _as_text(quals)
    if capital:
        text = (
            f"{text}\n\nทุนจดทะเบียนชำระแล้วไม่น้อยกว่า {int(capital):,} บาท"
        ).strip()
    payload["s3"] = text


def _schedule_lines(schedule: list[Any]) -> str:
    lines: list[str] = []
    for index, item in enumerate(schedule, start=1):
        if isinstance(item, dict):
            pct = item.get("percentage", "")
            deliverable = item.get("deliverable", "")
            lines.append(f"งวดที่ {index} ร้อยละ {pct} — {deliverable}")
        else:
            lines.append(str(item))
    return "\n".join(lines)


def _normalize_step_6(payload: dict[str, Any], data: dict[str, Any]) -> None:
    breakdown = data.get("budget_breakdown") or []
    schedule = data.get("payment_schedule") or []
    penalty = data.get("penalty_rate")
    warranty = data.get("warranty") or data.get("s9") or ""
    duration = data.get("duration_days")
    if breakdown:
        payload["s6"] = "รายละเอียดงบประมาณ:\n" + _as_text(breakdown)
    elif data.get("s6"):
        payload["s6"] = _as_text(data["s6"])
    if schedule:
        payload["s8"] = _schedule_lines(schedule)
    elif data.get("s8"):
        payload["s8"] = _as_text(data["s8"])
    if warranty:
        payload["s9"] = _as_text(warranty)
    if penalty is not None and penalty != "":
        payload["s10"] = (
            f"อัตราค่าปรับร้อยละ {penalty} ต่อวัน ของราคาค่าจ้างตามสัญญา "
            f"แต่ไม่ต่ำกว่า 100 บาทต่อวัน"
        )
    elif data.get("s10"):
        payload["s10"] = _as_text(data["s10"])
    if duration:
        payload["s5"] = _duration_sentence(duration)
    elif data.get("s5"):
        payload["s5"] = _as_text(data["s5"])


def _normalize_step_7(payload: dict[str, Any], data: dict[str, Any], section_keys: list[str]) -> None:
    for key in section_keys:
        if key in data:
            payload[key] = _as_text(data[key])


def normalize_step_payload(step: int, data: dict[str, Any]) -> dict[str, Any]:
    """Map frontend step objects (or already-keyed data) to section_key → text.

    Always includes original keys so metadata (project_name, budget, …)
    remains available for project-row updates.
    """
    payload: dict[str, Any] = dict(data)
    section_keys = STEP_SECTION_MAP.get(step, [])
    if step == 1:
        _normalize_step_1(payload, data)
    elif step == 2:
        _normalize_step_2(payload, data)
    elif step == 3:
        _normalize_step_3(payload, data)
    elif step == 4:
        _normalize_step_4(payload, data)
    elif step == 5:
        _normalize_step_5(payload, data)
    elif step == 6:
        _normalize_step_6(payload, data)
    elif step == 7:
        _normalize_step_7(payload, data, section_keys)
    return payload


def _index_sections(sections: list[dict[str, Any]]) -> tuple[dict[str, str], dict[str, str]]:
    by_key: dict[str, str] = {}
    subs: dict[str, str] = {}
    for section in sections:
        key = section.get("section_key") or ""
        sub = section.get("sub_key")
        content = section.get("content") or ""
        if sub:
            subs[f"{key}.{sub}" if not str(sub).startswith("s") else str(sub)] = content
            if "." not in str(sub) and key:
                subs[f"{key}.{sub}"] = content
        elif key:
            by_key[key] = content
    return by_key, subs


def _first_duration(s5: str) -> int | None:
    for token in s5.replace(",", "").split():
        if token.isdigit():
            return int(token)
    return None


def _step_1_data(by_key: dict[str, str], project: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_name": project.get("name") or "",
        "ministry": project.get("ministry") or "",
        "budget": project.get("budget"),
        "project_type": project.get("project_type") or "general",
        "template_id": project.get("template_id"),
        "location": by_key.get("s7") or "",
        "duration_days": _first_duration(by_key.get("s5", "")),
    }


def _bullet_items(raw: str) -> list[str]:
    return [line.lstrip("-• ").strip() for line in raw.splitlines() if line.strip()]


def _step_4_data(by_key: dict[str, str], subs: dict[str, str]) -> dict[str, Any]:
    scope_items = []
    for index in range(1, 15):
        key = f"s4.{index}"
        text = subs.get(key) or by_key.get(key) or ""
        if not text:
            continue
        parts = text.split("\n", 1)
        scope_items.append(
            {
                "title": parts[0].strip(),
                "details": parts[1].strip() if len(parts) > 1 else "",
            }
        )
    if not scope_items and by_key.get("s4"):
        scope_items = [{"title": "ขอบเขตงาน", "details": by_key["s4"]}]
    deliverables = _bullet_items(subs.get("s4.8") or "")
    return {
        "scope_items": scope_items or [{"title": "", "details": ""}],
        "deliverables": deliverables or [""],
    }


def _paid_up_capital(raw: str) -> int | None:
    digits = "".join(ch for ch in raw if ch.isdigit() or ch == ",")
    if not digits:
        return None
    try:
        return int(digits.replace(",", ""))
    except ValueError:
        return None


def _step_5_data(by_key: dict[str, str]) -> dict[str, Any]:
    raw = by_key.get("s3") or ""
    return {
        "qualifications": _bullet_items(raw) or [""],
        "paid_up_capital": _paid_up_capital(raw),
    }


def _step_6_data(by_key: dict[str, str]) -> dict[str, Any]:
    return {
        "budget_breakdown": [{"item": by_key.get("s6") or "", "amount": 0}],
        "payment_schedule": [{"percentage": 0, "deliverable": by_key.get("s8") or ""}],
        "penalty_rate": None,
        "warranty": by_key.get("s9") or "",
        "duration_days": None,
        "s5": by_key.get("s5") or "",
        "s6": by_key.get("s6") or "",
        "s8": by_key.get("s8") or "",
        "s9": by_key.get("s9") or "",
        "s10": by_key.get("s10") or "",
    }


def sections_to_step_data(
    step: int,
    sections: list[dict[str, Any]],
    project: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Rebuild a frontend step object from persisted TOR sections + project."""
    by_key, subs = _index_sections(sections)
    project = project or {}
    if step == 1:
        return _step_1_data(by_key, project)
    if step == 2:
        return {"description": by_key.get("s1") or ""}
    if step == 3:
        objectives = _bullet_items(by_key.get("s2") or "")
        return {"objectives": objectives or [""]}
    if step == 4:
        return _step_4_data(by_key, subs)
    if step == 5:
        return _step_5_data(by_key)
    if step == 6:
        return _step_6_data(by_key)
    if step == 7:
        return {key: by_key.get(key, "") for key in STEP_SECTION_MAP[7]}
    if step == 8:
        return {"exported": False}
    return by_key
