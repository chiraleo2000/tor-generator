"""Specialized TOR drafting agents — one per standard TOR section.

Each agent encapsulates:
- A system prompt in formal Thai (ภาษาราชการ) with section-specific guidance
- Logic to build LLM messages from user input + RAG context + validation feedback
- A draft() method that invokes the configured LLM provider and returns draft content

Agent registry maps section keys (s1–s10) to agent instances for dispatch by
the llm_draft orchestrator node.

Also includes the ReviewAgent (Agent R) for cross-section consistency analysis.

Requirements: 5.6, 10.2, 12.1, 12.4, 16.5
"""

from app.orchestrator.agents.base import BaseDraftingAgent
from app.orchestrator.agents.registry import (
    AGENT_REGISTRY,
    get_agent_for_section,
    get_review_agent,
)
from app.orchestrator.agents.review_agent import ReviewAgent, ReviewResult, ReviewSuggestion

__all__ = [
    "BaseDraftingAgent",
    "AGENT_REGISTRY",
    "get_agent_for_section",
    "get_review_agent",
    "ReviewAgent",
    "ReviewResult",
    "ReviewSuggestion",
]
