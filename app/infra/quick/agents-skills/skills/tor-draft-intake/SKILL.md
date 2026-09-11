---
name: tor-draft-intake
description: วิเคราะห์เอกสาร/ข้อความโครงการเข้าช่อง TOR ตาม Section_Profile ของหมวดใหญ่ ๗ ประเภท (ไม่ใช้ s4.1–s4.14 ตายตัว) ตาม Phase 0–2 ของแอป v0.6.1 ระบุช่องที่เติมแล้ว ช่องว่าง และถามเฉพาะข้อเท็จจริงบังคับ. ใช้เมื่อเริ่มร่าง TOR หรือยังไม่พร้อม compose.
compatibility: Amazon Quick Desktop. Optional MCP retrieve for non-fact legal/standards gaps only.
metadata:
  version: "0.6.1"
  product: Amazon Quick
  mirrors: Discussions/21 phases 0-2 + section_profile
  app_phases: "0,1,2"
allowed-tools: retrieve list_rag_groups ping get_health
---

# TOR Draft Intake (Phase 0–2)

คุณทำหน้าที่ Phase 0–2 ของแอป TOR v0.6.1: เตรียมข้อมูล → วิเคราะห์ช่อง → สอบถามเพิ่ม

## Slots

- ตาม Section_Profile ของ `Procurement_Category` (7 ประเภท)
- ห้ามหัวข้อระบบงานปัจจุบันใน buy_goods / construction / hire_service
- hire_develop ใช้รหัส semantic (`functional`, `testing`, `licenses`, …) — **อย่าแมป testing = s4.8**

## FACT_REQUIRED

`s1`, `s2`, `s5`, `s6` + หัวข้อย่อยขอบเขตบังคับข้อแรกของประเภทงาน

## Workflow

1. อ่านเอกสาร (≥20 ตัวอักษร) และระบุประเภทงาน
2. สร้าง `slot_map` (`filled|gap|reference_only` + value + evidence_quote)
3. ถามเฉพาะ FACT_REQUIRED ที่ยังว่าง
4. (ทางเลือก) `retrieve` มาตรฐานกลางเพื่อเติมช่องที่ไม่ใช่ FACT_REQUIRED
5. เมื่อครบ → `ready_to_compose=true` → ไป **tor-draft-compose**

## Forbidden

- ตั้ง `ready_to_compose` ทั้งที่ FACT_REQUIRED ยังว่าง
- แต่งงบ/ระยะเวลา/สถานที่เอง
- ร่างหมวดเต็มในสกิลนี้

## Output (JSON)

```json
{
  "analyzed": true,
  "ready_to_compose": false,
  "procurement_category": "hire_develop",
  "coverage_count": 0,
  "slot_map": {},
  "gap_questions": [],
  "fact_required_missing": [],
  "notes_th": "..."
}
```
