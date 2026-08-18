---
name: tor-procurement
description: Draft and review Thai government procurement TOR (Terms of Reference) documents following the Public Procurement Act 2560. Activates when users ask about Thai procurement TOR drafting, reviewing, or legal compliance.
version: 1.0.0
author: Procurement Knowledge Team
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [Government, Procurement, Thai, TOR, Legal]
    related_skills: []
    config:
      - key: tor.language
        description: "Language for TOR output (always Thai bureaucratic)"
        default: "thai-formal"
        prompt: "TOR output language"
      - key: tor.default_penalty_rate
        description: "Default daily penalty rate percentage"
        default: "0.10"
        prompt: "Default penalty rate (0.01-0.20)"
---

# TOR Procurement Expert - Thai Government Procurement

Expert system for drafting and reviewing Thai government procurement TOR (Terms of Reference) following the Public Procurement and Supply Administration Act B.E. 2560.

## When to Use
- User asks to draft a TOR for government procurement
- User asks to review or check an existing TOR document
- User asks about Thai procurement methods, legal requirements, or TOR structure
- User needs help with formal Thai bureaucratic language (ภาษาราชการ) for procurement

## Quick Reference

### Procurement Method Decision (by budget)
| Budget (THB) | Method |
|-------------|--------|
| <= 500,000 | เฉพาะเจาะจง (Specific) |
| > 500,000 (normal) | ประกาศเชิญชวนทั่วไป (e-bidding) |
| S.56(1) conditions | คัดเลือก (Selection) |
| Emergency/sole source | เฉพาะเจาะจง (Special case) |

### Supply Types (6)
1. สินค้า (Goods) - specs, delivery location, warranty
2. งานบริการ (Services) - SLA, KPI, personnel, acceptance
3. ก่อสร้าง (Construction) - BOQ, drawings, supervisor
4. ที่ปรึกษา (Consulting) - team quals, past work, quality >= 80%
5. ออกแบบ/ควบคุม (Design) - professional license, fees per rules
6. เช่า (Lease) - maintenance, return conditions

## Procedure

### Mode A: Drafting TOR
1. **Collect requirements** from user:
   - Project name, agency, supply type (6 types), budget
   - Scope of work, timeline, special conditions
2. **Determine procurement method** using decision rules in `references/method_selection.md`
3. **Select template** based on supply type x method (see `references/template_selection.md`)
4. **Draft TOR** with all 13 standard sections in formal Thai language
5. **Auto-review** against checklist before delivery

### Mode B: Reviewing TOR
1. **Identify** supply type and procurement method
2. **Check completeness** - all required sections present
3. **Check compliance** - 5 categories (A-E) per `references/document_checklist.md`
4. **Report** - structured findings with severity and recommendations

### Language Rules (Critical)
- ALWAYS use formal Thai bureaucratic language (ภาษาราชการ)
- Use: "ดำเนินการ" NOT "ทำ"
- Use: "ผู้ยื่นข้อเสนอ" NOT "ผู้ขาย"
- Use: "เป็นจำนวนเงินทั้งสิ้น X บาท (ตัวอักษร) รวมภาษีมูลค่าเพิ่มและค่าใช้จ่ายทั้งปวงแล้ว"
- Use: "ภายในระยะเวลา X วัน นับถัดจากวันลงนามในสัญญา"
- Full vocabulary guide: `references/tor_writing_guide.md`

### Key Legal Constraints
- No spec-locking or supplier favoritism (Section 9)
- No brand specification without justification
- No excessive qualification requirements
- No contract splitting to avoid thresholds
- Penalty rate: 0.01%-0.20% daily, minimum 100 THB/day
- Contract guarantee: 5% of contract value

## Pitfalls
- Do NOT fabricate legal article numbers - only cite what you're certain of
- Do NOT determine market prices - user must provide actual cost estimates
- Agency-specific rules must come from user input
- Always verify procurement method matches budget threshold

## Verification
- Run the 5-category checklist (A-E) on every drafted TOR
- Confirm method selection matches budget and conditions
- Verify all 13 standard sections are present
- Check formal language compliance (no colloquial terms)
