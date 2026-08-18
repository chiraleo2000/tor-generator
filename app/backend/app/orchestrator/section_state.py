"""Cross-section state management for the TOR drafting wizard.

Maintains completed sections across wizard steps so that later agents can
reference content from earlier sections. This enables cross-section context:
- Budget agent can reference scope to justify costs
- Payment agent references deliverables from scope
- Timeline agent references scope complexity
- Qualifications agent references budget for capital calculation
- Review agent analyzes all sections for consistency

The SectionStateManager is instantiated per-project and accumulates finalized
section content as each wizard step completes. When the orchestrator drafts
a new section, it passes existing_sections via user_input so the LLM has
full cross-section context.

Requirements: 10.2, 12.4
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.domain.tor_sections import TOR_SECTION_LABELS, TOR_SECTION_ORDER

logger = logging.getLogger(__name__)

SECTION_ORDER: list[str] = list(TOR_SECTION_ORDER)
SECTION_NAMES_TH: dict[str, str] = dict(TOR_SECTION_LABELS)


@dataclass
class SectionSnapshot:
    """A snapshot of a completed TOR section.

    Attributes:
        section_key: The section identifier (e.g. "s1", "s4").
        content: The finalized text content of the section.
        quality_score: The Rule Engine quality score when this section was finalized.
        metadata: Additional metadata (budget, timeline_days, project_type, etc.)
    """

    section_key: str
    content: str
    quality_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SectionStateManager:
    """Manages accumulated section state across wizard steps for a single project.

    This class provides:
    1. Storage and retrieval of completed section content
    2. Assembly of all sections into a full TOR document for the ReviewAgent
    3. A method to build `existing_sections` dict for injection into user_input
       so later agents have cross-section context

    Usage:
        manager = SectionStateManager(project_id="proj-123")
        manager.add_section("s1", "ความเป็นมา content...", quality_score=85)
        manager.add_section("s2", "วัตถุประสงค์ content...", quality_score=90)

        # When drafting s3, inject existing sections as context
        existing = manager.get_existing_sections()
        # Pass existing to user_input["existing_sections"] for the orchestrator

        # For review: get full assembled TOR
        full_tor = manager.assemble_full_tor()
    """

    def __init__(self, project_id: str) -> None:
        """Initialize the state manager for a project.

        Args:
            project_id: UUID of the project being drafted.
        """
        self.project_id = project_id
        self._sections: dict[str, SectionSnapshot] = {}

    @property
    def completed_section_keys(self) -> list[str]:
        """Return list of completed section keys in standard order."""
        return [key for key in SECTION_ORDER if key in self._sections]

    @property
    def section_count(self) -> int:
        """Return number of completed sections."""
        return len(self._sections)

    def add_section(
        self,
        section_key: str,
        content: str,
        quality_score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add or update a completed section.

        Args:
            section_key: The section identifier (e.g. "s1").
            content: The finalized content for this section.
            quality_score: Optional quality score from Rule Engine.
            metadata: Optional metadata dict (budget, timeline, etc.)
        """
        if section_key not in SECTION_ORDER:
            logger.warning(
                "Unknown section_key=%r added to state manager for project=%s",
                section_key,
                self.project_id,
            )

        self._sections[section_key] = SectionSnapshot(
            section_key=section_key,
            content=content,
            quality_score=quality_score,
            metadata=metadata or {},
        )

        logger.info(
            "Section %s added/updated for project=%s (total: %d sections)",
            section_key,
            self.project_id,
            self.section_count,
        )

    def remove_section(self, section_key: str) -> None:
        """Remove a section from the state (e.g., when user resets a step).

        Args:
            section_key: The section identifier to remove.
        """
        if section_key in self._sections:
            del self._sections[section_key]
            logger.info(
                "Section %s removed from project=%s state",
                section_key,
                self.project_id,
            )

    def get_section(self, section_key: str) -> SectionSnapshot | None:
        """Get a specific section snapshot.

        Args:
            section_key: The section to retrieve.

        Returns:
            The SectionSnapshot or None if not yet completed.
        """
        return self._sections.get(section_key)

    def get_existing_sections(self) -> dict[str, str]:
        """Get all completed sections as a dict mapping section_key to content.

        This is designed to be passed as user_input["existing_sections"] when
        invoking the orchestrator for a new section, enabling later agents to
        reference earlier content.

        Returns:
            Dict of section_key -> content for all completed sections.
        """
        return {
            key: snapshot.content
            for key, snapshot in self._sections.items()
        }

    def get_section_metadata(self) -> dict[str, dict[str, Any]]:
        """Get metadata for all completed sections.

        Returns:
            Dict of section_key -> metadata dict.
        """
        return {
            key: snapshot.metadata
            for key, snapshot in self._sections.items()
        }

    def assemble_full_tor(self) -> dict[str, str]:
        """Assemble all completed sections into a full TOR document dict.

        Returns sections in standard order. This is used by the ReviewAgent
        to analyze cross-section consistency.

        Returns:
            Ordered dict of section_key -> content for all completed sections.
        """
        assembled: dict[str, str] = {}
        for key in SECTION_ORDER:
            if key in self._sections:
                assembled[key] = self._sections[key].content
        return assembled

    def get_assembled_text(self) -> str:
        """Assemble all sections into a single text document for review.

        Combines all completed sections with headers into a readable format.

        Returns:
            Full TOR text with section headers.
        """
        parts: list[str] = []
        for key in SECTION_ORDER:
            if key in self._sections:
                section_name = SECTION_NAMES_TH.get(key, key)
                parts.append(f"## {section_name}")
                parts.append(self._sections[key].content)
                parts.append("")  # Blank line separator

        return "\n".join(parts)

    def get_average_quality_score(self) -> float | None:
        """Calculate average quality score across all completed sections.

        Returns:
            Average score (0-100) or None if no sections have scores.
        """
        scores = [
            s.quality_score
            for s in self._sections.values()
            if s.quality_score is not None
        ]
        if not scores:
            return None
        return sum(scores) / len(scores)

    @classmethod
    def from_sections_dict(
        cls,
        project_id: str,
        sections: dict[str, str],
        scores: dict[str, float] | None = None,
        metadata: dict[str, dict[str, Any]] | None = None,
    ) -> "SectionStateManager":
        """Create a SectionStateManager from an existing sections dict.

        Useful for reconstructing state from database records (e.g.,
        loading a project's existing TOR sections from the tor_sections table).

        Args:
            project_id: The project UUID.
            sections: Dict of section_key -> content.
            scores: Optional dict of section_key -> quality_score.
            metadata: Optional dict of section_key -> metadata dict.

        Returns:
            A populated SectionStateManager instance.
        """
        manager = cls(project_id=project_id)
        scores = scores or {}
        metadata = metadata or {}

        for key, content in sections.items():
            manager.add_section(
                section_key=key,
                content=content,
                quality_score=scores.get(key),
                metadata=metadata.get(key, {}),
            )

        return manager
