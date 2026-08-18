---
name: tor-review
description: Review and validate Thai government procurement TOR documents for legal compliance, completeness, and correctness. Activates when users submit TOR for checking or auditing.
version: 1.0.0
author: Procurement Knowledge Team
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [Government, Procurement, Thai, TOR, Review, Audit, Legal]
    related_skills: [tor-procurement]
---

# TOR Review Expert - ตรวจสอบ TOR จัดซื้อจัดจ้างภาครัฐ

Expert auditor for Thai government procurement TOR documents per Public Procurement Act B.E. 2560.

## When to Use
- User submits a TOR document for review/checking/auditing
- User asks "ตรวจสอบ TOR" or "check this TOR"
- User wants to find legal compliance issues in a TOR

## Quick Reference - Critical Violations
| Issue | Law | Consequence |
|-------|-----|-------------|
| Spec-locking/favoritism | ม.9 | Void procurement |
| Wrong method for budget | ม.55-56 | Void procurement |
| Contract splitting | ม.120 | Criminal penalty |
| Excessive qualifications | ม.11 | Unfair competition |

## Procedure

### Step 1: Identify basics
- Supply type (6: goods, services, construction, consulting, design, lease)
- Procurement method (3: general invitation, selection, specific)
- Verify method matches budget (≤500K→specific, >500K→e-bidding, S.56(1)→selection)

### Step 2: Check completeness (13 sections)
All TOR must have: background, objectives, qualifications (9 items min), scope, timeline, budget (incl VAT), location, milestones (sum=100%), warranty, penalty (0.01-0.20% ≥100THB/day), evaluation criteria, required documents, guarantee (5%)

### Step 3: Legal compliance (10 checks)
B1-B10 per `references/document_checklist.md`

### Step 4: Consistency (6 checks)
Cross-reference budget↔scope, timeline↔scope, milestones=100%, criteria↔qualifications

### Step 5: Type-specific checks
Construction: BOQ+drawings, IT: SLA+source code, Consulting: man-months+quality≥80%

### Step 6: Language
Formal Thai bureaucratic language, standard phrases, correct numbering

## Output Format
Structured report: status (pass/conditional/fail), risk level (low/medium/high/critical), findings per category (A-E), prioritized recommendations (🔴🟠🟡)

## Pitfalls
- Do NOT fabricate legal article numbers
- If budget is unknown, ASK before judging method compliance
- Agency-specific rules: note "ควรตรวจสอบเพิ่มเติมกับระเบียบภายใน"

## Verification
After producing the report, verify:
- All 13 sections checked
- All 10 legal items checked
- Critical violations flagged prominently
- Recommendations are actionable with specific fix suggestions
