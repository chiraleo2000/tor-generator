"""Convert between wizard step form objects and TOR section payloads."""

from __future__ import annotations

import json
from typing import Any

from app.domain.tor_sections import SCOPE_SUBSECTIONS, STEP_SECTION_MAP


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        lines: list[str] = []
        for item in value:
            if isinstance(item, dict):
                title = str(item.get("title") or item.get("item") or "").strip()
                details = str(
                    item.get("details")
                    or item.get("amount")
                    or item.get("deliverable")
                    or ""
                ).strip()
                if title and details:
                    lines.append(f"- {title}: {details}")
                elif title:
                    lines.append(f"- {title}")
                elif details:
                    lines.append(f"- {details}")
            else:
                text = str(item).strip()
                if text:
                    lines.append(f"- {text}")
        return "\n".join(lines)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def normalize_step_payload(step: int, data: dict[str, Any]) -> dict[str, Any]:
    """Map frontend step objects (or already-keyed data) to section_key → text.

    Always includes original keys so metadata (project_name, budget, …)
    remains available for project-row updates.
    """
    payload: dict[str, Any] = dict(data)
    section_keys = STEP_SECTION_MAP.get(step, [])

    if step == 1:
        duration = data.get("duration_days")
        location = data.get("location") or data.get("s7") or ""
        if duration:
            payload["s5"] = (
                f"ระยะเวลาดำเนินการ {duration} วัน นับจากวันลงนามในสัญญา"
            )
        elif data.get("s5"):
            payload["s5"] = _as_text(data.get("s5"))
        if location:
            payload["s7"] = _as_text(location)
    elif step == 2:
        payload["s1"] = _as_text(
            data.get("s1") or data.get("description") or data.get("problemDescription")
        )
    elif step == 3:
        payload["s2"] = _as_text(data.get("s2") or data.get("objectives"))
    elif step == 4:
        scope_items = data.get("scope_items") or data.get("scope") or []
        deliverables = data.get("deliverables") or []
        if isinstance(scope_items, list) and scope_items:
            payload["s4"] = _as_text(scope_items)
            for index, item in enumerate(scope_items[:14], start=1):
                sub_key = f"s4.{index}"
                if isinstance(item, dict):
                    title = str(item.get("title") or SCOPE_SUBSECTIONS.get(sub_key, "")).strip()
                    details = str(item.get("details") or "").strip()
                    payload[sub_key] = f"{title}\n{details}".strip() if details else title
                else:
                    payload[sub_key] = str(item)
        if deliverables:
            payload["s4.8"] = _as_text(deliverables)
            existing = payload.get("s4", "")
            payload["s4"] = (
                f"{existing}\n\nผลงานส่งมอบ:\n{_as_text(deliverables)}"
            ).strip()
        if data.get("s4") and "s4" not in payload:
            payload["s4"] = _as_text(data["s4"])
    elif step == 5:
        quals = data.get("qualifications") or data.get("s3")
        capital = data.get("paid_up_capital")
        text = _as_text(quals)
        if capital:
            text = (
                f"{text}\n\nทุนจดทะเบียนชำระแล้วไม่น้อยกว่า "
                f"{int(capital):,} บาท"
            ).strip()
        payload["s3"] = text
    elif step == 6:
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
            lines = []
            for i, item in enumerate(schedule, start=1):
                if isinstance(item, dict):
                    pct = item.get("percentage", "")
                    deliverable = item.get("deliverable", "")
                    lines.append(f"งวดที่ {i} ร้อยละ {pct} — {deliverable}")
                else:
                    lines.append(str(item))
            payload["s8"] = "\n".join(lines)
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
            payload["s5"] = (
                f"ระยะเวลาดำเนินการ {duration} วัน นับจากวันลงนามในสัญญา"
            )
        elif data.get("s5"):
            payload["s5"] = _as_text(data["s5"])
    elif step == 7:
        for key in section_keys:
            if key in data:
                payload[key] = _as_text(data[key])

    return payload


def sections_to_step_data(
    step: int,
    sections: list[dict[str, Any]],
    project: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Rebuild a frontend step object from persisted TOR sections + project."""
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

    project = project or {}

    if step == 1:
        duration = None
        s5 = by_key.get("s5", "")
        for token in s5.replace(",", "").split():
            if token.isdigit():
                duration = int(token)
                break
        return {
            "project_name": project.get("name") or "",
            "ministry": project.get("ministry") or "",
            "budget": project.get("budget"),
            "project_type": project.get("project_type") or "general",
            "template_id": project.get("template_id"),
            "location": by_key.get("s7") or "",
            "duration_days": duration,
        }
    if step == 2:
        return {"description": by_key.get("s1") or ""}
    if step == 3:
        raw = by_key.get("s2") or ""
        objectives = [line.lstrip("-• ").strip() for line in raw.splitlines() if line.strip()]
        return {"objectives": objectives or [""]}
    if step == 4:
        scope_items = []
        for i in range(1, 15):
            key = f"s4.{i}"
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
        deliverable_text = subs.get("s4.8") or ""
        deliverables = [
            line.lstrip("-• ").strip()
            for line in deliverable_text.splitlines()
            if line.strip()
        ]
        return {
            "scope_items": scope_items or [{"title": "", "details": ""}],
            "deliverables": deliverables or [""],
        }
    if step == 5:
        raw = by_key.get("s3") or ""
        quals = [line.lstrip("-• ").strip() for line in raw.splitlines() if line.strip()]
        capital = None
        digits = "".join(ch for ch in raw if ch.isdigit() or ch == ",")
        if digits:
            try:
                capital = int(digits.replace(",", ""))
            except ValueError:
                capital = None
        return {
            "qualifications": quals or [""],
            "paid_up_capital": capital,
        }
    if step == 6:
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
    if step == 7:
        return {key: by_key.get(key, "") for key in STEP_SECTION_MAP[7]}
    if step == 8:
        return {"exported": False}
    return by_key
