"""LangGraph orchestrator for TOR section drafting.

This package implements the AI-assisted drafting workflow using LangGraph StateGraph:
    validate_input → retrieve_context → llm_draft → rule_guardrail → human_review → finalize

Key components:
- state.py: TORDraftState TypedDict shared across all graph nodes
- graph.py: StateGraph definition with conditional routing and retry logic
- agents/: Specialized drafting agents for each TOR section (task 10.2)
- section_state.py: Cross-section state management (task 10.5)
- agents/review_agent.py: ReviewAgent for full-document analysis (task 10.5)
"""

from app.orchestrator.agent_graph import (
    build_agent_workflow_graph,
    compile_agent_workflow_graph,
)
from app.orchestrator.agent_state import AgentWorkflowState
from app.orchestrator.graph import (
    build_tor_drafting_graph,
    compile_tor_drafting_graph,
)
from app.orchestrator.section_state import SectionStateManager
from app.orchestrator.state import TORDraftState

__all__ = [
    "TORDraftState",
    "SectionStateManager",
    "build_tor_drafting_graph",
    "compile_tor_drafting_graph",
    "AgentWorkflowState",
    "build_agent_workflow_graph",
    "compile_agent_workflow_graph",
]
