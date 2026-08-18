"""Rule Engine package for deterministic TOR document validation.

The Rule Engine validates TOR documents against Thai procurement law
(พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560) and produces
a Quality_Score with structured findings.

Categories and weights:
- Legal compliance (40%)
- Completeness (30%)
- Consistency (20%)
- Format adherence (10%)
"""

from app.rule_engine.engine import (
    CategoryScore,
    Finding,
    RuleEngine,
    Severity,
    ValidationResult,
)

__all__ = [
    "CategoryScore",
    "Finding",
    "RuleEngine",
    "Severity",
    "ValidationResult",
]
