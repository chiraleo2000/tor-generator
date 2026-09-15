"""Base agent class for TOR section drafting.

Defines the protocol / abstract base that all 10 specialized drafting agents
implement. Provides shared utilities for building LLM messages, incorporating
RAG context, and handling validation feedback on retry.

Requirements: 12.1, 16.5
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.llm_tokens import DRAFT_MAX_TOKENS, clamp_max_tokens
from app.orchestrator.state import RAGChunk, ValidationFinding
from app.providers.base import LLMProvider, LLMResponse
from app.services.staged_prompts import (
    COMPOSE_SECTION_INSTRUCTION,
    SECTION_ANALYZE_SYSTEM,
    analyze_notes,
    attach_analysis,
)
from app.domain.section_prompts import core_system_prompt, section_prompt
from app.services.thai_draft import (
    MIN_SANITIZED_THAI_CHARS,
    SUBSTANCE_RULES,
    THAI_ONLY_RULES,
    attach_thai_only,
    detect_unauthorized_english,
    official_tor_style_block,
    sanitize_unauthorized_english,
    thai_char_count,
)

logger = logging.getLogger(__name__)

THAI_FORMAL_REGISTER_PREAMBLE = core_system_prompt()


def formal_register(category: str | None = None, section_key: str | None = None) -> str:
    """Preamble plus official TOR style rules for a procurement category."""
    extra = section_prompt(category, section_key or "")
    body = THAI_FORMAL_REGISTER_PREAMBLE + official_tor_style_block(category, section_key)
    if extra:
        body += "\n" + extra
    body += SUBSTANCE_RULES + THAI_ONLY_RULES
    return body


def _format_input_entry(key: str, value: Any) -> list[str]:
    if isinstance(value, list):
        lines = [f"- {key}:"]
        lines.extend(f"  • {item}" for item in value)
        return lines
    if isinstance(value, dict):
        lines = [f"- {key}:"]
        lines.extend(f"  • {sub_key}: {sub_val}" for sub_key, sub_val in value.items())
        return lines
    return [f"- {key}: {value}"]


class BaseDraftingAgent(ABC):
    """Abstract base class for specialized TOR section drafting agents.

    Each concrete agent defines:
    - section_key: The TOR section this agent handles (e.g. "s1")
    - section_name_th: Thai name of the section
    - section_name_en: English name for logging/debugging
    - system_prompt: Section-specific LLM system prompt (in Thai formal register)

    The base class provides the shared `draft()` flow:
    1. Build system message with section-specific prompt
    2. Build user message from user_input + RAG context + feedback
    3. Analyze notes, then compose the section via the LLM
    4. Return the generated content

    Subclasses MUST implement `get_system_prompt()` and MAY override
    `build_user_message()` for section-specific input formatting.
    """

    section_key: str
    section_name_th: str
    section_name_en: str

    @abstractmethod
    def get_system_prompt(self, category: str | None = None) -> str:
        """Return the full system prompt for this agent.

        The prompt MUST be in formal Thai (ภาษาราชการ) and include
        section-specific guidance, required elements, and examples.

        Returns:
            The system prompt string.
        """
        ...

    def build_user_message(
        self,
        user_input: dict[str, Any],
        rag_chunks: list[RAGChunk],
        template: dict[str, Any] | None = None,
        validation_findings: list[ValidationFinding] | None = None,
        human_feedback: str | None = None,
    ) -> str:
        """Build the user message from available context.

        Assembles the user message incorporating:
        - User-provided input data from the wizard step
        - RAG-retrieved legal/regulatory context
        - Template guidance (if available)
        - Validation feedback from prior attempts (on retry)
        - Human feedback (if re-draft was requested)

        Subclasses MAY override this to format section-specific inputs.

        Args:
            user_input: User-provided form data for this section.
            rag_chunks: Retrieved knowledge base chunks.
            template: Template guidance for the section (optional).
            validation_findings: Rule Engine findings from prior attempt (optional).
            human_feedback: Human reviewer's feedback (optional).

        Returns:
            Formatted user message string.
        """
        parts: list[str] = []

        draft_fields = user_input.get("current_draft_fields")
        revision = user_input.get("revision_instruction")
        is_redraft = bool(user_input.get("redraft"))
        base_input = {
            key: value
            for key, value in user_input.items()
            if key
            not in {
                "current_draft_fields",
                "revision_instruction",
                "redraft",
                "focus_sub_key",
                "current_draft",
                "user_feedback",
                "human_feedback",
            }
        }

        # Section: User input
        parts.append("=== ข้อมูลจากผู้ใช้ ===")
        parts.append(self._format_user_input(base_input))

        if isinstance(draft_fields, dict) and any(
            str(value or "").strip() for value in draft_fields.values()
        ):
            parts.append(
                "\n=== ร่างปัจจุบันในหมวดนี้ "
                "(ต้องคงสาระที่ผู้ใช้แก้แล้ว และเติมส่วนที่ยังว่างให้ครบจากเอกสารขั้นที่ ๐) ==="
            )
            for key, value in draft_fields.items():
                text = str(value or "").strip()
                parts.append(f"[{key}]\n{text or '(ว่าง — ต้องเติม)'}")
        feedback_text = str(
            user_input.get("user_feedback") or user_input.get("human_feedback") or ""
        ).strip()
        if feedback_text:
            parts.append(
                "\n=== ความคิดเห็นจากผู้ใช้ (ต้องปฏิบัติตามอย่างเคร่งครัด — แก้เฉพาะหมวดนี้) ==="
            )
            parts.append(feedback_text)
        if is_redraft:
            parts.append(
                "\n=== โหมดร่างใหม่ ===\n"
                "เขียนข้อความใหม่ทั้งหมดของหมวดนี้ให้ต่างจากร่างปัจจุบันอย่างชัดเจน "
                "ห้ามคัดลอกร่างเดิมมาวางซ้ำทั้งก้อน หรือแก้เพียงคำสองคำ "
                "ห้ามแก้หมวดอื่น"
            )
        if revision and str(revision).strip():
            parts.append("\n=== คำสั่งปรับปรุงร่าง ===")
            parts.append(str(revision).strip())

        # Section: RAG context (if available)
        if rag_chunks:
            parts.append("\n=== บริบทจากฐานความรู้กฎหมาย ===")
            # Limit to top-8 chunks and 1500 chars each to keep prompt under context window
            for i, chunk in enumerate(rag_chunks[:8], 1):
                source = chunk.get("source_document", "ไม่ระบุแหล่งที่มา")
                text = (chunk.get("text", "") or "")[:1500]
                parts.append(f"\n[อ้างอิง {i}] แหล่งที่มา: {source}")
                parts.append(text)

        # Section: Template guidance (if available)
        if template:
            guidance = template.get("placeholder_guidance", {}).get(self.section_key)
            if guidance:
                parts.append("\n=== แนวทางจากแม่แบบ ===")
                parts.append(str(guidance))

        # Section: Validation feedback (on retry)
        if validation_findings:
            parts.append("\n=== ข้อเสนอแนะจากการตรวจสอบครั้งก่อน (กรุณาแก้ไข) ===")
            for finding in validation_findings:
                severity = finding.get("severity", "warning")
                message = finding.get("message", "")
                correction = finding.get("recommended_correction", "")
                parts.append(f"- [{severity}] {message}")
                if correction:
                    parts.append(f"  แนวทางแก้ไข: {correction}")

        # Section: Human feedback (on re-draft request) — skip if already shown above
        if human_feedback and str(human_feedback).strip() != feedback_text:
            parts.append("\n=== ความคิดเห็นจากผู้ตรวจสอบ ===")
            parts.append(human_feedback)

        # Final instruction
        parts.append(
            f"\n=== คำสั่ง ===\n"
            f"กรุณาร่างเนื้อหาสำหรับส่วน «{self.section_name_th}» "
            f"โดยใช้ข้อมูลข้างต้นเป็นพื้นฐาน "
            f"เขียนเป็นภาษาไทยเท่านั้นด้วยภาษาราชการ "
            f"ให้ครบถ้วน ถูกต้องตามกฎหมาย และสอดคล้องกับบริบท"
        )

        return "\n".join(parts)

    def _format_user_input(self, user_input: dict[str, Any]) -> str:
        """Format user input dict as readable text for the LLM.

        Args:
            user_input: Dictionary of user-provided form fields.

        Returns:
            Formatted string representation.
        """
        if not user_input:
            return "(ไม่มีข้อมูลจากผู้ใช้)"

        lines: list[str] = []
        for key, value in user_input.items():
            if value is None or value == "":
                continue
            lines.extend(_format_input_entry(key, value))
        return "\n".join(lines) if lines else "(ไม่มีข้อมูลจากผู้ใช้)"

    async def draft(
        self,
        llm: LLMProvider,
        user_input: dict[str, Any],
        rag_chunks: list[RAGChunk] | None = None,
        template: dict[str, Any] | None = None,
        validation_findings: list[ValidationFinding] | None = None,
        human_feedback: str | None = None,
        **kwargs,
    ) -> str:
        """Generate a TOR section draft using the LLM.

        This is the main entry point called by the llm_draft orchestrator node.

        Args:
            llm: The LLM provider instance (from ProviderFactory).
            user_input: User-provided form data for this section.
            rag_chunks: Retrieved knowledge base chunks (may be empty).
            template: Template guidance for the section (optional).
            validation_findings: Rule Engine findings from prior attempt (optional).
            human_feedback: Human reviewer's feedback (optional).
            **kwargs: Additional LLM parameters (temperature, max_tokens, etc.)

        Returns:
            Generated draft content as a string.

        Raises:
            TimeoutError: If LLM invocation exceeds configured timeout.
            ConnectionError: If LLM provider is unreachable.
        """
        category = None
        if isinstance(user_input, dict):
            raw = user_input.get("project_type") or user_input.get("category")
            category = raw if isinstance(raw, str) else None
        try:
            system_prompt = self.get_system_prompt(category=category)
        except TypeError:
            system_prompt = self.get_system_prompt()
        user_message = self.build_user_message(
            user_input=user_input,
            rag_chunks=rag_chunks or [],
            template=template,
            validation_findings=validation_findings,
            human_feedback=human_feedback,
        )
        notes = await analyze_notes(llm, user_message, SECTION_ANALYZE_SYSTEM)
        compose_user = attach_analysis(
            user_message, notes, COMPOSE_SECTION_INSTRUCTION
        )
        system_prompt = attach_thai_only(system_prompt)
        compose_user = attach_thai_only(compose_user)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": compose_user},
        ]

        logger.info(
            "Agent [%s] invoking LLM for section=%s",
            self.section_name_en,
            self.section_key,
        )

        from app.llm_tokens import live_context_window
        from app.providers.model_capabilities import (
            compose_thinking_enabled,
            current_capabilities,
            filter_llm_kwargs,
        )
        from app.services.thai_draft import polish_export_text, reject_intake_echo

        def _finish(raw: str) -> str:
            polished = polish_export_text(raw)
            intake = ""
            if isinstance(user_input, dict):
                blob = user_input.get("_project_intake")
                if isinstance(blob, str):
                    intake = blob
                elif isinstance(blob, dict):
                    intake = str(blob.get("content") or "")
                if not intake:
                    slots = user_input.get("slot_map")
                    if isinstance(slots, dict):
                        pack = slots.get("_project_intake")
                        if isinstance(pack, dict):
                            intake = str(pack.get("content") or "")
                        elif isinstance(pack, str):
                            intake = pack
            if intake:
                polished = reject_intake_echo(polished, intake)
            return polished

        caps = current_capabilities()
        redraft = bool(isinstance(user_input, dict) and user_input.get("redraft"))
        llm_kwargs = {
            "temperature": 0.55 if redraft else 0.3,
            "max_tokens": DRAFT_MAX_TOKENS,
        }
        llm_kwargs.update(kwargs)
        llm_kwargs.pop("disable_thinking", None)
        llm_kwargs["enable_thinking"] = compose_thinking_enabled(caps.provider)
        llm_kwargs["max_tokens"] = clamp_max_tokens(
            compose_user,
            int(llm_kwargs.get("max_tokens") or DRAFT_MAX_TOKENS),
            context_window=live_context_window(),
            system=system_prompt,
        )
        llm_kwargs = filter_llm_kwargs(caps.provider, llm_kwargs)

        response: LLMResponse = await llm.invoke(messages, **llm_kwargs)
        content = str(response.content or "")
        if not content.strip():
            logger.warning(
                "Agent [%s] empty draft; retrying once",
                self.section_name_en,
            )
            response = await llm.invoke(messages, **llm_kwargs)
            content = str(response.content or "")
        hits = detect_unauthorized_english(content)
        if hits:
            logger.warning(
                "Agent [%s] draft had unauthorized English %s; retrying once",
                self.section_name_en,
                hits[:12],
            )
            response = await llm.invoke(messages, **llm_kwargs)
            content = str(response.content or "")
            hits = detect_unauthorized_english(content)
        if hits:
            cleaned = sanitize_unauthorized_english(content)
            if thai_char_count(cleaned) >= MIN_SANITIZED_THAI_CHARS:
                logger.warning(
                    "Agent [%s] sanitized unauthorized English %s",
                    self.section_name_en,
                    hits[:12],
                )
                return _finish(cleaned)
            logger.warning(
                "Agent [%s] retry still had unauthorized English; keeping sanitized text",
                self.section_name_en,
            )
            return _finish(cleaned or content)

        logger.info(
            "Agent [%s] completed draft: %d chars, usage=%s",
            self.section_name_en,
            len(content),
            response.usage,
        )

        return _finish(content)
