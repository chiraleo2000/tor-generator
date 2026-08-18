"""LangGraph StateGraph schema for TOR drafting orchestration.

Defines the TORDraftState TypedDict that flows through the orchestrator graph.
Each node reads from and writes to this shared state, enabling coordination
between validation, RAG retrieval, LLM drafting, rule guardrail, and human review.

Requirements: 5.2, 12.2, 12.4, 12.6
"""

from __future__ import annotations

from typing import TypedDict


class ValidationFinding(TypedDict, total=False):
    """A single finding from rule engine validation.

    Attributes:
        severity: One of "error", "warning", "suggestion".
        rule_violated: Identifier of the violated rule.
        affected_section: The TOR section key where the issue was found.
        message: Human-readable description (Thai).
        recommended_correction: Suggested fix (optional).
    """

    severity: str
    rule_violated: str
    affected_section: str
    message: str
    recommended_correction: str | None


class RAGChunk(TypedDict, total=False):
    """A retrieved knowledge base chunk.

    Attributes:
        id: Unique chunk identifier.
        text: Chunk text content.
        score: Cosine similarity score (0.0–1.0).
        source_document: Source document name.
        section_label: Section label within the source.
        page_number: Page number in source.
        document_type: Category of the source document.
        legal_reference: Legal reference if applicable.
    """

    id: str
    text: str
    score: float
    source_document: str | None
    section_label: str | None
    page_number: int | None
    document_type: str | None
    legal_reference: str | None


class TORDraftState(TypedDict, total=False):
    """Shared state for the TOR drafting LangGraph orchestrator.

    This TypedDict defines all fields passed between graph nodes. Fields
    use `total=False` to allow incremental population as the graph executes.

    Sections:
        Input: Fields provided at graph invocation.
        RAG Context: Populated by the retrieve_context node.
        LLM Output: Populated by the llm_draft node.
        Validation: Populated by the rule_guardrail node.
        Human Review: Populated by the human_review node.
        Final Output: Populated by the finalize node.
        Error Handling: Populated on any failure.
    """

    # -------------------------------------------------------------------------
    # Input — provided when invoking the graph
    # -------------------------------------------------------------------------

    # UUID of the project being drafted
    project_id: str

    # User-provided input for the current section (form data from wizard step)
    user_input: dict

    # Template structure and guidance for the target section
    template: dict

    # Target TOR section key (e.g., "s1", "s2", ..., "s13")
    target_section: str

    # -------------------------------------------------------------------------
    # RAG Context — populated by retrieve_context node
    # -------------------------------------------------------------------------

    # Retrieved knowledge base chunks relevant to the target section
    rag_chunks: list[RAGChunk]

    # Whether RAG retrieval failed (proceed without context if True)
    rag_retrieval_failed: bool

    # -------------------------------------------------------------------------
    # LLM Output — populated by llm_draft node
    # -------------------------------------------------------------------------

    # The generated draft content for the target section
    draft_content: str

    # Current draft version number (increments on retry)
    draft_version: int

    # -------------------------------------------------------------------------
    # Validation — populated by rule_guardrail node
    # -------------------------------------------------------------------------

    # Quality score from Rule Engine (0–100)
    quality_score: float

    # Structured validation findings from Rule Engine
    validation_findings: list[ValidationFinding]

    # Number of retry attempts made so far
    retry_count: int

    # Maximum retries allowed (configurable, default 3, max 10)
    max_retries: int

    # Whether the draft passed the guardrail threshold (quality_score >= 0.7 * 100)
    guardrail_passed: bool

    # -------------------------------------------------------------------------
    # Human Review — populated by human_review node
    # -------------------------------------------------------------------------

    # Whether the human approved the draft (None = pending review)
    human_approved: bool | None

    # Human feedback text (when requesting re-draft or providing edits)
    human_feedback: str | None

    # -------------------------------------------------------------------------
    # Final Output — populated by finalize node
    # -------------------------------------------------------------------------

    # The finalized content after human approval
    finalized_content: str | None

    # -------------------------------------------------------------------------
    # Best Draft Tracking — preserves highest-scoring draft across retries
    # -------------------------------------------------------------------------

    # The best draft content seen across all retry attempts (highest quality_score)
    best_draft_content: str | None

    # The quality score of the best draft
    best_draft_score: float

    # The validation findings associated with the best draft
    best_draft_findings: list[ValidationFinding]

    # -------------------------------------------------------------------------
    # Timeout Configuration
    # -------------------------------------------------------------------------

    # Timeout per agent invocation in seconds (default 60, max 300) — Req 12.6
    agent_timeout_seconds: int

    # -------------------------------------------------------------------------
    # Error Handling
    # -------------------------------------------------------------------------

    # Error message if the orchestrator encounters a fatal error
    error: str | None

    # Whether this section requires mandatory human review
    # (legal refs, budget calculations, penalty clauses — Req 12.7)
    requires_human_review: bool

