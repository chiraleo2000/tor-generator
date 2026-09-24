"""Reusable three-part TOR analyzer (legal, lock-in, project).

Other agents call ``analyze_tor`` to score a draft in Thai. Each part returns
0–100, a deduction explanation, and findings (source quote, reason, suggested
text). The total is a weighted blend. Missing sections are recorded but do not
zero the three scores when the draft still has text.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.rule_engine.engine import (
    KIND_LEGAL,
    Finding,
    Severity,
    SEVERITY_DEDUCTIONS,
    first_law_citation,
)
from app.rule_engine.rules.legal import (
    BrandLockFairnessRule,
    PenaltyRateRule,
    RequiredLegalReferencesRule,
    VendorPaidUpCapitalRule,
)
from app.rule_engine.rules.risk import AnnouncedPriceRule, ProcurementMethodRule
from app.rule_engine.rules.timeline import TimelineFeasibilityRule

PART_LEGAL = "legal"
PART_LOCK_IN = "lock_in"
PART_PROJECT = "project"

PART_LABELS: dict[str, str] = {
    PART_LEGAL: "ส่วนที่คาดว่าผิดกฎหมาย",
    PART_LOCK_IN: "ความเสี่ยง lock specs",
    PART_PROJECT: "ความเสี่ยงบริหารโครงการ",
}

# Weighted blend used as the review-page total.
PART_WEIGHTS: dict[str, float] = {
    PART_LEGAL: 0.40,
    PART_LOCK_IN: 0.30,
    PART_PROJECT: 0.30,
}

NO_ISSUE_TEXT = {
    PART_LEGAL: (
        "ตรวจตาม พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560 "
        "และระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ "
        "พ.ศ. 2560 แล้วไม่พบประเด็นในด้านกฎหมาย"
    ),
    PART_LOCK_IN: (
        "ตรวจตามหลักความเป็นธรรมในการแข่งขันและชุดความรู้ Oracle/IVM ในคลัง "
        "แล้วไม่พบการเจาะจงยี่ห้อ บริษัท บุคคล หรือผลิตภัณฑ์โดยไม่มี «หรือเทียบเท่า»"
    ),
    PART_PROJECT: (
        "ตรวจด้านส่งมอบ SLA การเข้างาน ต้นทุนที่เป็นไปได้ และ price-performance "
        "แล้วไม่พบประเด็นบริหารโครงการจากข้อความที่มี"
    ),
}

_EQUIVALENCE_PHRASES = (
    "หรือเทียบเท่า",
    "หรือยี่ห้ออื่นที่เทียบเท่า",
    "หรือเทียบเคียง",
    "or equivalent",
    "or equal",
    "หรือคุณสมบัติเทียบเท่า",
    "หรือที่มีคุณสมบัติเทียบเท่า",
)

_GENERIC_COMPANY = (
    "ผู้รับจ้าง",
    "คู่สัญญา",
    "เอกชน",
    "ผู้เสนอราคา",
    "ผู้ชนะ",
    "มหาชน",
)

_WORD_DELIVERY = "ส่งมอบ"
_WORD_INSTALL = "ติดตั้ง"
_WORD_SITE = "สถานที่"

# Generic company words are filtered in Python so this pattern stays under the regex limit.
_COMPANY_RE = re.compile(
    r"(บริษัท\s*[ก-๙A-Za-z0-9.&]{2,}(?:\s+จำกัด(?:\s*\(\s*มหาชน\s*\))?)?)"
)
_PERSON_RE = re.compile(r"(นาย|นางสาว|นาง)\s+[ก-๙A-Za-z]{2,}")
_MODEL_RE = re.compile(r"(รุ่น\s+[A-Za-z0-9][A-Za-z0-9\-_.]+)")
_PENALTY_RATE_RE = re.compile(
    r"(?:ค่าปรับ[^។\n]{0,40})?ร้อยละ\s*(\d+(?:\.\d+)?)\s*(?:%\s*)?(?:ต่อวัน)?"
)
_DAYS_RE = re.compile(r"(?:ภายใน|ไม่เกิน|ระยะเวลา(?:ดำเนินการ)?)\s*(\d{1,3})\s*วัน")
_LOWEST_COST_RE = re.compile(r"(ราคาต่ำสุด|ราคาถูกที่สุด|ราคาต่ำที่สุด|lowest\s+price)")

_ORACLE_JSON = Path(__file__).resolve().parents[1] / "domain" / "oracle_ivm_lockin.json"


@dataclass
class AnalyzerFinding:
    """One issue found on a scoring axis."""

    source_quote: str
    reason: str
    suggested_text: str
    section_key: str = ""
    legal_basis: str | None = None
    severity: str = "warning"


@dataclass
class PartScore:
    """Score, Thai explanation, and findings for one analyzer axis."""

    key: str
    label: str
    score: int
    explanation: str
    findings: list[AnalyzerFinding] = field(default_factory=list)


@dataclass
class TorAnalysisResult:
    """Three-part TOR analysis that other agents can persist or render."""

    legal: PartScore
    lock_in: PartScore
    project: PartScore
    total: int
    summary: str
    missing_sections: dict[str, str] = field(default_factory=dict)
    halted: bool = False

    def part(self, key: str) -> PartScore:
        mapping = {
            PART_LEGAL: self.legal,
            PART_LOCK_IN: self.lock_in,
            PART_PROJECT: self.project,
        }
        return mapping[key]


def analysis_as_dict(result: TorAnalysisResult) -> dict[str, Any]:
    """JSON-ready payload for review APIs and analysis_json."""
    return asdict(result)


def analyze_tor(
    tor_document: dict[str, Any] | None,
    *,
    user_documents: str = "",
    rag_text: str = "",
) -> TorAnalysisResult:
    """Score a TOR on legal, lock-in, and project axes (0–100 each).

    Args:
        tor_document: Section map (``s1``..``s13``) plus optional ``sections``,
            ``budget``, ``timeline_days``, and ``project_type``.
        user_documents: Project/KB text the user added; used in explanations
            when present, not as a substitute for statute text.
        rag_text: Central handbook / พ.ร.บ. excerpts from RAG.

    Returns:
        ``TorAnalysisResult`` with part scores, weighted total, and a one-sentence
        Thai summary of which part pulled the score down.
    """
    document = dict(tor_document or {})
    sections = _section_map(document)
    joined = "\n".join(sections.values())
    has_content = bool(joined.strip())
    missing, halted = _missing_sections(document)

    legal_findings = _score_legal(document, sections, rag_text)
    lock_findings = _score_lock_in(document, sections)
    project_findings = _score_project(document, sections)

    legal = _build_part(PART_LEGAL, legal_findings, has_content, missing)
    lock_in = _build_part(PART_LOCK_IN, lock_findings, has_content, missing)
    project = _build_part(PART_PROJECT, project_findings, has_content, missing)

    if has_content:
        legal, lock_in, project = _guard_nonzero_panel(legal, lock_in, project)

    if user_documents.strip():
        extra = (
            " ใช้เอกสารที่ผู้ใช้เพิ่มในโครงการหรือคลังของฉันประกอบการตรวจแล้ว"
        )
        legal.explanation = legal.explanation + extra
        lock_in.explanation = lock_in.explanation + extra
        project.explanation = project.explanation + extra

    total = _weighted_total(legal, lock_in, project)
    summary = _summary_sentence(legal, lock_in, project, missing)
    return TorAnalysisResult(
        legal=legal,
        lock_in=lock_in,
        project=project,
        total=total,
        summary=summary,
        missing_sections=missing,
        halted=halted,
    )


def _section_map(document: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    nested = document.get("sections")
    sources: list[Any] = [document]
    if isinstance(nested, dict):
        sources.append(nested)
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key, value in source.items():
            if not isinstance(key, str) or not key.startswith("s"):
                continue
            text = _as_text(value)
            if text and (key not in out or len(text) > len(out[key])):
                out[key] = text
    return out


def _as_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return " ".join(str(item).strip() for item in value.values() if item).strip()
    return ""


def _missing_sections(document: dict[str, Any]) -> tuple[dict[str, str], bool]:
    from app.rule_engine.rules.completeness import MissingSectionsHalt, SectionPresenceRule

    try:
        SectionPresenceRule().validate(document)
    except MissingSectionsHalt as halt:
        return dict(halt.missing_sections), True
    return {}, False


def _score_legal(
    document: dict[str, Any],
    sections: dict[str, str],
    rag_text: str,
) -> list[AnalyzerFinding]:
    findings: list[AnalyzerFinding] = []
    citation = first_law_citation(rag_text)
    rules = (
        VendorPaidUpCapitalRule(),
        PenaltyRateRule(),
        RequiredLegalReferencesRule(),
        AnnouncedPriceRule(),
        ProcurementMethodRule(),
    )
    for rule in rules:
        for item in rule.validate(document):
            findings.append(_from_engine_finding(item, sections, citation))
    findings.extend(_penalty_from_text(sections, citation))
    findings.extend(_missing_regulation_ref(sections, citation))
    return _dedupe_findings(findings)


def _score_lock_in(
    document: dict[str, Any],
    sections: dict[str, str],
) -> list[AnalyzerFinding]:
    findings: list[AnalyzerFinding] = []
    for item in BrandLockFairnessRule().validate(document):
        findings.append(_from_engine_finding(item, sections, item.legal_basis))
    findings.extend(_company_person_lock(sections))
    findings.extend(_oracle_lock(sections))
    return _dedupe_findings(findings)


def _score_project(
    document: dict[str, Any],
    sections: dict[str, str],
) -> list[AnalyzerFinding]:
    findings: list[AnalyzerFinding] = []
    for item in TimelineFeasibilityRule().validate(document):
        findings.append(_from_engine_finding(item, sections, item.legal_basis))
    findings.extend(_impossible_timeline(document, sections))
    findings.extend(_delivery_vs_scope(sections))
    findings.extend(_sla_consideration(sections))
    findings.extend(_site_access(sections))
    findings.extend(_owner_dependencies(sections))
    findings.extend(_cost_vs_performance(sections))
    return _dedupe_findings(findings)


def _from_engine_finding(
    item: Finding,
    sections: dict[str, str],
    fallback_basis: str | None,
) -> AnalyzerFinding:
    quote = (item.excerpt or "").strip()
    if not quote:
        quote = _quote(sections.get(item.affected_section, ""), item.message)
    basis = item.legal_basis or fallback_basis
    if item.finding_kind == KIND_LEGAL and not basis:
        basis = (
            "พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560 "
            "และระเบียบกระทรวงการคลัง พ.ศ. 2560"
        )
    return AnalyzerFinding(
        source_quote=quote[:280],
        reason=item.message,
        suggested_text=item.recommended_correction or "",
        section_key=item.affected_section,
        legal_basis=basis,
        severity=item.severity.value if hasattr(item.severity, "value") else str(item.severity),
    )


def _penalty_from_text(
    sections: dict[str, str],
    citation: str,
) -> list[AnalyzerFinding]:
    findings: list[AnalyzerFinding] = []
    text = sections.get("s10") or ""
    if not text:
        return findings
    for match in _PENALTY_RATE_RE.finditer(text):
        window = text[max(0, match.start() - 12) : match.end() + 8]
        if "ค่าปรับ" not in window and "ต่อวัน" not in match.group(0):
            continue
        rate = float(match.group(1))
        if 0.01 <= rate <= 0.20:
            continue
        findings.append(
            AnalyzerFinding(
                source_quote=window.strip()[:280],
                reason=(
                    f"อัตราค่าปรับร้อยละ {rate:g} ต่อวันอยู่นอกช่วง 0.01–0.20 "
                    "ตามระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างฯ พ.ศ. 2560 ข้อว่าด้วยค่าปรับ"
                ),
                suggested_text=(
                    "กำหนดค่าปรับร้อยละ 0.01–0.20 ต่อวัน และไม่ต่ำกว่า 100 บาทต่อวัน "
                    "ตามระเบียบกระทรวงการคลัง พ.ศ. 2560"
                ),
                section_key="s10",
                legal_basis=citation
                or "ระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560 ข้อว่าด้วยค่าปรับ",
                severity=Severity.ERROR.value,
            )
        )
    return findings


def _missing_regulation_ref(
    sections: dict[str, str],
    citation: str,
) -> list[AnalyzerFinding]:
    joined = " ".join(sections.values())
    if not joined.strip() or "s1" not in sections:
        return []
    has_reg = (
        "ระเบียบกระทรวงการคลัง" in joined
        or ("ระเบียบ" in joined and "2560" in joined and "จัดซื้อ" in joined)
    )
    if has_reg:
        return []
    return [
        AnalyzerFinding(
            source_quote=_quote(sections.get("s1", ""), "ระเบียบ"),
            reason=(
                "ไม่พบการอ้างระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้าง"
                "และการบริหารพัสดุภาครัฐ พ.ศ. 2560"
            ),
            suggested_text=(
                "เพิ่มการอ้างอิงระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้าง"
                "และการบริหารพัสดุภาครัฐ พ.ศ. 2560 ในส่วนความเป็นมาหรือเงื่อนไขทั่วไป"
            ),
            section_key="s1",
            legal_basis=citation
            or "ระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560",
            severity=Severity.WARNING.value,
        )
    ]


def _is_generic_company(kind: str, name: str) -> bool:
    if kind != "บริษัท":
        return False
    return any(word in name for word in _GENERIC_COMPANY)


def _named_entity_finding(
    key: str,
    content: str,
    match: re.Match[str],
    kind: str,
    seen: set[str],
) -> AnalyzerFinding | None:
    name = match.group(0).strip()
    token = name.lower()
    if token in seen or _is_generic_company(kind, name):
        return None
    context = content[max(0, match.start() - 40) : match.end() + 80]
    if any(phrase in context for phrase in _EQUIVALENCE_PHRASES):
        return None
    seen.add(token)
    return AnalyzerFinding(
        source_quote=context.strip()[:280],
        reason=f"พบการเจาะจง{kind} «{name}» โดยไม่มีข้อความ «หรือเทียบเท่า»",
        suggested_text=f"แทนด้วยคุณสมบัติเชิงหน้าที่ หรือเขียนว่า «{name} หรือเทียบเท่า»",
        section_key=key,
        legal_basis=(
            "หลักความเป็นธรรมในการแข่งขันตาม พ.ร.บ. "
            "การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560"
        ),
        severity=Severity.WARNING.value,
    )


def _company_person_lock(sections: dict[str, str]) -> list[AnalyzerFinding]:
    findings: list[AnalyzerFinding] = []
    seen: set[str] = set()
    patterns = ((_COMPANY_RE, "บริษัท"), (_PERSON_RE, "บุคคล"), (_MODEL_RE, "รุ่น"))
    for key in ("s3", "s4", "s5", "s6", "s8"):
        content = sections.get(key, "")
        if not content:
            continue
        for pattern, kind in patterns:
            for match in pattern.finditer(content):
                finding = _named_entity_finding(key, content, match, kind, seen)
                if finding is None:
                    continue
                findings.append(finding)
    return findings


@lru_cache(maxsize=1)
def _oracle_rules() -> list[dict[str, Any]]:
    raw = json.loads(_ORACLE_JSON.read_text(encoding="utf-8"))
    rules = raw.get("rules")
    return list(rules) if isinstance(rules, list) else []


def _keyword_hit(rule: dict[str, Any], lower: str) -> str:
    for item in rule.get("keywords") or []:
        if not item:
            continue
        word = str(item)
        if word.lower() in lower:
            return word
    return ""


def _oracle_hit_is_exempt(content: str, lower: str, hit: str) -> bool:
    if not any(phrase in content for phrase in _EQUIVALENCE_PHRASES):
        return False
    start = lower.find(hit.lower())
    window = content[max(0, start - 40) : start + len(hit) + 80]
    return any(phrase in window for phrase in _EQUIVALENCE_PHRASES)


def _oracle_finding(
    rule: dict[str, Any],
    key: str,
    content: str,
    lower: str,
    hit: str,
) -> AnalyzerFinding:
    start = lower.find(hit.lower())
    quote = hit if start < 0 else content[max(0, start) : start + 180]
    basis = str(rule.get("legal_basis") or "")
    return AnalyzerFinding(
        source_quote=quote.strip()[:280],
        reason=str(rule.get("reason") or rule.get("title") or hit),
        suggested_text=str(rule.get("suggested_text") or ""),
        section_key=key,
        legal_basis=basis or None,
        severity=Severity.WARNING.value,
    )


def _append_oracle_hit(
    findings: list[AnalyzerFinding],
    seen: set[str],
    key: str,
    content: str,
    lower: str,
    rule: dict[str, Any],
) -> None:
    rule_id = str(rule.get("id") or "")
    hit = _keyword_hit(rule, lower)
    if not hit or rule_id in seen:
        return
    if _oracle_hit_is_exempt(content, lower, hit):
        return
    seen.add(rule_id)
    findings.append(_oracle_finding(rule, key, content, lower, hit))


def _oracle_lock(sections: dict[str, str]) -> list[AnalyzerFinding]:
    findings: list[AnalyzerFinding] = []
    seen: set[str] = set()
    for key, content in sections.items():
        if not content:
            continue
        lower = content.lower()
        for rule in _oracle_rules():
            _append_oracle_hit(findings, seen, key, content, lower, rule)
    return findings


def _impossible_timeline(
    document: dict[str, Any],
    sections: dict[str, str],
) -> list[AnalyzerFinding]:
    scope = sections.get("s4") or sections.get("s4.1") or ""
    timeline = sections.get("s5") or ""
    days = document.get("timeline_days")
    if not isinstance(days, (int, float)):
        match = _DAYS_RE.search(timeline or scope)
        days = int(match.group(1)) if match else None
    if days is None:
        return []
    days_i = int(days)
    bulky = len(scope) >= 180 or _WORD_DELIVERY in scope or "ระบบ" in scope
    if days_i > 21 or not bulky:
        return []
    quote = _quote(timeline or scope, f"{days_i} วัน")
    return [
        AnalyzerFinding(
            source_quote=quote,
            reason=(
                f"ระยะเวลา {days_i} วันคับแคบเมื่อเทียบกับขอบเขตงานที่มี "
                "เสี่ยงส่งมอบไม่ทันและสร้างภาระค่าปรับ"
            ),
            suggested_text=(
                "ปรับระยะเวลาให้สอดคล้องปริมาณงานและผลงานส่งมอบ "
                "หรือลดขอบเขตให้ทำได้จริงในเวลาที่กำหนด"
            ),
            section_key="s5" if timeline else "s4",
            severity=Severity.ERROR.value,
        )
    ]


def _delivery_vs_scope(sections: dict[str, str]) -> list[AnalyzerFinding]:
    scope = sections.get("s4") or ""
    payment = sections.get("s8") or ""
    if len(scope) < 80:
        return []
    scope_has = "ผลงานส่งมอบ" in scope or _WORD_DELIVERY in scope
    pay_has = "ผลงานส่งมอบ" in payment or _WORD_DELIVERY in payment
    if scope_has and pay_has:
        return []
    if not scope_has and not pay_has:
        return [
            AnalyzerFinding(
                source_quote=_quote(scope, "ขอบเขต"),
                reason="ขอบเขตงานยังไม่ผูกกับผลงานส่งมอบหรืองวดงานที่ตรวจรับได้",
                suggested_text=(
                    "เพิ่มตารางผลงานส่งมอบในขอบเขตงาน และอ้างอิงชุดเดียวกันในงวดงาน"
                ),
                section_key="s4",
                severity=Severity.WARNING.value,
            )
        ]
    return [
        AnalyzerFinding(
            source_quote=_quote(scope if scope_has else payment, _WORD_DELIVERY),
            reason="ผลงานส่งมอบในขอบเขตงานกับงวดงานยังไม่สอดคล้องกัน",
            suggested_text=(
                "ให้ผลงานส่งมอบแต่ละรายการปรากฏทั้งในขอบเขตงานและงวดงาน"
            ),
            section_key="s8" if scope_has else "s4",
            severity=Severity.WARNING.value,
        )
    ]


def _sla_consideration(sections: dict[str, str]) -> list[AnalyzerFinding]:
    joined = " ".join(sections.get(key, "") for key in ("s4", "s9", "s11"))
    if len(joined) < 80:
        return []
    it_like = any(
        word in joined
        for word in ("ระบบ", "ซอฟต์แวร์", "เว็บไซต์", "แอปพลิเคชัน", "SLA", "บริการ")
    )
    if not it_like:
        return []
    if "SLA" in joined or "ระดับบริการ" in joined or "เวลาซ่อม" in joined:
        return []
    return [
        AnalyzerFinding(
            source_quote=_quote(joined, "ระบบ"),
            reason=(
                "งานลักษณะระบบ/บริการยังไม่มี SLA หรือระดับบริการที่วัดได้ "
                "ซึ่งเป็นประเด็นบริหารโครงการ ไม่ใช่ราคากลางตามกฎหมาย"
            ),
            suggested_text=(
                "กำหนดระดับบริการ เช่น เวลาตอบสนอง เวลาซ่อม และร้อยละความพร้อมใช้"
            ),
            section_key="s4",
            severity=Severity.WARNING.value,
        )
    ]


def _site_access(sections: dict[str, str]) -> list[AnalyzerFinding]:
    joined = " ".join(sections.values())
    site_like = any(
        word in joined
        for word in (_WORD_INSTALL, _WORD_SITE, "หน่วยงานผู้ใช้", "เข้าพื้นที่", "ลงพื้นที่", "ก่อสร้าง")
    )
    if not site_like:
        return []
    if "เข้างาน" in joined or "เข้าพื้นที่" in joined or "เวลาทำการ" in joined:
        return []
    return [
        AnalyzerFinding(
            source_quote=_quote(joined, _WORD_INSTALL if _WORD_INSTALL in joined else _WORD_SITE),
            reason="งานที่ต้องเข้าพื้นที่ยังไม่กำหนดเงื่อนไขเข้างานหรือเข้าพื้นที่",
            suggested_text=(
                "ระบุวันเวลาเข้างาน จุดประสานงาน และสิ่งที่ผู้ว่าจ้างต้องจัดให้ก่อนเข้าพื้นที่"
            ),
            section_key="s4",
            severity=Severity.WARNING.value,
        )
    ]


def _owner_dependencies(sections: dict[str, str]) -> list[AnalyzerFinding]:
    joined = " ".join(sections.values())
    if len(joined) < 120:
        return []
    if "ผู้ว่าจ้างต้อง" in joined or "หน่วยงานต้องจัดให้" in joined:
        return []
    needs_owner = any(
        word in joined
        for word in ("ข้อมูลเดิม", "เข้าถึงระบบ", "บัญชีผู้ใช้", _WORD_SITE, _WORD_INSTALL)
    )
    if not needs_owner:
        return []
    return [
        AnalyzerFinding(
            source_quote=_quote(joined, "ข้อมูล" if "ข้อมูล" in joined else _WORD_INSTALL),
            reason="ยังไม่ระบุสิ่งที่ผู้ว่าจ้างต้องจัดให้ ซึ่งเป็นเงื่อนไขบริหารโครงการ",
            suggested_text=(
                "เพิ่มหัวข้อสิ่งที่ผู้ว่าจ้างต้องจัดให้ เช่น ข้อมูล บัญชีเข้าถึง และสถานที่"
            ),
            section_key="s4",
            severity=Severity.SUGGESTION.value,
        )
    ]


def _cost_vs_performance(sections: dict[str, str]) -> list[AnalyzerFinding]:
    budget = sections.get("s6") or ""
    criteria = sections.get("s7") or sections.get("s8") or ""
    text = f"{budget}\n{criteria}"
    if not _LOWEST_COST_RE.search(text):
        return []
    if any(word in text for word in ("price-performance", "ราคาต่อประสิทธิภาพ", "คุณภาพ", "SLA")):
        return []
    match = _LOWEST_COST_RE.search(text)
    quote = match.group(0) if match else text[:120]
    return [
        AnalyzerFinding(
            source_quote=quote,
            reason=(
                "ใช้เกณฑ์ราคาต่ำสุดโดยไม่เทียบคุณภาพหรือ price-performance "
                "ซึ่งเป็นประเด็นพิจารณาต้นทุนที่เป็นไปได้ ไม่ใช่ราคากลางตามกฎหมาย"
            ),
            suggested_text=(
                "ระบุเกณฑ์คุณภาพหรือ price-performance ควบคู่ราคา "
                "และอธิบายต้นทุนต่ำสุดที่ทำได้จริงตามขอบเขต"
            ),
            section_key="s6" if budget else "s7",
            severity=Severity.WARNING.value,
        )
    ]


def _build_part(
    key: str,
    findings: list[AnalyzerFinding],
    has_content: bool,
    missing: dict[str, str],
) -> PartScore:
    score = 100.0
    lines: list[str] = []
    for item in findings:
        try:
            severity = Severity(item.severity)
        except ValueError:
            severity = Severity.WARNING
        deduct = SEVERITY_DEDUCTIONS.get(severity, 10.0)
        score -= deduct
        lines.append(f"หัก {deduct:.0f} คะแนน เพราะ{item.reason}")
    score_i = max(0, min(100, round(score)))
    if missing:
        names = ", ".join(f"{k} {v}" for k, v in list(missing.items())[:6])
        lines.insert(0, f"บันทึกหมวดที่ยังขาด: {names} แต่ยังให้คะแนนจากข้อความที่มี")
    if not findings and has_content:
        explanation = NO_ISSUE_TEXT[key]
        if missing:
            explanation = f"{lines[0]} {explanation}"
        return PartScore(
            key=key,
            label=PART_LABELS[key],
            score=100,
            explanation=explanation,
            findings=[],
        )
    if not findings and not has_content:
        return PartScore(
            key=key,
            label=PART_LABELS[key],
            score=0,
            explanation="ร่างยังไม่มีเนื้อหาให้ตรวจในด้านนี้",
            findings=[],
        )
    explanation = " ".join(lines) if lines else NO_ISSUE_TEXT[key]
    if score_i == 0 and not explanation.strip():
        explanation = "พบหลายประเด็นจึงหักคะแนนจนเหลือ 0 ในด้านนี้"
    return PartScore(
        key=key,
        label=PART_LABELS[key],
        score=score_i,
        explanation=explanation,
        findings=findings,
    )


def _guard_nonzero_panel(
    legal: PartScore,
    lock_in: PartScore,
    project: PartScore,
) -> tuple[PartScore, PartScore, PartScore]:
    """A draft with content must not return three unexplained zeros."""
    parts = (legal, lock_in, project)
    if not all(part.score == 0 for part in parts):
        return parts
    if any(part.explanation.strip() for part in parts):
        return parts
    note = "ร่างมีเนื้อหาแต่ยังสรุปคะแนนไม่ได้ครบ จึงไม่ให้ 0 ทั้งแผงโดยไม่มีคำอธิบาย"
    return tuple(replace(part, score=40, explanation=note) for part in parts)


def _weighted_total(legal: PartScore, lock_in: PartScore, project: PartScore) -> int:
    total = (
        legal.score * PART_WEIGHTS[PART_LEGAL]
        + lock_in.score * PART_WEIGHTS[PART_LOCK_IN]
        + project.score * PART_WEIGHTS[PART_PROJECT]
    )
    return max(0, min(100, round(total)))


def _summary_sentence(
    legal: PartScore,
    lock_in: PartScore,
    project: PartScore,
    missing: dict[str, str],
) -> str:
    ranked = sorted(
        (legal, lock_in, project),
        key=lambda part: (part.score, -PART_WEIGHTS[part.key]),
    )
    weakest = ranked[0]
    prefix = ""
    if missing:
        prefix = f"ยังขาดหมวด {', '.join(list(missing)[:4])} แต่ยังให้คะแนนจากข้อความที่มี "
    if weakest.score >= 90 and all(part.score >= 90 for part in (legal, lock_in, project)):
        return prefix + (
            "ทั้งสามด้านได้คะแนนสูงใกล้เคียงกัน ไม่มีด้านใดดึงคะแนนรวมลงอย่างเด่นชัด"
        )
    return prefix + (
        f"คะแนนรวมถูกดึงลงจาก{weakest.label} ({weakest.score}/100) มากที่สุด"
    )


def _quote(text: str, needle: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return needle[:180]
    idx = raw.find(needle) if needle else -1
    if idx < 0:
        return raw[:180]
    start = max(0, idx - 20)
    return raw[start : idx + max(len(needle), 80)][:280]


def _dedupe_findings(findings: list[AnalyzerFinding]) -> list[AnalyzerFinding]:
    seen: set[tuple[str, str]] = set()
    unique: list[AnalyzerFinding] = []
    for item in findings:
        key = (item.reason, item.source_quote[:80])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique
