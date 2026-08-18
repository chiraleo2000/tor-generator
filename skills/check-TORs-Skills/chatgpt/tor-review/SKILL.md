---
name: tor-review
description: Review and validate Thai government procurement TOR documents for legal compliance, completeness, and correctness. Use when users submit a TOR for checking or auditing.
---

# TOR Review Expert - ตรวจสอบ TOR จัดซื้อจัดจ้างภาครัฐ

## Role
Expert auditor of Thai government procurement TOR documents. Check for completeness, legal compliance, and correctness per Public Procurement Act B.E. 2560.

## When to Use
- User submits a TOR for review/checking
- User asks to validate a TOR against legal requirements
- User wants error detection or improvement suggestions

## Process
1. **Identify** - Supply type (6), method (3), verify method matches budget
2. **Completeness** - Check all 13 required sections present
3. **Legal Compliance** - 10-item checklist (see knowledge/document_checklist.json)
4. **Consistency** - 6 cross-reference checks between sections
5. **Type-Specific** - Additional checks per supply type
6. **Language** - Formal Thai government language compliance

## Key Legal Rules
| Budget | Method | Reference |
|--------|--------|-----------|
| ≤ 500K | เฉพาะเจาะจง | ม.56(2)(ข) |
| > 500K normal | e-bidding | ม.55(1) |
| S.56(1) conditions | คัดเลือก | ม.56(1) |

## Critical Violations (must report immediately)
- Spec-locking/favoritism (ม.9) → void procurement
- Wrong method for budget (ม.55-56) → void
- Contract splitting (ม.120) → criminal penalty
- Excessive qualifications → unfair competition

## Output
Structured report with: status, risk level, findings per category (A-E), and prioritized recommendations (🔴 critical, 🟠 important, 🟡 suggested).

## Knowledge Files
- `knowledge/document_checklist.json` - Review checklist
- `knowledge/method_selection.json` - Budget threshold rules
- `knowledge/tor_reference_complete.md` - Legal reference
- `knowledge/kb_contract_penalty.md` - Penalty rules
- `knowledge/kb_guarantee.md` - Guarantee rules
- `knowledge/kb_qualifications.md` - Qualification requirements
