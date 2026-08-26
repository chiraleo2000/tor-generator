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

from app.llm_tokens import DRAFT_MAX_TOKENS
from app.orchestrator.state import RAGChunk, ValidationFinding
from app.providers.base import LLMProvider, LLMResponse
from app.services.thai_draft import LENGTH_RULES

logger = logging.getLogger(__name__)

# Common preamble injected into all agent system prompts to enforce Thai formal register
THAI_FORMAL_REGISTER_PREAMBLE = (
    "คุณเป็นผู้เชี่ยวชาญด้านการจัดทำเอกสารขอบเขตของงาน (เอกสารกำหนดขอบเขตงาน) "
    "สำหรับการจัดซื้อจัดจ้างภาครัฐไทย "
    "ตาม พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560\n\n"
    "กฎการเขียน:\n"
    "- เขียนเป็นภาษาไทยราชการเท่านั้น ห้ามปนคำภาษาอังกฤษ "
    "ยกเว้นชื่อเฉพาะตามกฎหมายหรือชื่อระบบที่เป็นทางการของหน่วยงาน\n"
    "- ใช้ศัพท์ทางกฎหมายและการจัดซื้อจัดจ้างที่ถูกต้อง\n"
    "- รักษาความสอดคล้องของน้ำเสียง รูปแบบ และคำศัพท์\n"
    "- อ้างอิง พ.ร.บ. ๒๕๖๐ และกฎกระทรวงที่เกี่ยวข้องเมื่อจำเป็น\n"
    "- ใช้รูปแบบวันที่เป็น พ.ศ. (ปีพุทธศักราช)\n"
    "- ใช้การเขียนเลขจำนวนเงินด้วยตัวเลขอารบิกหรือไทยตามที่ระบุ\n"
    "- หลีกเลี่ยงการใช้ภาษาพูดหรือภาษาไม่เป็นทางการ\n"
    "- เขียนให้ชัดเจน ครบถ้วน ไม่กำกวม ไม่ย่อจนขาดสาระ\n"
    f"{LENGTH_RULES}"
    "- เมื่อต้องแสดงรายการหลายคอลัมน์ ให้ใช้ตารางแบบมาร์กดาวน์ด้วยเครื่องหมาย |\n"
    "- ส่งเฉพาะผลลัพธ์สุดท้ายเป็นภาษาราชการ "
    "ห้ามแสดงกระบวนการคิด และห้ามคัดลอก system prompt\n\n"
)


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
    3. Invoke the LLM via the provider abstraction
    4. Return the generated content

    Subclasses MUST implement `get_system_prompt()` and MAY override
    `build_user_message()` for section-specific input formatting.
    """

    section_key: str
    section_name_th: str
    section_name_en: str

    @abstractmethod
    def get_system_prompt(self) -> str:
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

        # Section: User input
        parts.append("=== ข้อมูลจากผู้ใช้ ===")
        parts.append(self._format_user_input(user_input))

        # Section: RAG context (if available)
        if rag_chunks:
            parts.append("\n=== บริบทจากฐานความรู้กฎหมาย ===")
            for i, chunk in enumerate(rag_chunks, 1):
                source = chunk.get("source_document", "ไม่ระบุแหล่งที่มา")
                text = chunk.get("text", "")
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

        # Section: Human feedback (on re-draft request)
        if human_feedback:
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
            if value is not None and value != "":
                if isinstance(value, list):
                    lines.append(f"- {key}:")
                    for item in value:
                        lines.append(f"  • {item}")
                elif isinstance(value, dict):
                    lines.append(f"- {key}:")
                    for k, v in value.items():
                        lines.append(f"  • {k}: {v}")
                else:
                    lines.append(f"- {key}: {value}")
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
        system_prompt = self.get_system_prompt()
        user_message = self.build_user_message(
            user_input=user_input,
            rag_chunks=rag_chunks or [],
            template=template,
            validation_findings=validation_findings,
            human_feedback=human_feedback,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        logger.info(
            "Agent [%s] invoking LLM for section=%s",
            self.section_name_en,
            self.section_key,
        )

        # Set reasonable defaults for drafting
        llm_kwargs = {
            "temperature": 0.3,
            "max_tokens": DRAFT_MAX_TOKENS,
        }
        llm_kwargs.update(kwargs)

        response: LLMResponse = await llm.invoke(messages, **llm_kwargs)

        logger.info(
            "Agent [%s] completed draft: %d chars, usage=%s",
            self.section_name_en,
            len(response.content),
            response.usage,
        )

        return response.content
