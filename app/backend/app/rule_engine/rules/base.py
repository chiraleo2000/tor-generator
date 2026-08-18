"""Base rule class for all Rule Engine validation rules.

All concrete rules must inherit from BaseRule and implement the validate method.
Rules are deterministic — given the same input, they always produce the same findings.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.rule_engine.engine import Finding


class BaseRule(ABC):
    """Abstract base class for all validation rules.

    Each rule inspects specific aspects of a TOR document and returns
    a list of findings (errors, warnings, or suggestions) when issues
    are detected.

    Subclasses must implement the `validate` method.
    """

    @abstractmethod
    def validate(self, tor_document: dict) -> list[Finding]:
        """Run this rule against the TOR document.

        Args:
            tor_document: Dict with section_key -> content mapping.
                Expected keys: s1..s13 for the 13 standard sections.
                Also includes metadata: budget, project_type, timeline_days, etc.

        Returns:
            List of Finding objects. Empty list means no issues found.
        """
        ...
