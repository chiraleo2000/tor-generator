"""Heuristic risk rules: vague language, price/cost abnormality, missing ราคากลาง."""

from __future__ import annotations

from app.rule_engine.engine import KIND_LEGAL, KIND_RISK, Finding, Severity
from app.rule_engine.rules.base import BaseRule

_VAGUE = (
    "ตามความเหมาะสม",
    "คุณภาพดี",
    "หากจำเป็น",
    "ตามที่เห็นสมควร",
    "เป็นต้น",
    "ฯลฯ",
    "โดยประมาณ",
    "เท่าที่สามารถ",
)
_METHOD_MARKERS = (
    "e-bidding",
    "e-Bidding",
    "ประกาศเชิญชวน",
    "วิธีคัดเลือก",
    "วิธีเฉพาะเจาะจง",
    "เฉพาะเจาะจง",
)


def _is_ascii_digit(char: str) -> bool:
    return "0" <= char <= "9"


def _take_digits(text: str, start: int, max_count: int | None = None) -> tuple[str, int]:
    end = start
    limit = len(text) if max_count is None else min(len(text), start + max_count)
    while end < limit and _is_ascii_digit(text[end]):
        end += 1
    return text[start:end], end


def _consume_grouped_amount(text: str, start: int) -> tuple[int | None, int]:
    """ASCII thousands groups: 1–3 digits then one or more ,ddd."""
    first, idx = _take_digits(text, start, max_count=3)
    if not first:
        return None, start
    groups = 0
    digits = first
    while idx < len(text) and text[idx] == ",":
        part, nxt = _take_digits(text, idx + 1, max_count=3)
        if len(part) != 3:
            break
        if nxt < len(text) and _is_ascii_digit(text[nxt]):
            break
        digits += part
        idx = nxt
        groups += 1
    if groups == 0:
        return None, start
    return int(digits), idx


def _parse_amounts(text: str) -> list[int]:
    """ASCII amounts with thousands separators, or 5+ digit runs (not Thai digits)."""
    amounts: list[int] = []
    raw = text or ""
    i = 0
    while i < len(raw):
        if not _is_ascii_digit(raw[i]):
            i += 1
            continue
        grouped, next_i = _consume_grouped_amount(raw, i)
        if grouped is not None:
            amounts.append(grouped)
            i = next_i
            continue
        run, end = _take_digits(raw, i)
        if len(run) >= 5:
            amounts.append(int(run))
        i = end
    return amounts


def _parse_baht_percents(text: str) -> list[int]:
    """Integers after «ร้อยละ», ASCII digits only (1–3 places)."""
    percents: list[int] = []
    raw = text or ""
    marker = "ร้อยละ"
    start = 0
    while True:
        pos = raw.find(marker, start)
        if pos < 0:
            return percents
        idx = pos + len(marker)
        while idx < len(raw) and raw[idx].isspace():
            idx += 1
        digits, end = _take_digits(raw, idx, max_count=3)
        if digits:
            percents.append(int(digits))
            start = end
            continue
        start = pos + len(marker)


def _section_text(tor_document: dict, key: str) -> str:
    direct = tor_document.get(key)
    if isinstance(direct, str):
        return direct
    nested = tor_document.get("sections")
    if isinstance(nested, dict):
        value = nested.get(key)
        if isinstance(value, str):
            return value
    return ""


def _joined_text(tor_document: dict) -> str:
    parts: list[str] = []
    items = list(tor_document.items())
    nested = tor_document.get("sections")
    if isinstance(nested, dict):
        items.extend(nested.items())
    for key, value in items:
        if isinstance(value, str) and not str(key).startswith("_"):
            parts.append(value)
    return "\n".join(parts)


class VagueLanguageRule(BaseRule):
    """Flag unspecified quality/quantity wording without measurable criteria."""

    def validate(self, tor_document: dict) -> list[Finding]:
        findings: list[Finding] = []
        for key in ("s2", "s4", "s4.1", "s6", "s8", "s10", "s11"):
            content = _section_text(tor_document, key)
            if len(content) < 20:
                continue
            for phrase in _VAGUE:
                if phrase not in content:
                    continue
                findings.append(
                    Finding(
                        severity=Severity.WARNING,
                        rule_violated="RISK_VAGUE_LANGUAGE",
                        affected_section=key if key.startswith("s") else "s4",
                        message=(
                            f"พบถ้อยคำคลุมเครือ «{phrase}» โดยไม่มีตัวเลขหรือเกณฑ์วัดผลชัดเจน"
                        ),
                        recommended_correction=(
                            "ระบุปริมาณ ระยะเวลา SLA หรือเกณฑ์ตรวจรับที่เป็นตัวเลขแทนถ้อยคำกว้าง"
                        ),
                        finding_kind=KIND_RISK,
                        excerpt=phrase,
                        risk_type="vague",
                    )
                )
                break
        return findings


class AnnouncedPriceRule(BaseRule):
    """Require ราคากลาง beside budget and flag large unexplained gaps."""

    def validate(self, tor_document: dict) -> list[Finding]:
        findings: list[Finding] = []
        budget_text = _section_text(tor_document, "s6")
        if not budget_text.strip():
            return findings
        if "ราคากลาง" not in budget_text:
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    rule_violated="LEGAL_ANNOUNCED_PRICE_MISSING",
                    affected_section="s6",
                    message="ไม่พบการระบุราคากลางแยกจากวงเงินงบประมาณ",
                    recommended_correction=(
                        "ระบุราคากลาง วิธีคำนวณ (สืบราคา/ราคาที่เคยจ้าง/หลักเกณฑ์) "
                        "และเปรียบเทียบกับวงเงินที่ได้รับจัดสรร"
                    ),
                    finding_kind=KIND_LEGAL,
                    legal_basis="หลักเกณฑ์ราคากลางและระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างฯ",
                    excerpt=budget_text[:180],
                )
            )
            return findings
        amounts = _parse_amounts(budget_text)
        unique = sorted(set(amounts))
        if len(unique) >= 2:
            low, high = unique[0], unique[-1]
            if low > 0 and (high - low) / high >= 0.2:
                findings.append(
                    Finding(
                        severity=Severity.WARNING,
                        rule_violated="RISK_PRICE_GAP",
                        affected_section="s6",
                        message=(
                            "วงเงินกับราคากลางต่างกันเกินร้อยละ 20 โดยยังไม่มีคำอธิบายในหมดงบประมาณ"
                        ),
                        recommended_correction="อธิบายส่วนต่างระหว่างราคากลางกับงบประมาณที่ขอตั้ง",
                        finding_kind=KIND_RISK,
                        excerpt=budget_text[:180],
                        risk_type="price",
                    )
                )
        return findings


class CostAbnormalityRule(BaseRule):
    """Flag cost/effort mismatch and payment totals that do not add to 100%."""

    def validate(self, tor_document: dict) -> list[Finding]:
        findings: list[Finding] = []
        scope = _section_text(tor_document, "s4") + _section_text(tor_document, "s4.10")
        budget_text = _section_text(tor_document, "s6")
        payment = _section_text(tor_document, "s8")
        has_effort = "man-day" in scope.lower() or "man-month" in scope.lower() or "คนวัน" in scope
        amounts = _parse_amounts(budget_text)
        if has_effort and amounts and max(amounts) < 500_000:
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    rule_violated="RISK_COST_EFFORT_MISMATCH",
                    affected_section="s6",
                    message="ระบุปริมาณงาน (man-day/man-month) แต่วงเงินต่ำผิดปกติเมื่อเทียบกับภาระงาน",
                    recommended_correction="ทบทวนประมาณการต้นทุนให้สอดคล้องปริมาณงานในขอบเขต",
                    finding_kind=KIND_RISK,
                    risk_type="cost",
                    excerpt=budget_text[:180],
                )
            )
        percents = _parse_baht_percents(payment)
        if percents and abs(sum(percents) - 100) > 1:
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    rule_violated="RISK_PAYMENT_SUM",
                    affected_section="s8",
                    message=f"สัดส่วนงวดจ่ายรวม {sum(percents)} ไม่เท่ากับ 100",
                    recommended_correction="ปรับร้อยละแต่ละงวดให้รวม 100",
                    finding_kind=KIND_RISK,
                    risk_type="cost",
                    excerpt=payment[:180],
                )
            )
        return findings


class ProcurementMethodRule(BaseRule):
    """High-budget TOR should state the procurement method."""

    def validate(self, tor_document: dict) -> list[Finding]:
        budget = tor_document.get("budget")
        text = _joined_text(tor_document)
        if not isinstance(budget, (int, float)) or budget < 500_000:
            amounts = _parse_amounts(_section_text(tor_document, "s6"))
            budget = max(amounts) if amounts else 0
        if not budget or budget < 500_000:
            return []
        if any(marker in text for marker in _METHOD_MARKERS):
            return []
        return [
            Finding(
                severity=Severity.WARNING,
                rule_violated="LEGAL_PROCUREMENT_METHOD_MISSING",
                affected_section="s6",
                message="ไม่พบวิธีจัดซื้อจัดจ้าง (ประกาศเชิญชวน/คัดเลือก/เฉพาะเจาะจง) ทั้งที่วงเงินไม่ต่ำ",
                recommended_correction="ระบุวิธีจัดซื้อจัดจ้างให้สอดคล้องวงเงินตาม พ.ร.บ. และกฎกระทรวง",
                finding_kind=KIND_LEGAL,
                legal_basis="พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560 ว่าด้วยวิธีการจัดซื้อจัดจ้าง",
            )
        ]
