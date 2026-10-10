"""Bidder risk report layered on top of the three-part TOR score.

Rows are emitted only when the TOR text supports them. Money is calculated from
a budget and a daily rate read from the document. Page numbers come from page
records or markers already in the text. Nothing here changes the 40/30/30 score.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

PAGE_NOT_FOUND = "ไม่พบเลขหน้า"
DISCLAIMER = (
    "เป็นความเห็นเชิงบริหารโครงการจากข้อความ TOR "
    "ยังไม่ได้ตรวจหลักฐานคุณสมบัติ ต้นทุน หรือกำลังคนของบริษัท"
)

LEVEL_CRITICAL = "สูงมาก"
LEVEL_HIGH = "สูง"
LEVEL_MEDIUM_HIGH = "กลาง–สูง"
LEVEL_MEDIUM = "กลาง"

SIGNAL_MIGRATION = "data_migration"
SIGNAL_AI = "ai_acceptance"
SIGNAL_PQC = "pqc"
SIGNAL_INFRA = "infrastructure"
SIGNAL_LAST_PHASE = "last_phase_penalty"

DECISION_SIGNALS = {
    SIGNAL_MIGRATION,
    SIGNAL_AI,
    SIGNAL_PQC,
    SIGNAL_INFRA,
    SIGNAL_LAST_PHASE,
}

GATE_BY_SIGNAL = {
    SIGNAL_MIGRATION: "ย้ายข้อมูลได้จริง",
    SIGNAL_AI: "เกณฑ์ AI ชัด",
    SIGNAL_PQC: "Infrastructure และ PQC พิสูจน์ได้",
    SIGNAL_INFRA: "Infrastructure และ PQC พิสูจน์ได้",
    SIGNAL_LAST_PHASE: "ข้อค่าปรับได้คำชี้แจง",
}

CATEGORY_SPECS: tuple[tuple[str, str], ...] = (
    ("clarity", "ความชัดเจนและปริมาณงาน"),
    ("external", "ความร่วมมือกับหน่วยงานภายนอก"),
    ("schedule", "ระยะเวลา × งานที่ต้องส่งมอบ"),
    ("infrastructure", "รายการอุปกรณ์ / Infrastructure × กำหนดส่งงาน และการผูกกับเทคโนโลยี"),
    ("penalty", "ความเสี่ยงค่าปรับพร้อมจำนวนเงิน"),
    ("security", "ความปลอดภัย / กรรมสิทธิ์ / ต้นทุนอื่น"),
)

_PAGE_TOLERANCE = 5
_PER_DAY_WORD = "ต่อวัน"
_PENALTY_WORD = "ค่าปรับ"
_ASCII = re.ASCII
_PRINTED_LINE = re.compile(r"^(?:[-–—]\s*)?(\d{1,4})(?:\s*[-–—])?$", _ASCII)
_MARKER_FIND = re.compile(
    r"\[\[page\b([^\]]*)\]\]"
    r"|\[\[หน้า:\s*(\d{1,4})\s*\]\]"
    r"|<!--\s*page\b([^>]*)-->"
    r"|^---\s*(?:page|หน้า)\s+(\d{1,4})\s*---$"
    r"|^\[PAGE\s+(\d{1,4})\]$",
    re.IGNORECASE | re.MULTILINE | _ASCII,
)
_MARKER_STRIP = (
    re.compile(r"\[\[page\b[^\]]*\]\]", re.IGNORECASE),
    re.compile(r"\[\[หน้า:[^\]]+\]\]"),
    re.compile(r"<!--\s*page\b[^>]*-->", re.IGNORECASE),
    re.compile(r"^---\s*(?:page|หน้า)\s+\d{1,4}\s*---\s*$", re.IGNORECASE | re.MULTILINE | _ASCII),
    re.compile(r"^\[PAGE\s+\d{1,4}\]\s*$", re.IGNORECASE | re.MULTILINE | _ASCII),
)
_FILE_ATTR = re.compile(r"file\s*=\s*(\d{1,4})", re.IGNORECASE | _ASCII)
_PRINTED_ATTR = re.compile(r"printed\s*=\s*(\d{1,4})", re.IGNORECASE | _ASCII)
_BARE_NUMBER = re.compile(r"(\d{1,4})", _ASCII)
_LABELED_BUDGET = re.compile(
    r"(?:วงเงิน(?:งบประมาณ)?|งบประมาณ|มูลค่าสัญญา(?:ทั้งหมด)?|ค่าจ้างทั้งสัญญา)"
    r"[^\n]{0,40}?(\d{1,3}(?:,\d{3})+|\d{5,12})",
    _ASCII,
)
_DAILY_RATE = re.compile(r"ร้อยละ\s*(\d+(?:\.\d+)?)", _ASCII)
_WHOLE_BASE = (
    "มูลค่าสัญญาทั้งหมด",
    "มูลค่าทั้งสัญญา",
    "วงเงินตามสัญญา",
    "วงเงินทั้งสัญญา",
    "ค่าจ้างทั้งสัญญา",
    "ของสัญญาทั้งหมด",
    "ราคาทั้งสัญญา",
)
_PHASE_BASE = ("ค่างวด", "เฉพาะงวด", "มูลค่างวด", "ค่างานงวด", "เป็นรายงวด", "รายงวด")
_MIGRATION = re.compile(r"ย้ายข้อมูล|โอนย้ายข้อมูล|โอนข้อมูลจากระบบ|data\s*migration", re.IGNORECASE)
_VAGUE = "ตามที่ผู้ว่าจ้างกำหนด"
_QUANTITY = re.compile(
    r"\d[\d,]*(?:\.\d+)?\s*(?:GB|TB|กิกะไบต์|เทระไบต์|รายการ|ระเบียน|หน้า)",
    re.IGNORECASE | _ASCII,
)
_VOLUME_HIT = re.compile(
    r"\d[\d,]*(?:\.\d+)?\s*(?:GB|TB|กิกะไบต์|เทระไบต์)"
    r"|(?:หน้า\s*OCR|OCR)"
    r"|(?:ผู้ใช้พร้อมกัน|concurrent)",
    re.IGNORECASE | _ASCII,
)
_AI_METRIC = re.compile(r"\b(?:TSR|CER|WER)\b")
_TEST_SET = re.compile(r"ชุดทดสอบ|ชุดข้อมูลทดสอบ|test\s*set", re.IGNORECASE)
_FORCED_FN = re.compile(r"ฟังก์ชัน(?:ของ)?ระบบเดิม|ตามระบบเดิมทุกประการ|ต้องทำงานได้เหมือนระบบเดิม")
_PHASE_PERCENT = re.compile(
    r"งวดที่\s*\d+[^\n]{0,50}?ร้อยละ\s*(\d+(?:\.\d+)?)",
    _ASCII,
)
_START_ANCHORS = (
    ("นับจากวันลงนาม", r"นับ(?:จาก|แต่)วัน(?:ที่)?ลงนาม"),
    ("นับจากวันส่งมอบพื้นที่", r"นับจากวัน(?:ที่)?ส่งมอบ(?:พื้นที่|สถานที่)"),
    ("นับจากวันที่ผู้ว่าจ้างแจ้ง", r"นับ(?:จาก|แต่)วัน(?:ที่)?(?:ผู้ว่าจ้างแจ้ง|ได้รับแจ้ง|รับหนังสือ)"),
)
_INFRA = re.compile(r"\bVM\b|\bGPU\b|เครื่องแม่ข่าย|สตอเรจ|\bstorage\b", re.IGNORECASE)
_INFRA_NOT_READY = ("ยังไม่พร้อม", "จะจัดให้ภายหลัง", "ยังไม่ได้จัด")
_PQC = re.compile(
    r"\bPQC\b|post[-\s]?quantum|เข้ารหัสหลังควอนตัม|เข้ารหัสเชิงควอนตัม|ML-KEM|Kyber|Dilithium",
    re.IGNORECASE,
)


def _grouped_or_plain_amount(token: str) -> bool:
    if "," not in token:
        return token.isascii() and token.isdigit() and len(token) <= 24
    parts = token.split(",")
    head, *groups = parts
    if not head.isascii() or not head.isdigit() or not 1 <= len(head) <= 3 or not groups:
        return False
    return all(len(group) == 3 and group.isascii() and group.isdigit() for group in groups)


def _hourly_baht_amount(text: str) -> str | None:
    for match in _HOURLY_BAHT.finditer(text):
        token = match.group(1)
        if _grouped_or_plain_amount(token):
            return token
    return None


_HOURLY_BAHT = re.compile(r"(\d[\d,]{0,23})\s*บาทต่อชั่วโมง", _ASCII)
_HOURLY_PERCENT = re.compile(r"ร้อยละ\s*(\d+(?:\.\d+)?)\s*ต่อชั่วโมง", _ASCII)
_PHASE_PENALTY = re.compile(r"งวดใด[^\n]{0,40}(?:ไม่ครบ|ไม่แล้วเสร็จ)|ปรับเป็นรายงวด|ค่าปรับรายงวด")
_OVERLAP_EXPLAINED = re.compile(r"งวดซ้อน|ทับซ้อน|คิดซ้ำ|ไม่ซ้ำซ้อน|ซ้อนกัน")
_NO_AMOUNT = "ไม่แสดงจำนวนเงินเพราะไม่มีวงเงินหรืออัตราในเอกสาร"


@dataclass
class RiskRow:
    """One supported bidder-risk row."""

    issue: str
    requirement: str
    quote: str
    page_ref: str
    impact: str
    level: str
    mitigation: str
    signal: str = ""


@dataclass
class RiskCategory:
    """One of the six bidder-risk tables."""

    key: str
    label: str
    rows: list[RiskRow] = field(default_factory=list)


@dataclass
class PenaltyBox:
    """Daily penalty examples. Amounts stay empty when budget or rate is missing."""

    budget: int | None = None
    percent_per_day: float | None = None
    baht_per_day: int | None = None
    amount_30_days: int | None = None
    amount_60_days: int | None = None
    base: str = "unspecified"
    base_label: str = "ข้อความไม่ได้ระบุฐานค่าปรับ"
    hourly_note: str = ""
    phase_penalty_note: str = ""
    overlap_note: str = ""
    amount_note: str = ""


@dataclass
class BidderRiskReport:
    """Structured report. Markdown is derived from the same rows."""

    recommendation: str
    recommendation_kind: str
    disclaimer: str
    gates: list[str]
    penalty: PenaltyBox
    categories: list[RiskCategory]
    markdown: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def strip_page_markers(text: str) -> str:
    """Remove page markers so section classification and the scorer ignore them."""
    cleaned = (text or "").replace("\f", "\n")
    for pattern in _MARKER_STRIP:
        cleaned = pattern.sub("", cleaned)
    return cleaned


def printed_is_close(printed: int, file_index: int) -> bool:
    """True when a footer number is near the file page index."""
    if printed < 1 or printed > 2000:
        return False
    display = file_index if file_index >= 1 else file_index + 1
    anchors = {file_index, display}
    return any(abs(printed - anchor) <= _PAGE_TOLERANCE for anchor in anchors)


def file_page_label(file_index: int) -> str:
    shown = file_index if file_index >= 1 else file_index + 1
    return f"หน้าตามไฟล์ที่ {shown}"


def read_printed_page(page_text: str, file_index: int) -> int | None:
    """Read a clear footer such as ``16`` or ``- 16 -`` when it is close to the file index."""
    lines = [line.strip() for line in (page_text or "").splitlines() if line.strip()]
    for line in reversed(lines[-8:]):
        match = _PRINTED_LINE.fullmatch(line)
        if not match:
            continue
        number = int(match.group(1))
        if printed_is_close(number, file_index):
            return number
    return None


def _coerce_printed(value: object, file_index: int) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int) and printed_is_close(value, file_index):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        number = int(value.strip())
        if printed_is_close(number, file_index):
            return number
    return None


def normalize_pages(pages: list[Any] | None) -> list[dict[str, Any]]:
    """Prefer extraction page records. Printed numbers are kept only when they are clear."""
    normalized: list[dict[str, Any]] = []
    for position, page in enumerate(pages or []):
        if isinstance(page, dict):
            raw_index = page.get("index", position + 1)
            body = str(page.get("text") or "")
            given = page.get("printed")
        else:
            raw_index = getattr(page, "index", position + 1)
            body = str(getattr(page, "text", "") or "")
            given = getattr(page, "printed", None)
        try:
            file_index = int(raw_index)
        except (TypeError, ValueError):
            file_index = position + 1
        printed = _coerce_printed(given, file_index)
        if printed is None:
            printed = read_printed_page(body, file_index)
        normalized.append({"index": file_index, "printed": printed, "text": body})
    return normalized


def format_page_marker(file_index: int, printed: int | None) -> str:
    if printed is None:
        return f"[[page file={file_index}]]"
    return f"[[page file={file_index} printed={printed}]]"


def text_with_page_markers(text: str, pages: list[Any] | None = None) -> str:
    """Join page records with markers. Existing marked text is left unchanged."""
    normalized = normalize_pages(pages)
    if not any(page["text"].strip() for page in normalized):
        return text or ""
    blocks = [
        f"{format_page_marker(page['index'], page['printed'])}\n{page['text']}"
        for page in normalized
    ]
    return "\n".join(blocks)


def _parse_marker(match: re.Match[str]) -> dict[str, int | None]:
    attr_blob = match.group(1) or match.group(3) or ""
    bare = match.group(2) or match.group(4) or match.group(5)
    file_index: int | None = None
    printed: int | None = None
    file_match = _FILE_ATTR.search(attr_blob)
    if file_match:
        file_index = int(file_match.group(1))
    printed_match = _PRINTED_ATTR.search(attr_blob)
    if printed_match:
        printed = int(printed_match.group(1))
    elif bare:
        printed = int(bare)
    elif attr_blob and file_index is None:
        number = _BARE_NUMBER.search(attr_blob)
        if number:
            printed = int(number.group(1))
    return {"file": file_index, "printed": printed}


def _ref_from_marker(info: dict[str, int | None]) -> str:
    printed = info.get("printed")
    file_index = info.get("file")
    if isinstance(printed, int):
        if file_index is None or printed_is_close(printed, file_index):
            return f"หน้า {printed}"
    if isinstance(file_index, int):
        return file_page_label(file_index)
    return PAGE_NOT_FOUND


def _ref_from_pages(needle: str, pages: list[dict[str, Any]]) -> str | None:
    if not needle:
        return None
    for page in pages:
        if needle not in str(page.get("text") or ""):
            continue
        printed = page.get("printed")
        if isinstance(printed, int):
            return f"หน้า {printed}"
        return file_page_label(int(page["index"]))
    return None


def _ref_from_marked_text(text: str, needle: str) -> str:
    if not needle or needle not in text:
        return PAGE_NOT_FOUND
    if "\f" in text and not _MARKER_FIND.search(text):
        return _ref_from_form_feed(text, needle)
    index = text.find(needle)
    current: dict[str, int | None] | None = None
    for match in _MARKER_FIND.finditer(text):
        if match.start() <= index:
            current = _parse_marker(match)
            continue
        break
    if current is None:
        return PAGE_NOT_FOUND
    return _ref_from_marker(current)


def _ref_from_form_feed(text: str, needle: str) -> str:
    cursor = 0
    for position, chunk in enumerate(text.split("\f"), start=1):
        end = cursor + len(chunk)
        if cursor <= text.find(needle) <= end:
            printed = read_printed_page(chunk, position)
            if printed is not None:
                return f"หน้า {printed}"
            return file_page_label(position)
        cursor = end + 1
    return PAGE_NOT_FOUND


class _PageLocator:
    def __init__(self, text: str, pages: list[Any] | None) -> None:
        self.text = text or ""
        self.pages = normalize_pages(pages)

    def ref_for(self, needle: str) -> str:
        pages_have_text = any(str(page.get("text") or "").strip() for page in self.pages)
        if pages_have_text:
            found = _ref_from_pages(needle, self.pages)
            if found:
                return found
            return PAGE_NOT_FOUND
        return _ref_from_marked_text(self.text, needle)


def _short_quote(text: str, needle: str, limit: int = 140) -> str:
    index = text.find(needle)
    if index < 0:
        return ""
    start = max(0, index - 24)
    raw = text[start : index + len(needle) + 70]
    quote = " ".join(strip_page_markers(raw).split())
    return quote[:limit].strip()


def _requirement(quote: str, page_ref: str) -> str:
    return f"«{quote}» ({page_ref})"


def _add_row(
    rows: list[RiskRow],
    locator: _PageLocator,
    *,
    needle: str,
    issue: str,
    impact: str,
    level: str,
    mitigation: str,
    signal: str = "",
) -> None:
    if not needle or needle not in locator.text:
        return
    quote = _short_quote(locator.text, needle)
    if not quote:
        return
    page_ref = locator.ref_for(needle)
    rows.append(
        RiskRow(
            issue=issue,
            requirement=_requirement(quote, page_ref),
            quote=quote,
            page_ref=page_ref,
            impact=impact,
            level=level,
            mitigation=mitigation,
            signal=signal,
        )
    )


def _as_budget(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = int(value)
        return number if number > 0 else None
    if isinstance(value, str):
        digits = value.replace(",", "").strip()
        if digits.isdigit():
            number = int(digits)
            return number if number > 0 else None
    return None


def _budget_from_text(text: str) -> int | None:
    match = _LABELED_BUDGET.search(text or "")
    if not match:
        return None
    return _as_budget(match.group(1))


def _daily_rate(text: str) -> Decimal | None:
    """Percent per day. Payment shares such as ร้อยละ 30 of a phase are not a rate."""
    fallback: Decimal | None = None
    for match in _DAILY_RATE.finditer(text or ""):
        window = text[max(0, match.start() - 24) : match.end() + 12]
        if "ต่อชั่วโมง" in window and _PER_DAY_WORD not in window:
            continue
        if _PER_DAY_WORD not in window and _PENALTY_WORD not in window:
            continue
        rate = Decimal(match.group(1))
        if _PER_DAY_WORD in window:
            return rate
        if rate <= Decimal("0.20") and fallback is None:
            fallback = rate
    return fallback


def _penalty_base(text: str) -> tuple[str, str]:
    if any(phrase in text for phrase in _WHOLE_BASE):
        return "whole_contract", "มูลค่าสัญญาทั้งหมด"
    if any(phrase in text for phrase in _PHASE_BASE):
        return "phase", "เฉพาะงวดตามที่ข้อความระบุ"
    return "unspecified", "ข้อความไม่ได้ระบุฐานค่าปรับ"


def _baht(budget: int, percent: Decimal, days: int) -> int:
    amount = (Decimal(budget) * percent / Decimal(100)) * Decimal(days)
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _hourly_note(text: str, budget: int | None) -> str:
    amount = _hourly_baht_amount(text)
    if amount:
        return f"ค่าปรับ SLA ตามข้อความ {amount} บาทต่อชั่วโมง"
    percent_match = _HOURLY_PERCENT.search(text)
    if not percent_match:
        if "ต่อชั่วโมง" in text and _PENALTY_WORD in text:
            return "มีข้อความค่าปรับรายชั่วโมงแต่ไม่มีอัตราที่เป็นตัวเลข จึงไม่แสดงจำนวนเงิน"
        return ""
    if budget is None:
        return "มีอัตราค่าปรับต่อชั่วโมงแต่ไม่มีวงเงิน จึงไม่แสดงจำนวนเงิน"
    percent = Decimal(percent_match.group(1))
    per_hour = _baht(budget, percent, 1)
    return f"ค่าปรับ SLA ประมาณ {per_hour:,} บาทต่อชั่วโมง จากวงเงินในเอกสาร"


def _phase_penalty_note(text: str) -> str:
    match = _PHASE_PENALTY.search(text)
    if not match:
        return ""
    return f"TOR กำหนดค่าปรับรายงวดเมื่องวดส่งไม่ครบ: {' '.join(match.group(0).split())}"


def _overlap_note(text: str) -> str:
    if "งวด" not in text or _PENALTY_WORD not in text:
        return ""
    if _OVERLAP_EXPLAINED.search(text):
        found = _OVERLAP_EXPLAINED.search(text)
        phrase = found.group(0) if found else ""
        return f"ข้อความกล่าวถึงวิธีคิดงวดซ้อน ({phrase})"
    return "TOR ไม่ได้บอกวิธีคิดค่าปรับเมื่องวดซ้อนกัน"


def build_penalty_box(
    text: str,
    *,
    budget: int | None = None,
    penalty_rate_percent: float | None = None,
) -> PenaltyBox:
    """Baht per day = budget × (percent per day / 100). Examples are 30 and 60 days."""
    resolved_budget = budget if budget is not None else _budget_from_text(text)
    rate = _daily_rate(text)
    if rate is None and penalty_rate_percent is not None:
        rate = Decimal(str(penalty_rate_percent))
    base, base_label = _penalty_base(text)
    box = PenaltyBox(
        budget=resolved_budget,
        base=base,
        base_label=base_label,
        hourly_note=_hourly_note(text, resolved_budget),
        phase_penalty_note=_phase_penalty_note(text),
        overlap_note=_overlap_note(text),
    )
    if resolved_budget is None or rate is None:
        box.amount_note = _NO_AMOUNT
        return box
    box.percent_per_day = float(rate)
    box.baht_per_day = _baht(resolved_budget, rate, 1)
    box.amount_30_days = _baht(resolved_budget, rate, 30)
    box.amount_60_days = _baht(resolved_budget, rate, 60)
    box.amount_note = (
        f"{box.baht_per_day:,} บาท/วัน "
        f"ตัวอย่าง 30 วัน {box.amount_30_days:,} บาท "
        f"60 วัน {box.amount_60_days:,} บาท "
        f"ฐาน{base_label}"
    )
    return box


def _last_phase_tied(text: str, base: str) -> bool:
    if base != "whole_contract" or _PENALTY_WORD not in text:
        return False
    if not re.search(r"งวดสุดท้าย", text):
        return False
    return bool(re.search(r"ไม่ครบ|ไม่แล้วเสร็จ|ล่าช้า|ส่งไม่", text))



def _migration_level(text: str) -> str:
    vague = _VAGUE in text
    has_quantity = bool(_QUANTITY.search(text))
    if vague or not has_quantity:
        return LEVEL_CRITICAL
    return LEVEL_HIGH


def _has_ascii_digit(token: str) -> bool:
    return any(character.isascii() and character.isdigit() for character in token)


def _append_volume_row(rows: list[RiskRow], locator: _PageLocator, volume: re.Match[str]) -> None:
    level = LEVEL_MEDIUM_HIGH if _has_ascii_digit(volume.group(0)) else LEVEL_HIGH
    _add_row(
        rows,
        locator,
        needle=volume.group(0),
        issue="ปริมาณข้อมูลหรือผู้ใช้ถูกเขียนไว้ในขอบเขต",
        impact="ต้องตรวจว่าตัวเลขนี้ทำได้ด้วยทีม ระยะเวลา และเครื่องที่มี",
        level=level,
        mitigation="เทียบปริมาณกับวิธีทำงานและชุดทดสอบก่อนเสนอราคา",
    )


def _append_ai_row(
    rows: list[RiskRow],
    locator: _PageLocator,
    text: str,
    metric: re.Match[str],
) -> None:
    has_set = bool(_TEST_SET.search(text))
    if has_set:
        issue = "เกณฑ์ตรวจรับ AI อ้างชุดทดสอบที่ต้องตรวจว่าใช้ได้จริง"
        level = LEVEL_HIGH
    else:
        issue = "เกณฑ์ตรวจรับ AI ยังไม่มีชุดทดสอบที่ใช้วัด"
        level = LEVEL_CRITICAL
    _add_row(
        rows,
        locator,
        needle=metric.group(0),
        issue=issue,
        impact="ตรวจรับไม่ผ่านได้แม้ระบบทำงาน ถ้าชุดวัดยังไม่ชัดตอนยื่น",
        level=level,
        mitigation="ให้ผู้ว่าจ้างระบุชุดทดสอบ วิธีวัด และเกณฑ์ผ่านก่อนยื่น",
        signal=SIGNAL_AI,
    )


def _clarity_rows(locator: _PageLocator) -> list[RiskRow]:
    text = locator.text
    rows: list[RiskRow] = []
    migration = _MIGRATION.search(text)
    if migration:
        level = _migration_level(text)
        _add_row(
            rows,
            locator,
            needle=migration.group(0),
            issue="การย้ายข้อมูลยังพิสูจน์ปริมาณหรือความเป็นไปได้ไม่ได้",
            impact="ถ้าข้อมูลจริงย้ายไม่ได้ งานจะค้างและโดนค่าปรับทั้งที่งบถูกประเมินจากข้อความไม่ครบ",
            level=level,
            mitigation="ขอปริมาณ รูปแบบ และตัวอย่างข้อมูลก่อนยื่น และตัดถ้อยคำที่ให้ผู้ว่าจ้างกำหนดทีหลัง",
            signal=SIGNAL_MIGRATION,
        )
    forced = _FORCED_FN.search(text)
    if forced and not migration:
        _add_row(
            rows,
            locator,
            needle=forced.group(0),
            issue="บังคับฟังก์ชันของระบบเดิมโดยยังไม่มีรายการฟังก์ชัน",
            impact="ขอบเขตขยายได้หลังเซ็นสัญญา เพราะยึดระบบเดิมที่ผู้ยื่นยังไม่เห็น",
            level=LEVEL_HIGH,
            mitigation="ขอรายการฟังก์ชันที่ใช้จริงและตัวอย่างหน้าจอก่อนยื่น",
            signal=SIGNAL_MIGRATION,
        )
    migration_is_critical = any(
        row.signal == SIGNAL_MIGRATION and row.level == LEVEL_CRITICAL for row in rows
    )
    if _VAGUE in text and not migration_is_critical:
        _add_row(
            rows,
            locator,
            needle=_VAGUE,
            issue="ขอบเขตอ้างว่าให้เป็นไปตามที่ผู้ว่าจ้างกำหนด",
            impact="ปริมาณงานเปลี่ยนได้หลังยื่นราคา โดยผู้ยื่นไม่มีฐานต่อรอง",
            level=LEVEL_HIGH,
            mitigation="เปลี่ยนเป็นตัวเลข รายการส่งมอบ หรือเอกสารแนบที่อ้างอิงได้",
        )
    volume = _VOLUME_HIT.search(text)
    if volume:
        _append_volume_row(rows, locator, volume)
    metric = _AI_METRIC.search(text)
    if metric:
        _append_ai_row(rows, locator, text, metric)
    return rows


def _external_rows(locator: _PageLocator) -> list[RiskRow]:
    text = locator.text
    rows: list[RiskRow] = []
    patterns = (
        (
            r"ผู้พัฒนาระบบเดิม|เจ้าของระบบเดิม|ผู้ให้บริการระบบเดิม",
            "งานขึ้นกับผู้พัฒนาระบบเดิม",
            "ถ้าเจ้าของระบบเดิมไม่เปิดข้อมูลหรืออินเทอร์เฟซ งานเริ่มไม่ได้",
            LEVEL_HIGH,
            "ถามเป็นลายลักษณ์อักษรว่าจะได้สิทธิ์เข้าถึงก่อนยื่น",
        ),
        (
            r"Microsoft\s*365|ไมโครซอฟท์\s*365",
            "งานผูกกับสิทธิ์ Microsoft 365",
            "ไม่มีสิทธิ์ผู้เช่าหรือ API แล้วเชื่อมต่อไม่ได้",
            LEVEL_HIGH,
            "ตรวจสิทธิ์ผู้เช่าและขอบเขต API ที่หน่วยงานมีอยู่จริง",
        ),
        (
            r"สิทธิ์[^\n]{0,24}API|API[^\n]{0,24}สิทธิ์",
            "งานต้องใช้สิทธิ์ API ของหน่วยงานภายนอก",
            "ผู้ให้สิทธิ์ปฏิเสธหรือคิดค่าใช้จ่ายเพิ่มได้",
            LEVEL_HIGH,
            "ขอเงื่อนไขการเปิด API และผู้รับค่าใช้จ่ายเป็นลายลักษณ์อักษร",
        ),
        (
            r"ระบบสารบรรณ",
            "งานเชื่อมระบบสารบรรณภาครัฐ",
            "รูปแบบหนังสือและสิทธิ์เข้าระบบอยู่นอกสัญญา",
            LEVEL_MEDIUM_HIGH,
            "ระบุระบบ รูปแบบไฟล์ และผู้ประสานงานใน TOR",
        ),
        (
            r"แหล่งข่าว|สำนักข่าว",
            "งานอ้างแหล่งข่าวภายนอก",
            "ลิขสิทธิ์หรือความต่อเนื่องของแหล่งข่าวอยู่นอกการควบคุมผู้รับจ้าง",
            LEVEL_MEDIUM,
            "ระบุแหล่งที่อนุญาตให้ใช้และวิธีแทนเมื่อแหล่งปิด",
        ),
        (
            r"อบรมต่างประเทศ|ดูงานต่างประเทศ|ฝึกอบรมต่างประเทศ",
            "มีการอบรมหรือดูงานต่างประเทศ",
            "ค่าเดินทาง วีซ่า และจำนวนคนอยู่นอกเรตที่เห็นในข้อความ",
            LEVEL_HIGH,
            "แยกจำนวนคน สถานที่ และผู้รับค่าใช้จ่ายก่อนเสนอราคา",
        ),
        (
            r"อบรมในประเทศ|ฝึกอบรมในประเทศ",
            "มีการอบรมในประเทศที่ต้องประสานหน่วยงานภายนอก",
            "สถานที่ วิทยากร หรือจำนวนคนอาจยังไม่ปิด",
            LEVEL_MEDIUM,
            "ยืนยันจำนวนคน มื้ออาหาร สถานที่ และเอกสารประกอบ",
        ),
    )
    for pattern, issue, impact, level, mitigation in patterns:
        found = re.search(pattern, text, re.IGNORECASE)
        if not found:
            continue
        _add_row(
            rows,
            locator,
            needle=found.group(0),
            issue=issue,
            impact=impact,
            level=level,
            mitigation=mitigation,
        )
    return rows


def _schedule_rows(locator: _PageLocator) -> list[RiskRow]:
    text = locator.text
    rows: list[RiskRow] = []
    percents = [Decimal(item) for item in _PHASE_PERCENT.findall(text) if Decimal(item) >= 1]
    if len(percents) >= 2 and abs(sum(percents, Decimal(0)) - Decimal(100)) > Decimal(5):
        needle = "งวดที่"
        if needle in text:
            _add_row(
                rows,
                locator,
                needle=needle,
                issue="สัดส่วนงวดจ่ายรวมแล้วไม่ครบหรือเกินงาน",
                impact="มีช่วงที่ส่งงานแล้วไม่มีเงินเข้า หรือมีส่วนที่ไม่มีงวดรองรับ",
                level=LEVEL_HIGH,
                mitigation="ให้ร้อยละทุกงวดรวม 100 และระบุว่าช่วงว่างมีเงินหรือไม่",
            )
    if percents and percents[-1] >= 80:
        _add_row(
            rows,
            locator,
            needle="งวดที่",
            issue="งานและเงินกองที่งวดท้าย",
            impact="กระแสเงินสดติดลบยาวแล้วความเสี่ยงค่าปรับไปอยู่ที่งวดสุดท้าย",
            level=LEVEL_HIGH,
            mitigation="ขอย้ายผลงานส่งมอบและเงินมาใส่งวดก่อนหน้า",
        )
    elif re.search(r"งานที่เหลือทั้งหมด|กองที่งวดสุดท้าย", text):
        found = re.search(r"งานที่เหลือทั้งหมด|กองที่งวดสุดท้าย", text)
        if found:
            _add_row(
                rows,
                locator,
                needle=found.group(0),
                issue="ข้อความระบุว่างานกองที่งวดสุดท้าย",
                impact="ตรวจรับทั้งสัญญาถูกผูกกับงวดท้ายงวดเดียว",
                level=LEVEL_HIGH,
                mitigation="แตกผลงานส่งมอบให้ตรวจรับได้ระหว่างทาง",
            )
    anchors = [label for label, pattern in _START_ANCHORS if re.search(pattern, text)]
    if len(anchors) >= 2:
        _add_row(
            rows,
            locator,
            needle="นับ",
            issue="ถ้อยคำวันเริ่มนับเวลาไม่ตรงกัน",
            impact=f"ระยะเวลาอาจเริ่มคนละจุด ({' / '.join(anchors)}) แล้วค่าปรับเริ่มไม่พร้อมกัน",
            level=LEVEL_MEDIUM_HIGH,
            mitigation="ให้ทั้งสัญญาใช้จุดเริ่มเดียวและเขียนซ้ำให้ตรงกัน",
        )
    return rows


def _infrastructure_rows(locator: _PageLocator) -> list[RiskRow]:
    text = locator.text
    rows: list[RiskRow] = []
    infra = _INFRA.search(text)
    if infra:
        window = text[max(0, infra.start() - 80) : infra.end() + 80]
        not_ready = any(phrase in window for phrase in _INFRA_NOT_READY) or _VAGUE in window
        employer = bool(re.search(r"ผู้ว่าจ้าง|หน่วยงาน", window))
        if not_ready:
            _add_row(
                rows,
                locator,
                needle=infra.group(0),
                issue="Infrastructure ที่ต้องใช้ยังไม่พร้อม",
                impact="ส่งงานไม่ได้ถ้าเครื่องหรือสิทธิ์ยังไม่มีวันเริ่มสัญญา",
                level=LEVEL_CRITICAL,
                mitigation="ให้ผู้ว่าจ้างยืนยันสเปก วันพร้อมใช้ และผู้รับค่าใช้จ่ายเป็นลายลักษณ์อักษร",
                signal=SIGNAL_INFRA,
            )
        elif employer:
            _add_row(
                rows,
                locator,
                needle=infra.group(0),
                issue="ผู้ว่าจ้างเป็นผู้จัด Infrastructure",
                impact="ถ้าเครื่องไม่ตรงสเปกหรือมาช้า ผู้รับจ้างยังต้องส่งงานตามกำหนด",
                level=LEVEL_HIGH,
                mitigation="เขียนสเปก วันส่งมอบเครื่อง และผลเมื่อเครื่องมาช้าไว้ในสัญญา",
                signal=SIGNAL_INFRA,
            )
    license_hit = re.search(
        r"(?:ค่าไลเซนส์|ค่าลิขสิทธิ์|ค่า OS|ระบบปฏิบัติการ)[^\n]{0,40}ผู้รับจ้าง"
        r"|ผู้รับจ้าง[^\n]{0,40}(?:ค่าไลเซนส์|ค่าลิขสิทธิ์|ระบบปฏิบัติการ)",
        text,
    )
    if license_hit:
        _add_row(
            rows,
            locator,
            needle=license_hit.group(0),
            issue="ผู้รับจ้างรับค่า OS หรือไลเซนส์",
            impact="ต้นทุนลิขสิทธิ์อยู่นอกวงเงินที่มองเห็นถ้าไม่ได้ใส่ในราคา",
            level=LEVEL_MEDIUM_HIGH,
            mitigation="ใส่ราคาไลเซนส์ในใบเสนอราคาก่อนยื่น",
        )
    tie = re.search(r"ต้องใช้[^\n]{0,40}(?:Microsoft\s+Word|เอดิเตอร์|สแกนเนอร์)", text, re.IGNORECASE)
    if tie:
        _add_row(
            rows,
            locator,
            needle=tie.group(0),
            issue="งานผูกกับเอดิเตอร์หรือสแกนเนอร์ที่ระบุชื่อ",
            impact="เปลี่ยนเครื่องมือไม่ได้แม้แผง lock specs จะคนละประเด็นกับยี่ห้อฮาร์ดแวร์",
            level=LEVEL_MEDIUM_HIGH,
            mitigation="ขอทางเลือกที่เทียบเท่า หรือให้หน่วยงานเป็นผู้จัดเครื่องมือนั้น",
        )
    return rows


def _penalty_rows(locator: _PageLocator, box: PenaltyBox) -> list[RiskRow]:
    text = locator.text
    if _PENALTY_WORD not in text:
        return []
    tied = _last_phase_tied(text, box.base)
    if tied:
        level = LEVEL_CRITICAL
        signal = SIGNAL_LAST_PHASE
        issue = "งวดสุดท้ายผูกค่าปรับทั้งสัญญา"
        impact = "งานงวดท้ายไม่ครบแล้วถูกปรับจากมูลค่าสัญญาทั้งหมด ไม่ใช่เฉพาะเงินงวดนั้น"
    elif box.percent_per_day is not None and box.percent_per_day > 0.20:
        level = LEVEL_HIGH
        signal = ""
        issue = "อัตราค่าปรับต่อวันสูงกว่าช่วงที่ระเบียบใช้เป็นปกติ"
        impact = box.amount_note or _NO_AMOUNT
    else:
        level = LEVEL_MEDIUM
        signal = ""
        issue = "มีค่าปรับรายวันที่ต้องคำนวณจากข้อความ"
        impact = box.amount_note or _NO_AMOUNT
    rows: list[RiskRow] = []
    _add_row(
        rows,
        locator,
        needle=_PENALTY_WORD,
        issue=issue,
        impact=impact,
        level=level,
        mitigation="ให้ผู้ว่าจ้างยืนยันฐานค่าปรับ วิธีคิดเมื่องวดซ้อน และตัวอย่างจำนวนเงิน",
        signal=signal,
    )
    if box.phase_penalty_note:
        match = _PHASE_PENALTY.search(text)
        if match:
            _add_row(
                rows,
                locator,
                needle=match.group(0),
                issue="TOR ปรับเป็นรายงวดเมื่องวดส่งไม่ครบ",
                impact="แต่ละงวดที่ค้างอาจถูกปรับแยกจากค่าปรับทั้งสัญญา",
                level=LEVEL_HIGH,
                mitigation="ถามว่าค่าปรับรายงวดซ้อนกับค่าปรับทั้งสัญญาหรือไม่",
            )
    return rows



def _append_pqc_row(
    rows: list[RiskRow],
    locator: _PageLocator,
    text: str,
    pqc: re.Match[str],
) -> None:
    window = text[max(0, pqc.start() - 40) : pqc.end() + 40]
    required = any(word in window for word in ("ต้อง", "ใช้จริง", "ใช้งาน"))
    level = LEVEL_CRITICAL if required else LEVEL_HIGH
    _add_row(
        rows,
        locator,
        needle=pqc.group(0),
        issue="TOR ให้ใช้ PQC จริง",
        impact="พิสูจน์อัลกอริทึมและไลบรารีไม่ได้แล้วตรวจรับไม่ผ่าน",
        level=level,
        mitigation="ระบุอัลกอริทึม ไลบรารี และวิธีทดสอบที่หน่วยงานยอมรับ",
        signal=SIGNAL_PQC,
    )


def _append_cashflow_row(rows: list[RiskRow], locator: _PageLocator, text: str) -> None:
    phase_values = [
        Decimal(item) for item in _PHASE_PERCENT.findall(text) if Decimal(item) >= 1
    ]
    paid = sum(phase_values, Decimal(0))
    phase_gap = bool(phase_values) and abs(paid - Decimal(100)) > Decimal(5)
    mentions_cash = re.search(r"ไม่มีเงินเข้า|กระแสเงินสด", text) is not None
    installment_gap = "งวด" in text and phase_gap
    if not mentions_cash and not installment_gap:
        return
    needle = "กระแสเงินสด" if "กระแสเงินสด" in text else "งวด"
    if needle not in text:
        return
    _add_row(
        rows,
        locator,
        needle=needle,
        issue="กระแสเงินสดระหว่างงวดยังไม่ปิด",
        impact="ช่วงที่ไม่มีเงินเข้าอาจยาวกว่าที่ต้นทุนรับได้",
        level=LEVEL_HIGH,
        mitigation="ทำตารางเงินเข้ารายงวดเทียบต้นทุนก่อนยื่น",
    )


def _security_rows(locator: _PageLocator) -> list[RiskRow]:
    text = locator.text
    rows: list[RiskRow] = []
    pqc = _PQC.search(text)
    if pqc:
        _append_pqc_row(rows, locator, text, pqc)
    vuln = re.search(r"ทดสอบช่องโหว่|penetration|pentest", text, re.IGNORECASE)
    if vuln:
        _add_row(
            rows,
            locator,
            needle=vuln.group(0),
            issue="มีงานทดสอบช่องโหว่",
            impact="ขอบเขตทดสอบและผู้รับค่าใช้จ่ายอาจกินงบที่ไม่ได้ตั้งไว้",
            level=LEVEL_MEDIUM_HIGH,
            mitigation="ระบุจำนวนรอบ ระบบที่ทดสอบ และผู้จ่ายค่าเครื่องมือ",
        )
    governance = re.search(r"ธรรมาภิบาล(?:ด้าน)?(?:AI|ปัญญาประดิษฐ์)|AI governance", text, re.IGNORECASE)
    if governance:
        _add_row(
            rows,
            locator,
            needle=governance.group(0),
            issue="มีข้อ AI governance",
            impact="หลักฐานการกำกับโมเดลอาจเป็นงานเพิ่มที่ไม่ได้คิดราคา",
            level=LEVEL_MEDIUM_HIGH,
            mitigation="ขอรายการเอกสารที่ต้องส่งมอบด้านธรรมาภิบาล",
        )
    ownership = re.search(
        r"กรรมสิทธิ์[^\n]{0,40}(?:ซอร์สโค้ด|ซอร์ส|source)|ซอร์สโค้ดเป็นของ|source code เป็นของ",
        text,
        re.IGNORECASE,
    )
    if ownership:
        _add_row(
            rows,
            locator,
            needle=ownership.group(0),
            issue="กรรมสิทธิ์ซอร์สโค้ดถูกกำหนดใน TOR",
            impact="ต้องส่งมอบโค้ดและสิทธิ์ที่อาจติดไลเซนส์บุคคลที่สาม",
            level=LEVEL_HIGH,
            mitigation="แยกส่วนที่ส่งมอบได้กับส่วนที่ติดไลบรารีภายนอก",
        )
    nda = re.search(r"\bNDA\b|สัญญาไม่เปิดเผย|ข้อตกลงการไม่เปิดเผย", text, re.IGNORECASE)
    if nda:
        _add_row(
            rows,
            locator,
            needle=nda.group(0),
            issue="มีข้อผูกพันการไม่เปิดเผยข้อมูล",
            impact="ขอบเขตข้อมูลลับกระทบการจ้างช่วงและการเก็บหลักฐาน",
            level=LEVEL_MEDIUM,
            mitigation="อ่านระยะเวลาและความรับผิดก่อนยื่น",
        )
    warranty = re.search(r"รับประกัน[^\n]{0,40}(?:ค่าใช้จ่าย|ตลอดอายุ|ผู้รับจ้างรับภาระ)", text)
    if warranty:
        _add_row(
            rows,
            locator,
            needle=warranty.group(0),
            issue="ภาระรับประกันถูกใส่เป็นต้นทุนของผู้รับจ้าง",
            impact="ค่าอะไหล่หรือคนประจำการอยู่นอกราคาถ้าไม่ใส่ในใบเสนอราคา",
            level=LEVEL_MEDIUM,
            mitigation="คิดต้นทุนรับประกันตามระยะที่ข้อความระบุ",
        )
    _append_cashflow_row(rows, locator, text)
    return rows


def _unique(rows: list[RiskRow]) -> list[RiskRow]:
    seen: set[tuple[str, str]] = set()
    kept: list[RiskRow] = []
    for row in rows:
        key = (row.issue, row.quote[:80])
        if key in seen:
            continue
        seen.add(key)
        kept.append(row)
    return kept


def _gates(rows: list[RiskRow]) -> list[str]:
    gates: list[str] = []
    for row in rows:
        gate = GATE_BY_SIGNAL.get(row.signal or "")
        if row.level in {LEVEL_CRITICAL, LEVEL_HIGH} and gate and gate not in gates:
            gates.append(gate)
    return gates


def _recommendation(text: str, rows: list[RiskRow]) -> tuple[str, str, list[str]]:
    decision = [row for row in rows if row.signal in DECISION_SIGNALS]
    critical = [row for row in decision if row.level == LEVEL_CRITICAL]
    high = [row for row in decision if row.level == LEVEL_HIGH]
    gates = _gates(critical + high)
    if len((text or "").strip()) < 40 and not rows:
        sentence = f"ข้อมูลไม่พอสำหรับประเมินความเสี่ยงก่อนยื่น {DISCLAIMER}"
        return sentence, "insufficient", []
    if critical:
        gate_text = f" ด่านที่ยังเปิด: {', '.join(gates)}" if gates else ""
        sentence = f"ไม่ควรยื่นในสถานะข้อมูลปัจจุบัน{gate_text} {DISCLAIMER}"
        return sentence, "do_not_bid", gates
    if high:
        named = ", ".join(gates) if gates else "ด่านที่ระบุในตาราง"
        sentence = f"พิจารณาได้เมื่อปิดด่านที่ระบุ: {named} {DISCLAIMER}"
        return sentence, "consider", gates
    sentence = f"ไม่พบความเสี่ยงสูงจากข้อความที่มี ซึ่งไม่ใช่คำรับรองว่าควรยื่น {DISCLAIMER}"
    return sentence, "no_high_risk", []


def _markdown(report: BidderRiskReport) -> str:
    lines = [
        "# ความเสี่ยงก่อนตัดสินใจยื่น",
        "",
        report.recommendation,
        "",
        "## ค่าปรับ",
        f"- ฐาน: {report.penalty.base_label}",
    ]
    if report.penalty.amount_note:
        lines.append(f"- {report.penalty.amount_note}")
    if report.penalty.hourly_note:
        lines.append(f"- {report.penalty.hourly_note}")
    if report.penalty.phase_penalty_note:
        lines.append(f"- {report.penalty.phase_penalty_note}")
    if report.penalty.overlap_note:
        lines.append(f"- {report.penalty.overlap_note}")
    lines.append("")
    for category in report.categories:
        lines.extend(
            [
                f"## {category.label}",
                "",
                "| ประเด็น | ข้อกำหนด | ผลกระทบ | ระดับ | สิ่งที่ต้องตรวจ |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        if not category.rows:
            lines.append("| ไม่พบประเด็นจากข้อความที่มี |  |  |  |  |")
        for row in category.rows:
            cells = [
                row.issue,
                row.requirement,
                row.impact,
                row.level,
                row.mitigation,
            ]
            escaped = [cell.replace("|", "\\|").replace("\n", " ") for cell in cells]
            lines.append("| " + " | ".join(escaped) + " |")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def assess_bidder_risk(
    text: str,
    *,
    pages: list[Any] | None = None,
    budget: int | None = None,
    penalty_rate_percent: float | None = None,
) -> BidderRiskReport:
    """Build the six-category report from TOR text and optional page records."""
    source = text or ""
    if pages:
        joined = text_with_page_markers(source, pages)
        if joined.strip():
            source = joined
    locator = _PageLocator(source, pages)
    penalty = build_penalty_box(
        source,
        budget=budget,
        penalty_rate_percent=penalty_rate_percent,
    )
    grouped = {
        "clarity": _unique(_clarity_rows(locator)),
        "external": _unique(_external_rows(locator)),
        "schedule": _unique(_schedule_rows(locator)),
        "infrastructure": _unique(_infrastructure_rows(locator)),
        "penalty": _unique(_penalty_rows(locator, penalty)),
        "security": _unique(_security_rows(locator)),
    }
    categories = [
        RiskCategory(key=key, label=label, rows=grouped[key]) for key, label in CATEGORY_SPECS
    ]
    flat = [row for category in categories for row in category.rows]
    recommendation, kind, gates = _recommendation(source, flat)
    report = BidderRiskReport(
        recommendation=recommendation,
        recommendation_kind=kind,
        disclaimer=DISCLAIMER,
        gates=gates,
        penalty=penalty,
        categories=categories,
    )
    report.markdown = _markdown(report)
    return report
