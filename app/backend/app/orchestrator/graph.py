"""LangGraph StateGraph orchestrator for TOR section drafting.

Implements the drafting workflow as a directed graph:
    validate_input → retrieve_context → llm_draft → rule_guardrail
        → (pass) human_review → finalize
        → (fail & retries < max) llm_draft (retry with feedback)
        → (fail & retries >= max) human_review (with warnings)

Conditional routing logic:
- After rule_guardrail: route based on quality_score and retry_count
- After human_review: route to finalize (approved) or llm_draft (re-draft requested)

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.8, 12.2, 12.5, 12.6, 12.7
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Literal

from langgraph.graph import END, StateGraph

from app.domain.tor_sections import (
    MANDATORY_HUMAN_REVIEW_SECTIONS,
    TOR_SECTION_LABELS_BILINGUAL,
)
from app.orchestrator.agents.registry import get_agent_for_section
from app.orchestrator.state import TORDraftState

if TYPE_CHECKING:
    from app.rule_engine.engine import RuleEngine

logger = logging.getLogger(__name__)

# Guardrail threshold: quality_score >= 70 passes (maps to 0.7 requirement)
GUARDRAIL_THRESHOLD = 70

# Default configuration
DEFAULT_MAX_RETRIES = 3

# LLM timeout per invocation in seconds (Requirement 12.6)
LLM_TIMEOUT_SECONDS = 60

# Maximum allowed timeout (Requirement 12.6)
MAX_TIMEOUT_SECONDS = 300

SECTION_NAMES: dict[str, str] = dict(TOR_SECTION_LABELS_BILINGUAL)

# Agent system prompts mapping per TOR section (used until agents/ module is available)
AGENT_SYSTEM_PROMPTS: dict[str, str] = {
    "s1": (
        "คุณเป็น AI ผู้เชี่ยวชาญด้านการจัดทำ TOR ภาครัฐไทย ส่วนที่ 1: ความเป็นมา "
        "หน้าที่ของคุณคือร่างเนื้อหาส่วนความเป็นมาของ TOR โดยอธิบายบริบทของโครงการ "
        "ปัญหาที่ต้องการแก้ไข และเหตุผลความจำเป็นในการจัดซื้อจัดจ้าง "
        "ใช้ภาษาราชการไทยที่เป็นทางการ"
    ),
    "s2": (
        "คุณเป็น AI ผู้เชี่ยวชาญด้านการจัดทำ TOR ภาครัฐไทย ส่วนที่ 2: วัตถุประสงค์ "
        "หน้าที่ของคุณคือร่างวัตถุประสงค์ของโครงการตามหลัก SMART "
        "(Specific, Measurable, Achievable, Relevant, Time-bound) "
        "วัตถุประสงค์ต้องสอดคล้องกับความเป็นมาและขอบเขตของโครงการ "
        "ใช้ภาษาราชการไทยที่เป็นทางการ"
    ),
    "s3": (
        "คุณเป็น AI ผู้เชี่ยวชาญด้านการจัดทำ TOR ภาครัฐไทย ส่วนที่ 3: คุณสมบัติผู้เสนอราคา "
        "หน้าที่ของคุณคือร่างคุณสมบัติผู้เสนอราคาตามข้อกำหนดกฎหมาย พ.ร.บ. 2560 "
        "รวมถึงทุนจดทะเบียน ผลงาน ใบอนุญาต และคุณสมบัติเฉพาะที่จำเป็น "
        "ทุนจดทะเบียนชำระแล้วต้องเท่ากับ งบประมาณ ÷ 4 (ปัดลง) "
        "ใช้ภาษาราชการไทยที่เป็นทางการ"
    ),
    "s4": (
        "คุณเป็น AI ผู้เชี่ยวชาญด้านการจัดทำ TOR ภาครัฐไทย ส่วนที่ 4: ขอบเขตของงาน "
        "หน้าที่ของคุณคือร่างขอบเขตงานอย่างละเอียด ครอบคลุม 14 หมวดย่อย "
        "รวมถึงรายละเอียดทางเทคนิค ผลงานส่งมอบ และเกณฑ์การตรวจรับ "
        "ใช้ภาษาราชการไทยที่เป็นทางการ"
    ),
    "s5": (
        "คุณเป็น AI ผู้เชี่ยวชาญด้านการจัดทำ TOR ภาครัฐไทย ส่วนที่ 5: ระยะเวลาดำเนินการ "
        "หน้าที่ของคุณคือร่างระยะเวลาดำเนินการที่เหมาะสม "
        "กำหนดเหตุการณ์สำคัญ (milestones) และระยะเวลาต่อเหตุการณ์ "
        "คำนึงถึงความเป็นไปได้: งบ > 100 ล้าน → ≥ 180 วัน; งบ < 10 ล้าน → ≤ 365 วัน "
        "ใช้ภาษาราชการไทยที่เป็นทางการ"
    ),
    "s6": (
        "คุณเป็น AI ผู้เชี่ยวชาญด้านการจัดทำ TOR ภาครัฐไทย ส่วนที่ 6: วงเงินงบประมาณ "
        "หน้าที่ของคุณคือร่างรายละเอียดวงเงินงบประมาณ เหตุผลของราคา "
        "และรายละเอียดการจัดสรรงบประมาณต่อรายการ "
        "ใช้ภาษาราชการไทยที่เป็นทางการ"
    ),
    "s7": (
        "คุณเป็น AI ผู้เชี่ยวชาญด้านการจัดทำ TOR ภาครัฐไทย ส่วนที่ 7: สถานที่ดำเนินการ "
        "หน้าที่ของคุณคือร่างสถานที่ปฏิบัติงาน สถานที่ส่งมอบ/ติดตั้ง และเงื่อนไขการเข้าพื้นที่ "
        "ใช้ภาษาราชการไทยที่เป็นทางการ"
    ),
    "s8": (
        "คุณเป็น AI ผู้เชี่ยวชาญด้านการจัดทำ TOR ภาครัฐไทย ส่วนที่ 8: งวดงาน/การจ่ายเงิน "
        "หน้าที่ของคุณคือร่างการแบ่งงวดงานและเงื่อนไขการจ่ายเงิน "
        "ร้อยละรวมทุกงวดต้องเท่ากับ 100% แต่ละงวดต้องอยู่ระหว่าง 5%-50% "
        "แต่ละงวดต้องระบุผลงานส่งมอบที่ชัดเจน "
        "ใช้ภาษาราชการไทยที่เป็นทางการ"
    ),
    "s9": (
        "คุณเป็น AI ผู้เชี่ยวชาญด้านการจัดทำ TOR ภาครัฐไทย ส่วนที่ 9: การรับประกัน "
        "หน้าที่ของคุณคือร่างเงื่อนไขการรับประกันงาน/พัสดุ "
        "ใช้ภาษาราชการไทยที่เป็นทางการ"
    ),
    "s10": (
        "คุณเป็น AI ผู้เชี่ยวชาญด้านการจัดทำ TOR ภาครัฐไทย ส่วนที่ 10: อัตราค่าปรับ "
        "หน้าที่ของคุณคือร่างอัตราค่าปรับกรณีส่งงานล่าช้า "
        "อัตราค่าปรับต้องอยู่ระหว่าง 0.01%-0.20% ต่อวัน ขั้นต่ำ 100 บาท/วัน "
        "ใช้ภาษาราชการไทยที่เป็นทางการ"
    ),
    "s11": (
        "คุณเป็น AI ผู้เชี่ยวชาญด้านการจัดทำ TOR ภาครัฐไทย ส่วนที่ 11: เกณฑ์พิจารณาข้อเสนอ "
        "หน้าที่ของคุณคือร่างเกณฑ์การพิจารณาคัดเลือก ทั้งด้านเทคนิคและราคา "
        "กำหนดน้ำหนักคะแนนและเกณฑ์ผ่าน "
        "ใช้ภาษาราชการไทยที่เป็นทางการ"
    ),
    "s12": (
        "คุณเป็น AI ผู้เชี่ยวชาญด้านการจัดทำ TOR ภาครัฐไทย ส่วนที่ 12: เอกสารที่ต้องยื่น "
        "หน้าที่ของคุณคือร่างรายการเอกสารที่ผู้เสนอราคาต้องยื่น "
        "ใช้ภาษาราชการไทยที่เป็นทางการ"
    ),
    "s13": (
        "คุณเป็น AI ผู้เชี่ยวชาญด้านการจัดทำ TOR ภาครัฐไทย ส่วนที่ 13: เงื่อนไขอื่นๆ "
        "หน้าที่ของคุณคือร่างเงื่อนไขเพิ่มเติม หลักประกัน และข้อสงวนสิทธิ์ "
        "ต้องสอดคล้องกับกฎหมาย พ.ร.บ. 2560 "
        "ใช้ภาษาราชการไทยที่เป็นทางการ"
    ),
}


# =============================================================================
# Helper functions
# =============================================================================


def _build_rag_query(target_section: str, user_input: dict) -> str:
    """Build a search query for RAG retrieval based on section and user input.

    Combines the section name with relevant user input fields to create
    a contextual search query.

    Args:
        target_section: The TOR section key (e.g., "s1", "s4").
        user_input: User-provided form data from the wizard step.

    Returns:
        A query string suitable for RAG embedding and similarity search.
    """
    section_name = SECTION_NAMES.get(target_section, target_section)

    # Build query from user input context
    query_parts = [f"TOR {section_name}"]

    # Include project description/name if available
    if user_input.get("project_name"):
        query_parts.append(f"โครงการ: {user_input['project_name']}")

    if user_input.get("project_type"):
        query_parts.append(f"ประเภท: {user_input['project_type']}")

    if user_input.get("description"):
        query_parts.append(user_input["description"])

    # Include section-specific data that helps with context retrieval
    if target_section == "s3" and user_input.get("budget"):
        query_parts.append(f"งบประมาณ: {user_input['budget']} บาท คุณสมบัติผู้เสนอราคา")

    if target_section == "s6" and user_input.get("budget"):
        query_parts.append(f"วงเงินงบประมาณ {user_input['budget']} บาท")

    if target_section == "s10":
        query_parts.append("อัตราค่าปรับ เงื่อนไข กฎหมาย พ.ร.บ. 2560")

    return " ".join(query_parts)


def _build_section_filter(target_section: str) -> dict | None:
    """Build metadata filter for section-relevant RAG retrieval.

    Maps target sections to relevant document types and legal references
    for more precise retrieval.

    Args:
        target_section: The TOR section key.

    Returns:
        Filter dict for the RAG retriever, or None for broad search.
    """
    from app.rag.retrieval import RetrievalFilter

    # Legal-heavy sections filter for law/regulation documents
    if target_section in ("s3", "s10", "s13"):
        return RetrievalFilter(section_relevance=target_section)

    # All other sections: filter by section relevance if available
    return RetrievalFilter(section_relevance=target_section)


def _build_llm_messages(
    target_section: str,
    user_input: dict,
    template: dict,
    rag_chunks: list[dict],
    validation_findings: list[dict] | None = None,
    human_feedback: str | None = None,
    retry_count: int = 0,
) -> list[dict]:
    """Build the message list for the LLM invocation.

    Constructs system prompt + user messages with:
    - Agent system prompt for the target section
    - User input data from the wizard
    - RAG-retrieved context for reference
    - Template guidance
    - Validation feedback (on retry)
    - Human feedback (on re-draft request)

    Args:
        target_section: TOR section key.
        user_input: User form data.
        template: Template structure and guidance.
        rag_chunks: Retrieved RAG context chunks.
        validation_findings: Findings from previous attempt (on retry).
        human_feedback: Human feedback requesting re-draft.
        retry_count: Current retry count.

    Returns:
        List of message dicts with 'role' and 'content' keys.
    """
    messages: list[dict] = []

    # System prompt: agent-specific instruction
    system_prompt = AGENT_SYSTEM_PROMPTS.get(
        target_section,
        "คุณเป็น AI ผู้เชี่ยวชาญด้านการจัดทำ TOR ภาครัฐไทย ใช้ภาษาราชการไทยที่เป็นทางการ",
    )
    messages.append({"role": "system", "content": system_prompt})

    # User message: combine all context into a structured prompt
    user_parts: list[str] = []

    # Section header
    section_name = SECTION_NAMES.get(target_section, target_section)
    user_parts.append(f"## กรุณาร่าง TOR ส่วนที่: {section_name}\n")

    # User input data
    user_parts.append("### ข้อมูลจากผู้ใช้:")
    for key, value in user_input.items():
        if value:
            user_parts.append(f"- {key}: {value}")
    user_parts.append("")

    # Template guidance
    if template:
        user_parts.append("### แนวทางจากแม่แบบ:")
        if isinstance(template, dict):
            guidance = template.get("placeholder_guidance", {})
            structure = template.get("section_structure", {})
            if guidance.get(target_section):
                user_parts.append(f"คำแนะนำ: {guidance[target_section]}")
            if structure.get(target_section):
                user_parts.append(f"โครงสร้าง: {structure[target_section]}")
        user_parts.append("")

    # RAG context
    if rag_chunks:
        user_parts.append("### ข้อมูลอ้างอิงจากฐานความรู้:")
        for i, chunk in enumerate(rag_chunks[:5], 1):
            chunk_text = chunk.get("text", "")
            source = chunk.get("source_document", "ไม่ระบุแหล่ง")
            user_parts.append(f"[{i}] {chunk_text[:500]}")
            user_parts.append(f"    (ที่มา: {source})")
        user_parts.append("")
    else:
        user_parts.append(
            "### หมายเหตุ: ไม่สามารถดึงข้อมูลอ้างอิงจากฐานความรู้ได้ "
            "กรุณาร่างตามข้อมูลที่มี\n"
        )

    # Validation feedback (on retry) — structured correction instructions (Req 12.3)
    if retry_count > 0 and validation_findings:
        user_parts.append("### ⚠️ ข้อแก้ไขจากการตรวจสอบครั้งก่อน:")
        user_parts.append(
            "กรุณาแก้ไขประเด็นต่อไปนี้ในฉบับร่างใหม่:"
        )
        for finding in validation_findings:
            severity = finding.get("severity", "warning")
            message = finding.get("message", "")
            correction = finding.get("recommended_correction", "")
            icon = "❌" if severity == "error" else "⚠️"
            user_parts.append(f"  {icon} {message}")
            if correction:
                user_parts.append(f"    → แนะนำ: {correction}")
        user_parts.append("")

    # Human feedback (on re-draft request)
    if human_feedback:
        user_parts.append("### 💬 ข้อเสนอแนะจากผู้ใช้:")
        user_parts.append(human_feedback)
        user_parts.append("")

    # Final instruction
    user_parts.append(
        "### คำสั่ง: กรุณาร่างเนื้อหา TOR ส่วนนี้ให้สมบูรณ์ "
        "ถูกต้องตามกฎหมาย พ.ร.บ. การจัดซื้อจัดจ้าง 2560 "
        "และใช้ภาษาราชการไทยที่เป็นทางการ"
    )

    messages.append({"role": "user", "content": "\n".join(user_parts)})

    return messages


async def _draft_section_with_agent(
    llm: Any,
    target_section: str,
    user_input: dict,
    rag_chunks: list[dict],
    template: dict,
    validation_findings: list[dict] | None,
    human_feedback: str | None,
    retry_count: int,
    agent_timeout: float | int,
) -> str:
    """Draft one TOR section via the registered agent, or raw LLM fallback.

    Specialized s1–s13 agents own prompt construction. If no agent is
    registered for ``target_section``, fall back to ``_build_llm_messages``.
    Timeout wrapping stays here so ``llm_draft`` does not grow branches.
    """
    findings = validation_findings if retry_count > 0 else None
    agent = get_agent_for_section(target_section)
    if agent is not None:
        return await asyncio.wait_for(
            agent.draft(
                llm,
                user_input,
                rag_chunks,
                template,
                findings,
                human_feedback,
                temperature=0.3,
                max_tokens=4000,
            ),
            timeout=agent_timeout,
        )

    messages = _build_llm_messages(
        target_section=target_section,
        user_input=user_input,
        template=template,
        rag_chunks=rag_chunks,
        validation_findings=findings,
        human_feedback=human_feedback,
        retry_count=retry_count,
    )
    response = await asyncio.wait_for(
        llm.invoke(messages=messages, temperature=0.3, max_tokens=4000),
        timeout=agent_timeout,
    )
    return response.content


def _create_rule_engine() -> RuleEngine:
    """Create a RuleEngine instance with all rules registered.

    Lazily imports and registers all validation rules from the rules package.

    Returns:
        A fully configured RuleEngine instance.
    """
    from app.rule_engine.engine import RuleEngine

    engine = RuleEngine()

    # Register legal rules
    try:
        from app.rule_engine.rules.legal import (
            BrandLockFairnessRule,
            PenaltyRateRule,
            RequiredLegalReferencesRule,
            VendorPaidUpCapitalRule,
        )
        from app.rule_engine.rules.payment import PaymentScheduleRule
        from app.rule_engine.rules.timeline import TimelineFeasibilityRule

        engine.register_rule("legal", VendorPaidUpCapitalRule())
        engine.register_rule("legal", PenaltyRateRule())
        engine.register_rule("legal", BrandLockFairnessRule())
        engine.register_rule("legal", RequiredLegalReferencesRule())
        engine.register_rule("legal", PaymentScheduleRule())
        engine.register_rule("legal", TimelineFeasibilityRule())
    except ImportError:
        logger.debug("Legal rules module not available, skipping registration")

    # Register completeness rules
    try:
        from app.rule_engine.rules.completeness import (
            MinimumContentRule,
            RequiredSubsectionsRule,
            SectionPresenceRule,
        )

        engine.register_rule("completeness", SectionPresenceRule())
        engine.register_rule("completeness", RequiredSubsectionsRule())
        engine.register_rule("completeness", MinimumContentRule())
    except ImportError:
        logger.debug("Completeness rules module not available, skipping registration")

    # Register consistency rules
    try:
        from app.rule_engine.rules.consistency import (
            BudgetScopeConsistencyRule,
            QualificationsComplexityConsistencyRule,
            TimelineDeliverablesConsistencyRule,
        )

        engine.register_rule("consistency", BudgetScopeConsistencyRule())
        engine.register_rule("consistency", TimelineDeliverablesConsistencyRule())
        engine.register_rule("consistency", QualificationsComplexityConsistencyRule())
    except ImportError:
        logger.debug("Consistency rules module not available, skipping registration")

    # Register format rules
    try:
        from app.rule_engine.rules.format import get_format_rules

        for rule in get_format_rules():
            engine.register_rule("format", rule)
    except (ImportError, AttributeError):
        logger.debug("Format rules module not available, skipping registration")

    return engine


# =============================================================================
# Node implementations
# =============================================================================


async def validate_input(state: TORDraftState) -> TORDraftState:
    """Validate required input fields before proceeding with the drafting workflow.

    Checks that project_id, user_input, and target_section are present and valid.
    If validation fails, sets the error field and the graph will route to END.

    Args:
        state: Current graph state with input fields.

    Returns:
        Updated state. On success: initializes retry_count, max_retries, and
        requires_human_review. On failure: sets error field.
    """
    await asyncio.sleep(0)
    errors: list[str] = []

    if not state.get("project_id"):
        errors.append("project_id is required")

    if not state.get("user_input"):
        errors.append("user_input is required")

    target_section = state.get("target_section")
    if not target_section:
        errors.append("target_section is required")
    elif target_section not in SECTION_NAMES:
        errors.append(
            f"target_section '{target_section}' is invalid. "
            f"Must be one of: {', '.join(sorted(SECTION_NAMES.keys()))}"
        )

    if errors:
        logger.warning("Input validation failed: %s", errors)
        return {
            **state,
            "error": f"Validation failed: {'; '.join(errors)}",
        }

    # Initialize orchestration control fields
    max_retries = state.get("max_retries", DEFAULT_MAX_RETRIES)
    # Enforce max_retries bounds: default 3, maximum 10 (Requirement 12.6)
    max_retries = max(1, min(10, max_retries))

    # Enforce agent_timeout_seconds bounds: default 60, maximum 300 (Requirement 12.6)
    agent_timeout = state.get("agent_timeout_seconds", LLM_TIMEOUT_SECONDS)
    agent_timeout = max(1, min(MAX_TIMEOUT_SECONDS, agent_timeout))

    # Determine if mandatory human review is needed (Requirement 12.7)
    requires_review = target_section in MANDATORY_HUMAN_REVIEW_SECTIONS

    logger.info(
        "Input validated for project=%s, section=%s, max_retries=%d, "
        "timeout=%ds, mandatory_review=%s",
        state.get("project_id"),
        target_section,
        max_retries,
        agent_timeout,
        requires_review,
    )

    return {
        **state,
        "retry_count": state.get("retry_count", 0),
        "max_retries": max_retries,
        "agent_timeout_seconds": agent_timeout,
        "draft_version": state.get("draft_version", 0),
        "requires_human_review": requires_review,
        "best_draft_content": None,
        "best_draft_score": -1.0,
        "best_draft_findings": [],
        "error": None,
    }


async def retrieve_context(state: TORDraftState) -> TORDraftState:
    """Retrieve relevant knowledge base chunks via the RAG pipeline.

    Uses the RAG retriever to find relevant legal/regulatory context for
    the target TOR section. If retrieval fails, sets rag_retrieval_failed=True
    and proceeds without context (Requirement 5.8: graceful RAG degradation).

    Args:
        state: Current graph state with target_section and user_input.

    Returns:
        Updated state with rag_chunks populated (or empty list on failure).
    """
    target_section = state.get("target_section", "")
    user_input = state.get("user_input", {})

    logger.info("Retrieving RAG context for section=%s", target_section)

    try:
        from app.providers.factory import ProviderFactory
        from app.rag.retrieval import RAGRetriever

        # Create provider instances
        factory = ProviderFactory()
        embedding_provider = factory.get_embedding()
        vector_store_provider = factory.get_vector_store()

        # Create RAG retriever
        retriever = RAGRetriever(
            embedding_provider=embedding_provider,
            vector_store_provider=vector_store_provider,
            default_top_k=5,
        )

        # Build contextual query based on section and user input
        query = _build_rag_query(target_section, user_input)

        # Build section-specific filter
        retrieval_filter = _build_section_filter(target_section)

        # Execute retrieval
        result = await retriever.retrieve(
            query=query,
            top_k=5,
            filter=retrieval_filter,
        )

        # Convert RetrievedChunk objects to RAGChunk dicts for state
        rag_chunks = [
            {
                "id": chunk.id,
                "text": chunk.text,
                "score": chunk.score,
                "source_document": chunk.source_document,
                "section_label": chunk.section_label,
                "page_number": chunk.page_number,
                "document_type": chunk.document_type,
                "legal_reference": chunk.legal_reference,
            }
            for chunk in result.chunks
        ]

        logger.info(
            "RAG retrieval successful: %d chunks retrieved for section=%s",
            len(rag_chunks),
            target_section,
        )

        return {
            **state,
            "rag_chunks": rag_chunks,
            "rag_retrieval_failed": False,
        }

    except Exception:
        logger.exception(
            "RAG retrieval failed for section=%s. Proceeding without context (Req 5.8).",
            target_section,
        )
        return {
            **state,
            "rag_chunks": [],
            "rag_retrieval_failed": True,
        }


async def llm_draft(state: TORDraftState) -> TORDraftState:
    """Generate a TOR section draft using the appropriate specialized agent.

    Invokes the LLM provider with:
    - Agent-specific system prompt for the target section
    - User input from the wizard step
    - RAG-retrieved context chunks
    - Template guidance
    - Validation feedback from previous attempts (if retrying)
    - Human feedback (if re-draft was requested)

    On retry, incorporates specific violation feedback from the Rule Engine
    as structured correction instructions (Requirement 12.3).

    Args:
        state: Current graph state with user_input, rag_chunks, template, and
            optionally validation_findings from a previous attempt.

    Returns:
        Updated state with draft_content and incremented draft_version.
    """
    target_section = state.get("target_section", "")
    user_input = state.get("user_input", {})
    template = state.get("template", {})
    rag_chunks = state.get("rag_chunks", [])
    validation_findings = state.get("validation_findings", [])
    human_feedback = state.get("human_feedback")
    retry_count = state.get("retry_count", 0)
    current_version = state.get("draft_version", 0) + 1

    logger.info(
        "Generating draft for section=%s, version=%d, retry=%d",
        target_section,
        current_version,
        retry_count,
    )

    try:
        from app.providers.factory import ProviderFactory

        # Get LLM provider via factory
        factory = ProviderFactory()
        llm = factory.get_llm()
        agent_timeout = state.get("agent_timeout_seconds", LLM_TIMEOUT_SECONDS)
        try:
            draft_content = await _draft_section_with_agent(
                llm,
                target_section,
                user_input,
                rag_chunks,
                template,
                validation_findings,
                human_feedback,
                retry_count,
                agent_timeout,
            )
        except asyncio.TimeoutError:
            logger.exception(
                "LLM timeout for section=%s after %ds (agent_timeout=%ds)",
                target_section,
                agent_timeout,
                agent_timeout,
            )
            return {
                **state,
                "draft_content": state.get("draft_content", ""),
                "draft_version": current_version,
                "error": (
                    f"LLM timeout after {agent_timeout}s for section {target_section}. "
                    f"Agent: {target_section}, elapsed: {agent_timeout}s"
                ),
            }

        logger.info(
            "LLM draft generated successfully for section=%s, version=%d, chars=%d",
            target_section,
            current_version,
            len(draft_content),
        )

        return {
            **state,
            "draft_content": draft_content,
            "draft_version": current_version,
        }

    except TimeoutError:
        logger.exception(
            "LLM timeout for section=%s after %ds",
            target_section,
            LLM_TIMEOUT_SECONDS,
        )
        return {
            **state,
            "draft_content": state.get("draft_content", ""),
            "draft_version": current_version,
            "error": f"LLM timeout after {LLM_TIMEOUT_SECONDS}s for section {target_section}",
        }

    except ConnectionError:
        logger.exception(
            "LLM provider unreachable for section=%s",
            target_section,
        )
        return {
            **state,
            "draft_content": state.get("draft_content", ""),
            "draft_version": current_version,
            "error": "LLM provider unreachable. Please check connectivity.",
        }

    except Exception as exc:
        logger.exception("LLM draft failed for section=%s", target_section)
        return {
            **state,
            "draft_content": state.get("draft_content", ""),
            "draft_version": current_version,
            "error": f"LLM draft generation failed: {exc}",
        }


async def rule_guardrail(state: TORDraftState) -> TORDraftState:
    """Run the Rule Engine on the generated draft to validate compliance.

    Constructs a TOR document dict from the current draft content plus any
    existing sections from user_input, then invokes RuleEngine.validate().

    The score determines routing:
    - score >= 70: pass to human_review
    - score < 70 and retries < max: retry llm_draft with feedback
    - score < 70 and retries >= max: pass to human_review with warnings

    The Rule Engine is always the final authority on legal/numeric matters.
    LLM output is never presented without Rule Engine validation (Req 12.5).

    Args:
        state: Current graph state with draft_content.

    Returns:
        Updated state with quality_score, validation_findings, guardrail_passed,
        and incremented retry_count if the guardrail rejects.
    """
    await asyncio.sleep(0)
    target_section = state.get("target_section", "")
    draft_content = state.get("draft_content", "")
    user_input = state.get("user_input", {})

    logger.info(
        "Running rule guardrail on section=%s, draft_version=%d",
        target_section,
        state.get("draft_version", 0),
    )

    try:
        # Construct tor_document from draft + existing sections and metadata
        tor_document: dict = {}

        # Include existing sections from user_input if available
        existing_sections = user_input.get("existing_sections", {})
        for key, content in existing_sections.items():
            tor_document[key] = content

        # Set the current draft for the target section
        tor_document[target_section] = draft_content

        # Include project metadata needed for validation rules
        if user_input.get("budget"):
            tor_document["budget"] = user_input["budget"]
        if user_input.get("project_type"):
            tor_document["project_type"] = user_input["project_type"]
        if user_input.get("timeline_days"):
            tor_document["timeline_days"] = user_input["timeline_days"]
        if "payment_installments" in user_input:
            tor_document["payment_installments"] = user_input["payment_installments"]

        # Create Rule Engine and validate
        engine = _create_rule_engine()
        result = engine.validate(tor_document)

        # Convert Finding objects to dicts for state
        findings_dicts = [
            {
                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                "rule_violated": f.rule_violated,
                "affected_section": f.affected_section,
                "message": f.message,
                "recommended_correction": f.recommended_correction,
            }
            for f in result.findings
        ]

        quality_score = result.quality_score
        passed = quality_score >= GUARDRAIL_THRESHOLD

        retry_count = state.get("retry_count", 0)
        if not passed:
            retry_count += 1

        # Track best-scoring draft across retries (Requirement 5.5)
        best_draft_content = state.get("best_draft_content")
        best_draft_score = state.get("best_draft_score", -1.0)
        best_draft_findings = state.get("best_draft_findings", [])

        if quality_score > best_draft_score:
            best_draft_content = state.get("draft_content", "")
            best_draft_score = quality_score
            best_draft_findings = findings_dicts

        logger.info(
            "Guardrail result: score=%d, passed=%s, retry_count=%d/%d, "
            "findings=%d, best_score=%d",
            quality_score,
            passed,
            retry_count,
            state.get("max_retries", DEFAULT_MAX_RETRIES),
            len(findings_dicts),
            best_draft_score,
        )

        return {
            **state,
            "quality_score": quality_score,
            "validation_findings": findings_dicts,
            "guardrail_passed": passed,
            "retry_count": retry_count,
            "best_draft_content": best_draft_content,
            "best_draft_score": best_draft_score,
            "best_draft_findings": best_draft_findings,
        }

    except Exception as exc:
        logger.exception(
            "Rule Engine execution failed for section=%s",
            target_section,
        )
        # Conservative: treat as failed validation
        retry_count = state.get("retry_count", 0) + 1
        return {
            **state,
            "quality_score": 0,
            "validation_findings": [
                {
                    "severity": "error",
                    "rule_violated": "RULE_ENGINE_ERROR",
                    "affected_section": target_section,
                    "message": f"Rule Engine execution failed: {exc}",
                    "recommended_correction": None,
                }
            ],
            "guardrail_passed": False,
            "retry_count": retry_count,
        }


async def human_review(state: TORDraftState) -> TORDraftState:
    """Present the draft to the user for review and approval.

    This node is a human-in-the-loop breakpoint. It presents:
    - The generated draft content
    - Quality score and validation findings
    - Any warnings about non-compliant areas (if max retries exhausted)
    - AI suggestions for improvement

    The human can:
    - Approve the draft → route to finalize
    - Request a re-draft with feedback → route back to llm_draft
    - Edit the content directly → route to finalize with edited content

    Mandatory for sections with legal references, budget calculations,
    or penalty clauses (Requirement 12.7).

    Args:
        state: Current graph state with draft_content, quality_score, findings.

    Returns:
        Updated state with human_approved and optionally human_feedback.
    """
    await asyncio.sleep(0)
    # In production, this node uses LangGraph's interrupt/breakpoint mechanism
    # to pause execution and wait for user input via the API.
    # The API endpoint will resume the graph with the human's decision.
    logger.info(
        "Human review requested for section=%s, score=%d, guardrail_passed=%s",
        state.get("target_section"),
        state.get("quality_score", 0),
        state.get("guardrail_passed", False),
    )

    # Note: When max retries are exhausted without passing, include a warning
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", DEFAULT_MAX_RETRIES)

    if retry_count >= max_retries and not state.get("guardrail_passed", False):
        logger.warning(
            "Presenting draft with warnings: max retries (%d) exhausted "
            "without passing guardrail for section=%s",
            max_retries,
            state.get("target_section"),
        )
        # Present the best-scoring draft instead of the last attempt (Req 5.5)
        best_draft = state.get("best_draft_content")
        best_score = state.get("best_draft_score", -1.0)
        best_findings = state.get("best_draft_findings", [])

        if best_draft and best_score > state.get("quality_score", 0):
            logger.info(
                "Using best draft (score=%d) instead of last attempt (score=%d)",
                best_score,
                state.get("quality_score", 0),
            )
            return {
                **state,
                "draft_content": best_draft,
                "quality_score": best_score,
                "validation_findings": best_findings,
                "human_approved": state.get("human_approved"),
                "human_feedback": state.get("human_feedback"),
            }

    # The human_approved and human_feedback fields are set by the API layer
    # when resuming the graph after the human makes their decision.
    return {
        **state,
        "human_approved": state.get("human_approved"),
        "human_feedback": state.get("human_feedback"),
    }


async def finalize(state: TORDraftState) -> TORDraftState:
    """Persist the approved section content and update project state.

    After human approval, this node:
    1. Stores the finalized content in the tor_sections table
    2. Creates a project version snapshot
    3. Updates the project's quality_score

    Note: Full database persistence will be integrated when the API endpoint
    layer provides the database session. For now, this sets finalized_content
    to signal successful completion.

    Args:
        state: Current graph state with approved draft_content.

    Returns:
        Updated state with finalized_content set.
    """
    await asyncio.sleep(0)
    target_section = state.get("target_section", "")
    project_id = state.get("project_id", "")
    draft_content = state.get("draft_content", "")

    logger.info(
        "Finalizing section=%s for project=%s, quality_score=%d",
        target_section,
        project_id,
        state.get("quality_score", 0),
    )

    # Set finalized content — the approved draft
    finalized_content = draft_content

    # NOTE: Database persistence placeholder.
    # When API endpoint integration is completed, this node will:
    # 1. Upsert into tor_sections table:
    #    - project_id, section_key=target_section, content=finalized_content
    #    - ai_draft=draft_content, quality_score, validation_findings
    #    - is_approved=True, version incremented
    # 2. Create project_versions snapshot:
    #    - project_id, version_number auto-increment
    #    - snapshot_data = full project state
    # 3. Update projects table:
    #    - quality_score (average of all section scores)
    #    - current_step (advance if appropriate)
    logger.info(
        "Section %s finalized for project %s. "
        "Content length: %d chars, quality_score: %d",
        target_section,
        project_id,
        len(finalized_content),
        state.get("quality_score", 0),
    )

    return {
        **state,
        "finalized_content": finalized_content,
        "error": None,
    }


# =============================================================================
# Conditional routing functions
# =============================================================================


def route_after_validation(state: TORDraftState) -> Literal["retrieve_context", "__end__"]:
    """Route after validate_input: proceed if valid, end if error.

    Args:
        state: Current graph state.

    Returns:
        "retrieve_context" if input is valid, "__end__" if there's an error.
    """
    if state.get("error"):
        return END
    return "retrieve_context"


def route_after_guardrail(
    state: TORDraftState,
) -> Literal["human_review", "llm_draft"]:
    """Route after rule_guardrail based on quality score and retry count.

    Routing logic:
    - If guardrail passed (score >= 70): → human_review
    - If guardrail failed and retries < max: → llm_draft (retry with feedback)
    - If guardrail failed and retries >= max: → human_review (with warnings)

    This ensures the system never enters an infinite retry loop (Req 12.6).

    Args:
        state: Current graph state with quality_score, retry_count, max_retries.

    Returns:
        Next node name: "human_review" or "llm_draft".
    """
    if state.get("guardrail_passed", False):
        return "human_review"

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", DEFAULT_MAX_RETRIES)

    if retry_count >= max_retries:
        # Max retries exhausted — present best result with warnings (Req 5.5)
        logger.warning(
            "Max retries (%d) exhausted for section=%s. "
            "Routing to human review with warnings.",
            max_retries,
            state.get("target_section"),
        )
        return "human_review"

    # Retry: route back to llm_draft with feedback
    return "llm_draft"


def route_after_human_review(
    state: TORDraftState,
) -> Literal["finalize", "llm_draft"]:
    """Route after human_review based on approval decision.

    Routing logic:
    - If human approved: → finalize
    - If human requested re-draft (feedback provided): → llm_draft
    - If no decision yet (None): → finalize (default to preserve state)

    Args:
        state: Current graph state with human_approved and human_feedback.

    Returns:
        Next node name: "finalize" or "llm_draft".
    """
    human_approved = state.get("human_approved")

    if human_approved is False and state.get("human_feedback"):
        # Human requested re-draft with specific feedback
        return "llm_draft"

    # Approved or pending (default to finalize)
    return "finalize"


# =============================================================================
# Graph construction
# =============================================================================


def build_tor_drafting_graph() -> StateGraph:
    """Build the LangGraph StateGraph for TOR section drafting.

    Creates a directed graph with the following structure:

        validate_input
            ├─ (error) → END
            └─ (valid) → retrieve_context
                            → llm_draft
                                → rule_guardrail
                                    ├─ (passed) → human_review
                                    ├─ (failed, retries < max) → llm_draft (loop)
                                    └─ (failed, retries >= max) → human_review
                                        human_review
                                            ├─ (approved) → finalize → END
                                            └─ (re-draft) → llm_draft (loop)

    Returns:
        A compiled LangGraph StateGraph ready for invocation.
    """
    # Create the state graph with TORDraftState schema
    graph = StateGraph(TORDraftState)

    # Add nodes
    graph.add_node("validate_input", validate_input)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("llm_draft", llm_draft)
    graph.add_node("rule_guardrail", rule_guardrail)
    graph.add_node("human_review", human_review)
    graph.add_node("finalize", finalize)

    # Set entry point
    graph.set_entry_point("validate_input")

    # Add edges with conditional routing
    graph.add_conditional_edges(
        "validate_input",
        route_after_validation,
        {
            "retrieve_context": "retrieve_context",
            END: END,
        },
    )

    # Linear edge: retrieve_context → llm_draft
    graph.add_edge("retrieve_context", "llm_draft")

    # Linear edge: llm_draft → rule_guardrail
    graph.add_edge("llm_draft", "rule_guardrail")

    # Conditional edge: rule_guardrail → human_review or llm_draft (retry)
    graph.add_conditional_edges(
        "rule_guardrail",
        route_after_guardrail,
        {
            "human_review": "human_review",
            "llm_draft": "llm_draft",
        },
    )

    # Conditional edge: human_review → finalize or llm_draft (re-draft)
    graph.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "finalize": "finalize",
            "llm_draft": "llm_draft",
        },
    )

    # Terminal edge: finalize → END
    graph.add_edge("finalize", END)

    return graph


def compile_tor_drafting_graph():
    """Build and compile the TOR drafting graph for execution.

    Configures the human_review node as a LangGraph interrupt point,
    enabling human-in-the-loop behavior where the graph pauses execution
    and waits for user input before proceeding (Requirement 12.7).

    Returns:
        A compiled graph (CompiledStateGraph) that can be invoked with
        an initial TORDraftState dict.

    Usage:
        graph = compile_tor_drafting_graph()
        result = await graph.ainvoke({
            "project_id": "...",
            "user_input": {...},
            "template": {...},
            "target_section": "s1",
        })

    Human-in-the-loop:
        The graph will interrupt at `human_review` node. To resume:
        1. Retrieve the graph state after interruption
        2. Update state with human_approved and human_feedback
        3. Resume the graph with the updated state
    """
    graph = build_tor_drafting_graph()
    # Configure human_review as an interrupt point (Requirement 12.7)
    # This causes the graph to pause execution before the human_review node,
    # allowing the API layer to collect user approval/feedback and then resume.
    return graph.compile(interrupt_before=["human_review"])
