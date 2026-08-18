"""Agent registry — maps TOR section keys to specialized drafting agents.

Keys follow the canonical legal 13-section model in app.domain.tor_sections.

Requirements: 5.6, 10.2, 12.1, 12.4
"""

from __future__ import annotations

import logging

from app.orchestrator.agents.background_agent import BackgroundDraftingAgent
from app.orchestrator.agents.base import BaseDraftingAgent
from app.orchestrator.agents.budget_agent import BudgetDraftingAgent
from app.orchestrator.agents.conditions_agent import ConditionsDraftingAgent
from app.orchestrator.agents.documents_agent import DocumentsDraftingAgent
from app.orchestrator.agents.evaluation_agent import EvaluationDraftingAgent
from app.orchestrator.agents.location_agent import LocationDraftingAgent
from app.orchestrator.agents.objectives_agent import ObjectivesDraftingAgent
from app.orchestrator.agents.payment_agent import PaymentDraftingAgent
from app.orchestrator.agents.penalties_agent import PenaltiesDraftingAgent
from app.orchestrator.agents.qualifications_agent import QualificationsDraftingAgent
from app.orchestrator.agents.review_agent import ReviewAgent
from app.orchestrator.agents.scope_agent import ScopeDraftingAgent
from app.orchestrator.agents.timeline_agent import TimelineDraftingAgent
from app.orchestrator.agents.warranty_agent import WarrantyDraftingAgent

logger = logging.getLogger(__name__)

AGENT_REGISTRY: dict[str, BaseDraftingAgent] = {
    "s1": BackgroundDraftingAgent(),
    "s2": ObjectivesDraftingAgent(),
    "s3": QualificationsDraftingAgent(),
    "s4": ScopeDraftingAgent(),
    "s5": TimelineDraftingAgent(),
    "s6": BudgetDraftingAgent(),
    "s7": LocationDraftingAgent(),
    "s8": PaymentDraftingAgent(),
    "s9": WarrantyDraftingAgent(),
    "s10": PenaltiesDraftingAgent(),
    "s11": EvaluationDraftingAgent(),
    "s12": DocumentsDraftingAgent(),
    "s13": ConditionsDraftingAgent(),
}

REVIEW_AGENT = ReviewAgent()


def get_agent_for_section(section_key: str) -> BaseDraftingAgent | None:
    """Get the specialized agent for a given TOR section key."""
    lookup = section_key
    if section_key.startswith("s4"):
        lookup = "s4"
    agent = AGENT_REGISTRY.get(lookup)
    if agent is None:
        logger.warning(
            "No agent registered for section_key=%r. Valid keys: %s",
            section_key,
            ", ".join(sorted(AGENT_REGISTRY.keys())),
        )
    return agent


def get_review_agent() -> ReviewAgent:
    """Get the ReviewAgent instance for full-document analysis."""
    return REVIEW_AGENT


def list_available_agents() -> list[dict[str, str]]:
    """List all registered agents with their section information."""
    agents_info = [
        {
            "section_key": agent.section_key,
            "section_name_th": agent.section_name_th,
            "section_name_en": agent.section_name_en,
        }
        for agent in AGENT_REGISTRY.values()
    ]
    agents_info.append({
        "section_key": "review",
        "section_name_th": REVIEW_AGENT.section_name_th,
        "section_name_en": REVIEW_AGENT.section_name_en,
    })
    return agents_info
