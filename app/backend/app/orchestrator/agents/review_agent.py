"""Review Agent — Cross-section TOR consistency analysis and suggestions.

The ReviewAgent (Agent R) is a specialized agent that differs from the
section-specific drafting agents. Instead of generating content for a single
section, it analyzes the full assembled TOR document for cross-section
consistency, compliance gaps, clarity issues, and completeness problems.

It produces categorized suggestions matching the Suggestion model schema:
- compliance: Legal/regulatory compliance issues
- clarity: Language clarity and precision improvements
- completeness: Missing information or underdeveloped areas
- consistency: Cross-section contradictions or misalignments

Requirements: 10.2, 12.4
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.llm_tokens import (
    REVIEW_CONTEXT_WINDOW,
    REVIEW_MAX_TOKENS,
    clamp_max_tokens,
    estimate_tokens,
)
from app.orchestrator.agents.base import THAI_FORMAL_REGISTER_PREAMBLE
from app.orchestrator.section_state import SECTION_NAMES_TH, SECTION_ORDER
from app.providers.base import LLMProvider
from app.providers.structured_invoke import invoke_with_schema
from app.schemas.llm_structured import ReviewSuggestionsResult, json_schema_for

logger = logging.getLogger(__name__)

# Maximum suggestions the ReviewAgent should generate per invocation
MAX_SUGGESTIONS = 20
MIN_SUGGESTIONS = 3


@dataclass
class ReviewSuggestion:
    """A structured suggestion from the ReviewAgent.

    Maps directly to the Suggestion ORM model fields for persistence.

    Attributes:
        category: One of "compliance", "clarity", "completeness", "consistency".
        section_key: The affected TOR section (e.g. "s1", "s4").
        current_text: The problematic text found in the TOR.
        suggested_text: The recommended replacement text.
        predicted_score_improvement: Estimated quality score increase (0.0-10.0).
    """

    category: str  # compliance | clarity | completeness | consistency
    section_key: str
    current_text: str
    suggested_text: str
    predicted_score_improvement: float


@dataclass
class ReviewResult:
    """Complete result from the ReviewAgent analysis.

    Attributes:
        suggestions: List of categorized suggestions.
        overall_assessment: Brief overall assessment text.
        section_scores: Optional per-section quality indicators.
    """

    suggestions: list[ReviewSuggestion] = field(default_factory=list)
    overall_assessment: str = ""
    section_scores: dict[str, float] = field(default_factory=dict)


# Deterministic cross-section consistency checks that don't require LLM
# These are fast checks that supplement the LLM-based review
CROSS_SECTION_CHECKS: list[dict[str, Any]] = [
    {
        "id": "budget_scope_alignment",
        "sections_required": ["s4", "s6"],
        "category": "consistency",
        "description": "งบประมาณต้องสอดคล้องกับขอบเขตงาน",
    },
    {
        "id": "timeline_deliverables_alignment",
        "sections_required": ["s4", "s5", "s8"],
        "category": "consistency",
        "description": "ระยะเวลาต้องสอดคล้องกับผลงานส่งมอบและงวดงาน",
    },
    {
        "id": "qualifications_complexity",
        "sections_required": ["s3", "s4", "s6"],
        "category": "consistency",
        "description": "คุณสมบัติต้องสอดคล้องกับความซับซ้อนและงบประมาณ",
    },
    {
        "id": "payment_schedule_scope",
        "sections_required": ["s4", "s8"],
        "category": "consistency",
        "description": "งวดงานต้องสอดคล้องกับขอบเขตงานและผลงานส่งมอบ",
    },
    {
        "id": "penalties_timeline",
        "sections_required": ["s5", "s10"],
        "category": "consistency",
        "description": "ค่าปรับต้องสอดคล้องกับระยะเวลาดำเนินการ",
    },
    {
        "id": "objectives_scope_alignment",
        "sections_required": ["s2", "s4"],
        "category": "completeness",
        "description": "วัตถุประสงค์ทุกข้อต้องมีงานรองรับในขอบเขตงาน",
    },
]

# One user-facing review; split internally when the packed TOR exceeds the window.
REVIEW_SECTION_BATCHES: tuple[tuple[str, ...], ...] = (
    ("s1", "s2", "s3", "s4"),
    ("s5", "s6", "s7", "s8"),
    ("s9", "s10", "s11", "s12", "s13"),
)
MAX_REVIEW_SECTION_CHARS = 100_000

REVIEW_SYSTEM_PROMPT = (
    THAI_FORMAL_REGISTER_PREAMBLE
    + "คุณเป็นผู้ตรวจเอกสาร TOR ภาครัฐไทยที่เข้มงวด "
    "หน้าที่คือวิจารณ์ร่าง ไม่ใช่ชื่นชมหรือรับทุกอย่างว่าผ่าน\n\n"
    "=== บทบาทของคุณ ===\n"
    "วิเคราะห์เอกสาร TOR ทั้งฉบับเทียบกับ:\n"
    "1. พระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. ๒๕๖๐ และระเบียบที่เกี่ยวข้อง (คลังกลาง)\n"
    "2. เอกสารที่เจ้าหน้าที่อัปโหลดหรือวางในขั้นที่ ๐ ของโครงการนี้เท่านั้น ห้ามใช้เอกสารโครงการอื่น\n"
    "3. ความสอดคล้องระหว่างหมวด ความครบถ้วน ความชัดเจน\n\n"
    "ห้ามสรุปว่าสมบูรณ์ถ้ายังมีช่องว่าง ตัวเลขไม่ตรง หรือไม่สอดคล้องกฎหมาย\n"
    "ตอบเป็นภาษาไทยราชการเท่านั้น\n\n"
    "=== รูปแบบผลลัพธ์ ===\n"
    "ตอบในรูปแบบ JSON object ที่มีคีย์ suggestions เป็น array ดังนี้:\n"
    "```json\n"
    '{ "suggestions": [\n'
    '  {\n'
    '    "category": "consistency|completeness|clarity|compliance",\n'
    '    "section_key": "s1|s2|...|s13",\n'
    '    "current_text": "ข้อความปัจจุบันที่มีปัญหา (ย่อหน้าหรือประโยค)",\n'
    '    "suggested_text": "ข้อความที่แนะนำให้แก้ไข",\n'
    '    "predicted_score_improvement": 1.0\n'
    '  }\n'
    "] }\n"
    "```\n\n"
    "=== กฎการให้คำแนะนำ ===\n"
    "- ให้คำแนะนำ 3-20 ข้อ เรียงจากสำคัญมากไปน้อย\n"
    "- predicted_score_improvement: 0.5-10.0\n"
    "- current_text: คัดลอกข้อความจริงจากเอกสาร (ไม่เกิน 200 ตัวอักษร)\n"
    "- suggested_text: ให้ข้อความทดแทนที่สมบูรณ์ พร้อมใช้งาน ยาวครบถ้วนตามภาษาราชการ\n"
    "- เน้นช่องว่างเทียบกฎหมายและความต้องการโครงการ\n"
    "- ตอบเป็น JSON เท่านั้น ไม่มีข้อความอื่นนอก JSON\n"
)


class ReviewAgent:
    """Agent R: Analyzes full assembled TOR for cross-section consistency.

    Unlike section-specific drafting agents (which extend BaseDraftingAgent),
    the ReviewAgent operates on the complete document to identify:
    - Cross-section inconsistencies
    - Compliance gaps
    - Clarity issues
    - Completeness problems

    It combines deterministic checks (rule-based, fast) with LLM-based
    analysis (thorough, context-aware) to produce actionable suggestions.

    Usage:
        agent = ReviewAgent()
        result = await agent.review(
            llm=provider_factory.get_llm("structured"),
            sections={"s1": "content...", "s2": "content..."},
            project_metadata={"budget": 5000000, "project_type": "it"},
        )
        for suggestion in result.suggestions:
            print(f"[{suggestion.category}] {suggestion.section_key}: ...")
    """

    def __init__(self) -> None:
        """Initialize the ReviewAgent."""
        self.section_name_en = "ReviewAgent"
        self.section_name_th = "ตัวแทนตรวจสอบ"

    async def review(
        self,
        llm: LLMProvider,
        sections: dict[str, str],
        project_metadata: dict[str, Any] | None = None,
        custom_requirements: str | None = None,
    ) -> ReviewResult:
        """Analyze full assembled TOR and generate categorized suggestions.

        Performs two passes:
        1. Deterministic checks — fast rule-based cross-section validation
        2. LLM analysis — deep contextual review using the language model

        Args:
            llm: The LLM provider instance for AI-based analysis.
            sections: Dict of section_key -> content for all completed sections.
            project_metadata: Optional project info (budget, type, timeline_days).
            custom_requirements: Optional user-uploaded requirements text for
                project-specific compliance checking.

        Returns:
            ReviewResult with categorized suggestions (3-20 items).
        """
        project_metadata = project_metadata or {}

        logger.info(
            "ReviewAgent starting analysis: %d sections, metadata_keys=%s",
            len(sections),
            list(project_metadata.keys()),
        )

        # Pass 1: Deterministic cross-section checks
        deterministic_suggestions = self._run_deterministic_checks(
            sections=sections,
            project_metadata=project_metadata,
        )

        # Pass 1b: Custom requirements checks (if provided)
        if custom_requirements and custom_requirements.strip():
            custom_suggestions = self._check_custom_requirements(
                sections=sections,
                requirements=custom_requirements,
            )
            deterministic_suggestions.extend(custom_suggestions)

        # Pass 2: LLM-based analysis
        llm_suggestions = await self._run_llm_review(
            llm=llm,
            sections=sections,
            project_metadata=project_metadata,
            custom_requirements=custom_requirements,
        )

        # Merge and deduplicate suggestions
        all_suggestions = self._merge_suggestions(
            deterministic_suggestions, llm_suggestions
        )

        # Enforce min/max bounds
        all_suggestions = all_suggestions[:MAX_SUGGESTIONS]

        # Build overall assessment
        assessment = self._build_assessment(sections, all_suggestions)

        logger.info(
            "ReviewAgent completed: %d suggestions generated "
            "(deterministic=%d, llm=%d)",
            len(all_suggestions),
            len(deterministic_suggestions),
            len(llm_suggestions),
        )

        return ReviewResult(
            suggestions=all_suggestions,
            overall_assessment=assessment,
        )

    def _run_deterministic_checks(
        self,
        sections: dict[str, str],
        project_metadata: dict[str, Any],
    ) -> list[ReviewSuggestion]:
        """Run fast deterministic cross-section consistency checks.

        These checks verify basic relationships between sections without
        needing the LLM. They catch common issues like:
        - Budget mentioned in scope but not in budget section
        - Deliverables in payment not matching scope
        - Timeline inconsistencies

        Args:
            sections: All completed TOR sections.
            project_metadata: Project metadata (budget, type, etc.)

        Returns:
            List of suggestions from deterministic checks.
        """
        suggestions: list[ReviewSuggestion] = []

        # Check: Budget/Scope alignment
        if "s4" in sections and "s6" in sections:
            scope_text = sections["s4"]
            budget_text = sections["s6"]

            # If scope mentions specific quantities/items not reflected in budget
            if len(scope_text) > 500 and len(budget_text) < 200:
                suggestions.append(ReviewSuggestion(
                    category="completeness",
                    section_key="s6",
                    current_text=budget_text[:150] if budget_text else "(งบประมาณว่างเปล่า)",
                    suggested_text=(
                        "ควรเพิ่มรายละเอียดการจัดสรรงบประมาณให้สอดคล้อง"
                        "กับขอบเขตงานที่ระบุไว้อย่างละเอียด"
                    ),
                    predicted_score_improvement=3.0,
                ))

        # Check: Payment schedule references deliverables from scope
        if "s8" in sections and "s4" in sections:
            payment_text = sections["s8"]
            scope_text = sections["s4"]
            scope_has_deliverables = "ผลงานส่งมอบ" in scope_text
            payment_mentions_deliverable = (
                "ผลงานส่งมอบ" in payment_text
                or "deliverable" in payment_text.lower()
            )

            if scope_has_deliverables and not payment_mentions_deliverable:
                suggestions.append(ReviewSuggestion(
                    category="consistency",
                    section_key="s8",
                    current_text=payment_text[:150] if payment_text else "(งวดงานว่างเปล่า)",
                    suggested_text=(
                        "ควรระบุผลงานส่งมอบที่ชัดเจนในแต่ละงวดงาน "
                        "โดยอ้างอิงจากขอบเขตงานในส่วนที่ 4"
                    ),
                    predicted_score_improvement=2.5,
                ))

        # Check: Objectives should align with scope
        if "s2" in sections and "s4" in sections:
            objectives_text = sections["s2"]
            scope_text = sections["s4"]

            # Very basic check: if objectives is short relative to scope
            if len(objectives_text) < 100 and len(scope_text) > 300:
                suggestions.append(ReviewSuggestion(
                    category="completeness",
                    section_key="s2",
                    current_text=objectives_text[:150],
                    suggested_text=(
                        "ควรเพิ่มวัตถุประสงค์ให้ครอบคลุมขอบเขตงานทั้งหมด "
                        "ตามหลัก SMART (Specific, Measurable, Achievable, "
                        "Relevant, Time-bound)"
                    ),
                    predicted_score_improvement=2.0,
                ))

        # Check: Background should mention legal basis
        if "s1" in sections:
            background = sections["s1"]
            if "พ.ร.บ." not in background and "พระราชบัญญัติ" not in background:
                suggestions.append(ReviewSuggestion(
                    category="compliance",
                    section_key="s1",
                    current_text=background[:150],
                    suggested_text=(
                        "ควรอ้างอิง พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ "
                        "พ.ศ. 2560 หรือกฎหมายที่เกี่ยวข้องในส่วนความเป็นมา"
                    ),
                    predicted_score_improvement=2.0,
                ))

        # Check: Qualifications capital should match budget
        budget = project_metadata.get("budget")
        if budget and "s3" in sections:
            expected_capital = budget // 4
            qualifications = sections["s3"]
            capital_str = f"{expected_capital:,}"
            # Simple heuristic: if capital amount isn't mentioned
            if str(expected_capital) not in qualifications and capital_str not in qualifications:
                suggestions.append(ReviewSuggestion(
                    category="compliance",
                    section_key="s3",
                    current_text=qualifications[:150],
                    suggested_text=(
                        f"ควรระบุทุนจดทะเบียนชำระแล้วไม่น้อยกว่า "
                        f"{expected_capital:,.0f} บาท "
                        f"(งบประมาณ {budget:,.0f} ÷ 4)"
                    ),
                    predicted_score_improvement=4.0,
                ))

        # Check: Penalties section should mention rate
        if "s10" in sections:
            penalties = sections["s10"]
            if "ร้อยละ" not in penalties and "%" not in penalties:
                suggestions.append(ReviewSuggestion(
                    category="compliance",
                    section_key="s10",
                    current_text=penalties[:150],
                    suggested_text=(
                        "ควรระบุอัตราค่าปรับเป็นร้อยละต่อวัน "
                        "(0.01%-0.20% ตามระเบียบ) อย่างชัดเจน"
                    ),
                    predicted_score_improvement=3.5,
                ))

        return suggestions

    def _check_custom_requirements(
        self,
        sections: dict[str, str],
        requirements: str,
    ) -> list[ReviewSuggestion]:
        """Check TOR against user-uploaded custom requirements.

        Uses basic keyword/phrase matching to verify that key terms from
        the requirements document appear in the TOR sections.

        Args:
            sections: All completed TOR sections.
            requirements: User-uploaded requirements text.

        Returns:
            List of suggestions for unaddressed requirements.
        """
        suggestions: list[ReviewSuggestion] = []
        all_tor_text = " ".join(sections.values()).lower()

        # Split requirements into paragraphs and check each
        paragraphs = [
            p.strip() for p in requirements.split("\n") if len(p.strip()) > 20
        ]

        for paragraph in paragraphs[:20]:  # Limit to 20 paragraphs
            # Extract key terms (words > 4 chars) from this paragraph
            words = [w for w in paragraph.split() if len(w) > 4]
            if not words:
                continue

            # Check if at least 30% of key terms appear in TOR
            matched = sum(1 for w in words if w.lower() in all_tor_text)
            coverage = matched / len(words) if words else 0

            if coverage < 0.3:
                suggestions.append(ReviewSuggestion(
                    category="completeness",
                    section_key="s4",
                    current_text=paragraph[:150],
                    suggested_text=(
                        "ข้อกำหนดเพิ่มเติมนี้ยังไม่ถูกระบุใน TOR: "
                        f"'{paragraph[:100]}' — ควรเพิ่มเนื้อหาที่ตอบสนองข้อกำหนดนี้"
                    ),
                    predicted_score_improvement=2.0,
                ))

            if len(suggestions) >= 5:
                break

        return suggestions

    async def _run_llm_review(
        self,
        llm: LLMProvider,
        sections: dict[str, str],
        project_metadata: dict[str, Any],
        custom_requirements: str | None = None,
    ) -> list[ReviewSuggestion]:
        """Run LLM-based deep review of the full TOR document.

        Sends the full assembled TOR to the LLM with the review system prompt
        to get contexual cross-section analysis.

        Args:
            llm: LLM provider instance.
            sections: All completed sections.
            project_metadata: Project metadata for context.
            custom_requirements: Optional user-uploaded requirements text.

        Returns:
            List of suggestions from LLM analysis.
        """
        if not sections:
            return []

        extra = (custom_requirements or "").strip()
        collected: list[ReviewSuggestion] = []
        for subset in self._iter_review_batches(sections, project_metadata, extra):
            collected.extend(
                await self._invoke_review_suggestions(
                    llm, subset, project_metadata, extra
                )
            )
        return collected

    def _iter_review_batches(
        self,
        sections: dict[str, str],
        project_metadata: dict[str, Any],
        extra: str,
    ) -> list[dict[str, str]]:
        """One batch when the full TOR fits; otherwise groups then single sections."""
        keys = [key for key in SECTION_ORDER if key in sections]
        if not keys:
            return []
        full = {key: sections[key] for key in keys}
        if self._review_message_fits(full, project_metadata, extra):
            return [full]
        batches: list[dict[str, str]] = []
        for group in REVIEW_SECTION_BATCHES:
            subset = {key: sections[key] for key in group if key in sections}
            if not subset:
                continue
            if self._review_message_fits(subset, project_metadata, extra) or len(subset) == 1:
                batches.append(subset)
                continue
            for key, text in subset.items():
                batches.append({key: text})
        return batches

    def _review_message_fits(
        self,
        sections: dict[str, str],
        project_metadata: dict[str, Any],
        extra: str,
    ) -> bool:
        packed = self._compose_review_user_message(sections, project_metadata, extra)
        used = estimate_tokens(REVIEW_SYSTEM_PROMPT) + estimate_tokens(packed)
        return used + 2048 < REVIEW_CONTEXT_WINDOW

    def _compose_review_user_message(
        self,
        sections: dict[str, str],
        project_metadata: dict[str, Any],
        extra: str,
    ) -> str:
        body = self._build_review_user_message(sections, project_metadata)
        if not extra:
            return body
        return (
            f"{body}\n\n=== ข้อกำหนดเพิ่มเติมของโครงการ ===\n{extra[:16000]}\n\n"
            "ตรวจสอบว่า TOR สอดคล้องกับข้อกำหนดเพิ่มเติมเหล่านี้ด้วย "
            "โดยให้คำแนะนำหมวด compliance หรือ completeness"
        )

    async def _invoke_review_suggestions(
        self,
        llm: LLMProvider,
        sections: dict[str, str],
        project_metadata: dict[str, Any],
        extra: str,
    ) -> list[ReviewSuggestion]:
        user_message = self._compose_review_user_message(
            sections, project_metadata, extra
        )
        max_out = clamp_max_tokens(
            user_message,
            REVIEW_MAX_TOKENS,
            context_window=REVIEW_CONTEXT_WINDOW,
            system=REVIEW_SYSTEM_PROMPT,
        )
        messages = [
            {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        try:
            payload = await invoke_with_schema(
                llm,
                messages,
                json_schema_for(ReviewSuggestionsResult),
                "review_suggestions",
                temperature=0.2,
                max_tokens=max_out,
            )
            import json

            suggestions = self._parse_llm_suggestions(
                json.dumps(payload, ensure_ascii=False)
            )
            logger.info("LLM review produced %d suggestions", len(suggestions))
            return suggestions
        except Exception:
            logger.exception(
                "LLM review failed. Falling back to deterministic-only.",
            )
            return []

    def _build_review_user_message(
        self,
        sections: dict[str, str],
        project_metadata: dict[str, Any],
    ) -> str:
        """Build user message containing the full TOR for review.

        Args:
            sections: All completed TOR sections.
            project_metadata: Project metadata.

        Returns:
            Formatted user message string.
        """
        parts: list[str] = []

        # Project metadata
        parts.append("=== ข้อมูลโครงการ ===")
        if project_metadata.get("budget"):
            parts.append(f"งบประมาณ: {project_metadata['budget']:,.0f} บาท")
        if project_metadata.get("project_type"):
            parts.append(f"ประเภทโครงการ: {project_metadata['project_type']}")
        if project_metadata.get("timeline_days"):
            parts.append(f"ระยะเวลา: {project_metadata['timeline_days']} วัน")
        req = str(project_metadata.get("requirements") or "").strip()
        if req:
            parts.append("=== ความต้องการและเอกสารขั้นที่ ๐ ของโครงการนี้เท่านั้น ===")
            parts.append(req[:24000])
            parts.append("")
        legal = str(project_metadata.get("legal_context") or "").strip()
        if legal:
            parts.append("=== กฎหมายและระเบียบจากคลังกลาง ===")
            parts.append(legal[:20000])
            parts.append("")

        # Full TOR sections — keep long official drafts; cap only runaway blobs
        parts.append("=== เอกสาร TOR ฉบับเต็ม ===")
        for key in SECTION_ORDER:
            if key not in sections:
                continue
            section_name = SECTION_NAMES_TH.get(key, key)
            parts.append(f"\n### ส่วนที่ {key}: {section_name}")
            content = sections[key]
            if len(content) > MAX_REVIEW_SECTION_CHARS:
                content = content[:MAX_REVIEW_SECTION_CHARS] + "\n... (ตัดทอนส่วนท้าย)"
            parts.append(content)
        parts.append("")

        # Analysis instruction
        parts.append(
            "=== คำสั่ง ===\n"
            "วิจารณ์ร่างอย่างเข้มงวด เทียบกฎหมายและความต้องการโครงการ "
            "ห้ามรับทุกอย่างว่าผ่าน ให้คำแนะนำเป็น JSON ตาม system prompt\n"
            "เน้นช่องว่าง ตัวเลขไม่ตรง และหมวดที่ยังไม่ครบ"
        )

        return "\n".join(parts)

    async def comment_on_draft(
        self,
        llm: LLMProvider,
        question: str,
        sections: dict[str, str],
        project_metadata: dict[str, Any] | None = None,
        findings: list[str] | None = None,
    ) -> str:
        """Thai critical comment on the assembled TOR (high token budget)."""
        body = self._build_review_user_message(sections, project_metadata or {})
        if findings:
            body += "\n=== ประเด็นจากกฎระเบียบ ===\n" + "\n".join(findings[:12])
        body += (
            f"\n=== คำถามเจ้าหน้าที่ ===\n{question.strip()}\n"
            "ตอบเป็นภาษาไทยราชการ ประเมินว่าร่างยังขาดอะไร "
            "เทียบกฎหมายและความต้องการโครงการ แล้วเสนอวิธีแก้เป็นข้อ ๆ "
            "ห้ามสรุปว่าผ่านถ้ายังมีช่องว่าง"
        )
        system = (
            THAI_FORMAL_REGISTER_PREAMBLE
            + "คุณเป็นผู้ตรวจ TOR ที่เข้มงวด ห้ามรับทุกอย่างว่าผ่าน ตอบภาษาไทยเท่านั้น"
        )
        max_out = clamp_max_tokens(
            body,
            REVIEW_MAX_TOKENS,
            context_window=REVIEW_CONTEXT_WINDOW,
            system=system,
        )
        response = await llm.invoke(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": body},
            ],
            temperature=0.2,
            max_tokens=max_out,
        )
        return str(getattr(response, "content", "") or "").strip()

    def _parse_llm_suggestions(self, llm_output: str) -> list[ReviewSuggestion]:
        """Parse LLM JSON output into ReviewSuggestion objects.

        Handles:
        - JSON wrapped in markdown code blocks
        - Malformed JSON (returns empty list)
        - Invalid suggestion fields (skips invalid items)

        Args:
            llm_output: Raw LLM response text.

        Returns:
            List of parsed ReviewSuggestion objects.
        """
        import json

        # Strip markdown code blocks if present
        text = llm_output.strip()
        if text.startswith("```"):
            # Remove opening ```json or ``` and closing ```
            lines = text.split("\n")
            # Remove first line (```json) and last line (```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON array in the text
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1 and end > start:
                try:
                    data = json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    logger.warning("Failed to parse LLM review output as JSON")
                    return []
            else:
                logger.warning("No JSON array found in LLM review output")
                return []

        if isinstance(data, dict):
            raw_items = data.get("suggestions")
            data = raw_items if isinstance(raw_items, list) else []
        if not isinstance(data, list):
            logger.warning("LLM review output is not a JSON array")
            return []

        suggestions: list[ReviewSuggestion] = []
        valid_categories = {"compliance", "clarity", "completeness", "consistency"}

        for item in data:
            if not isinstance(item, dict):
                continue

            category = item.get("category", "")
            section_key = item.get("section_key", "")
            current_text = item.get("current_text", "")
            suggested_text = item.get("suggested_text", "")
            score_improvement = item.get("predicted_score_improvement", 1.0)

            # Validate fields
            if category not in valid_categories:
                continue
            if not section_key or section_key not in [f"s{i}" for i in range(1, 14)]:
                continue
            if not current_text or not suggested_text:
                continue

            # Clamp score improvement
            try:
                score_improvement = float(score_improvement)
                score_improvement = max(0.5, min(10.0, score_improvement))
            except (TypeError, ValueError):
                score_improvement = 1.0

            suggestions.append(ReviewSuggestion(
                category=category,
                section_key=section_key,
                current_text=current_text[:500],  # Truncate if too long
                suggested_text=suggested_text[:1000],
                predicted_score_improvement=score_improvement,
            ))

        return suggestions

    def _merge_suggestions(
        self,
        deterministic: list[ReviewSuggestion],
        llm_based: list[ReviewSuggestion],
    ) -> list[ReviewSuggestion]:
        """Merge and deduplicate suggestions from both passes.

        Deterministic suggestions take priority (they're rule-validated).
        LLM suggestions are added after, with deduplication based on
        section_key + category overlap.

        Args:
            deterministic: Suggestions from rule-based checks.
            llm_based: Suggestions from LLM analysis.

        Returns:
            Merged list, sorted by predicted_score_improvement descending.
        """
        # Track existing (section_key, category) pairs from deterministic
        existing_keys = {
            (s.section_key, s.category) for s in deterministic
        }

        merged = list(deterministic)

        for suggestion in llm_based:
            # Skip if we already have a suggestion for same section+category
            key = (suggestion.section_key, suggestion.category)
            if key not in existing_keys:
                merged.append(suggestion)
                existing_keys.add(key)

        # Sort by predicted score improvement (highest first)
        merged.sort(key=lambda s: s.predicted_score_improvement, reverse=True)

        return merged

    def _build_assessment(
        self,
        sections: dict[str, str],
        suggestions: list[ReviewSuggestion],
    ) -> str:
        """Build a brief overall assessment text.

        Args:
            sections: Completed sections.
            suggestions: Generated suggestions.

        Returns:
            Thai-language assessment summary.
        """
        total_sections = len(sections)
        total_suggestions = len(suggestions)

        # Count by category
        category_counts: dict[str, int] = {}
        for s in suggestions:
            category_counts[s.category] = category_counts.get(s.category, 0) + 1

        parts: list[str] = []
        parts.append(
            f"ตรวจสอบเอกสาร TOR จำนวน {total_sections} ส่วน "
            f"พบข้อเสนอแนะ {total_suggestions} รายการ"
        )

        if category_counts:
            breakdown = ", ".join(
                f"{cat}: {count}" for cat, count in sorted(category_counts.items())
            )
            parts.append(f"แบ่งตามประเภท: {breakdown}")

        if total_suggestions == 0:
            parts.append(
                "ยังต้องเทียบกับกฎหมายและความต้องการโครงการอีกครั้ง "
                "ไม่ถือว่าผ่านโดยอัตโนมัติ"
            )
        elif total_suggestions <= 5:
            parts.append("มีประเด็นที่ต้องแก้ก่อนถือว่าครบ")
        else:
            parts.append("ควรทบทวนและปรับปรุงตามข้อเสนอแนะเพื่อให้เอกสารครบ")

        return " ".join(parts)
