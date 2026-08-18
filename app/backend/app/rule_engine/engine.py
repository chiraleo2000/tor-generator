"""Core Rule Engine: Deterministic TOR document validation with weighted scoring.

The Rule Engine orchestrates validation across 4 categories:
- Legal compliance (40%)
- Completeness (30%)
- Consistency (20%)
- Format adherence (10%)

The Rule Engine is purely deterministic with no randomness.
Multiple invocations with identical input produce identical results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.rule_engine.rules.base import BaseRule


class Severity(StrEnum):
    """Severity levels for validation findings."""

    ERROR = "error"
    WARNING = "warning"
    SUGGESTION = "suggestion"


@dataclass
class Finding:
    """A single validation finding from the Rule Engine.

    Attributes:
        severity: How critical this finding is (error, warning, suggestion).
        rule_violated: Identifier of the rule that was violated.
        affected_section: The TOR section key where the issue was found.
        message: Human-readable description of the issue (Thai).
        recommended_correction: Optional suggestion for how to fix the issue.
    """

    severity: Severity
    rule_violated: str
    affected_section: str
    message: str
    recommended_correction: str | None = None


@dataclass
class CategoryScore:
    """Score for a single validation category.

    Attributes:
        category: Name of the category (legal, completeness, consistency, format).
        score: Score within this category (0-100).
        weight: Weight of this category in the total score (0.0-1.0).
        findings: List of findings that affected this category's score.
    """

    category: str
    score: float  # 0-100 within this category
    weight: float  # 0.0-1.0
    findings: list[Finding] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Complete validation result from the Rule Engine.

    Attributes:
        quality_score: Total weighted score (0-100).
        categories: Breakdown of scores per category.
        findings: All findings across all categories.
        is_valid: Whether the document passes validation (quality_score >= 70).
        halted: Whether scoring was halted due to missing sections (Req 6.9).
        missing_sections: Dict of section_key -> section_name for missing sections.
    """

    quality_score: int  # 0-100 total
    categories: list[CategoryScore] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    is_valid: bool = False
    halted: bool = False
    missing_sections: dict[str, str] = field(default_factory=dict)


# Default category weights as specified in the design document
CATEGORY_WEIGHTS: dict[str, float] = {
    "legal": 0.40,
    "completeness": 0.30,
    "consistency": 0.20,
    "format": 0.10,
}

# Score deduction per severity level
SEVERITY_DEDUCTIONS: dict[Severity, float] = {
    Severity.ERROR: 20.0,
    Severity.WARNING: 10.0,
    Severity.SUGGESTION: 5.0,
}

# Minimum passing score threshold
PASSING_THRESHOLD: int = 70


class RuleEngine:
    """Deterministic rule engine that validates TOR documents.

    Orchestrates validation across 4 categories:
    - Legal compliance (40%)
    - Completeness (30%)
    - Consistency (20%)
    - Format adherence (10%)

    The Rule Engine is purely deterministic with no randomness.
    Multiple invocations with identical input produce identical results.
    """

    def __init__(self) -> None:
        """Initialize the Rule Engine with empty rule registries per category."""
        self._rules: dict[str, list[BaseRule]] = {
            "legal": [],
            "completeness": [],
            "consistency": [],
            "format": [],
        }

    def register_rule(self, category: str, rule: BaseRule) -> None:
        """Register a validation rule under a specific category.

        Args:
            category: One of 'legal', 'completeness', 'consistency', 'format'.
            rule: A BaseRule instance to be executed during validation.

        Raises:
            ValueError: If category is not recognized.
        """
        if category not in self._rules:
            raise ValueError(
                f"Unknown category '{category}'. "
                f"Must be one of: {', '.join(self._rules.keys())}"
            )
        self._rules[category].append(rule)

    def validate(self, tor_document: dict) -> ValidationResult:
        """Validate a TOR document and produce a Quality Score.

        Executes all registered rules per category, computes per-category scores
        based on severity deductions, then aggregates into a weighted total score.

        If a rule raises MissingSectionsHalt (from completeness rules), scoring
        is halted and the result is returned with halted=True and the list of
        missing sections (Requirement 6.9).

        Args:
            tor_document: Dict with section_key -> content mapping.
                Expected keys: s1..s13 for the 13 standard sections.
                Also includes metadata: budget, project_type, timeline_days, etc.

        Returns:
            ValidationResult with quality_score, category breakdown, and findings.
            If halted, quality_score is 0 and missing_sections is populated.
        """
        # Lazy import to avoid circular imports
        from app.rule_engine.rules.completeness import MissingSectionsHalt

        all_findings: list[Finding] = []
        category_scores: list[CategoryScore] = []

        for category, weight in CATEGORY_WEIGHTS.items():
            # Collect findings from all rules in this category
            category_findings: list[Finding] = []
            for rule in self._rules.get(category, []):
                try:
                    findings = rule.validate(tor_document)
                    category_findings.extend(findings)
                except MissingSectionsHalt as halt:
                    # Halt scoring: return immediately with missing sections info
                    return ValidationResult(
                        quality_score=0,
                        categories=[],
                        findings=halt.findings,
                        is_valid=False,
                        halted=True,
                        missing_sections=halt.missing_sections,
                    )

            # Compute category score based on findings
            score = self._compute_category_score(category_findings)

            category_scores.append(
                CategoryScore(
                    category=category,
                    score=score,
                    weight=weight,
                    findings=category_findings,
                )
            )
            all_findings.extend(category_findings)

        # Compute weighted total score
        total_score = self._compute_total_score(category_scores)

        return ValidationResult(
            quality_score=total_score,
            categories=category_scores,
            findings=all_findings,
            is_valid=total_score >= PASSING_THRESHOLD,
        )

    def _compute_category_score(self, findings: list[Finding]) -> float:
        """Compute score within a category based on findings severity.

        Starts at 100 and deducts based on finding severity:
        - ERROR: -20 points each
        - WARNING: -10 points each
        - SUGGESTION: -5 points each

        Score floor is 0. Score ceiling is 100.

        Args:
            findings: List of findings in this category.

        Returns:
            Float score between 0.0 and 100.0.
        """
        score = 100.0
        for finding in findings:
            deduction = SEVERITY_DEDUCTIONS.get(finding.severity, 0.0)
            score -= deduction
        # Clamp to [0, 100]
        return max(0.0, min(100.0, score))

    def _compute_total_score(self, category_scores: list[CategoryScore]) -> int:
        """Compute weighted total Quality_Score from category scores.

        Formula: sum(category_score * category_weight) for all categories.
        Result is rounded to nearest integer and clamped to [0, 100].

        Args:
            category_scores: List of CategoryScore objects with scores and weights.

        Returns:
            Integer quality score between 0 and 100.
        """
        total = 0.0
        for cs in category_scores:
            total += cs.score * cs.weight
        # Round and clamp to [0, 100]
        return max(0, min(100, round(total)))
