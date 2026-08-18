"""Rules sub-package for the Rule Engine.

Contains concrete rule implementations organized by validation category:
- legal.py: Legal compliance rules (พ.ร.บ. 2560)
- completeness.py: Section presence and content rules
- consistency.py: Cross-section consistency rules
- format.py: Thai government format adherence rules
- payment.py: Payment schedule validation rules
- timeline.py: Timeline feasibility rules

NOTE: Rule modules are NOT eagerly imported here to avoid circular imports.
Import specific rules directly from their modules, e.g.:
    from app.rule_engine.rules.payment import PaymentScheduleRule
    from app.rule_engine.rules.timeline import TimelineFeasibilityRule
"""

from app.rule_engine.rules.base import BaseRule

__all__ = ["BaseRule"]
