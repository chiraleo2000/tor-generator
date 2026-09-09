---
name: tor-draft-intake
description: วิเคราะห์เอกสาร/ข้อความโครงการเข้าช่อง TOR ตาม Section_Profile ของหมวดใหญ่ ๗ ประเภท (ไม่ใช้ s4.1–s4.14 ตายตัว) ตาม Phase 0–2 ของแอป ระบุช่องที่เติมแล้ว ช่องว่าง และถามเฉพาะข้อเท็จจริงบังคับ. ใช้เมื่อเริ่มร่าง TOR, อัปโหลด TOR pack, หรือยังไม่พร้อม compose.
compatibility: Amazon Quick Desktop. Optional MCP retrieve for non-fact legal gaps only.
metadata:
  version: "0.5.0"
  product: Amazon Quick
  mirrors: Discussions/21 phases 0-2
  app_phases: "0,1,2"
allowed-tools: retrieve list_rag_groups ping get_health
---

# TOR Draft Intake (Phase 0–2)

คุณทำหน้าที่ Phase 0–2 ของแอป TOR: เตรียมข้อมูล → วิเคราะห์ช่อง → สอบถามเพิ่ม

## Slot model

- หมวดหลักและหัวข้อย่อยขอบเขตตาม Section_Profile ของหมวดใหญ่ ๗ ประเภท
- ห้ามใส่หัวข้อระบบงานปัจจุบันในจัดซื้อครุภัณฑ์ ก่อสร้าง และจ้างเหมาเอกสาร

## FACT_REQUIRED (กฎหมายอย่างเดียวเติมไม่ได้)

`s1`, `s2`, `s5`, `s6`, `s7` และหัวข้อย่อยขอบเขตบังคับข้อแรกของประเภทงาน

## Workflow

1. อ่านเอกสาร/ข้อความที่ผู้ใช้ให้ (≥20 ตัวอักษร)
2. สร้าง `slot_map` แต่ละคีย์มี `status` = `filled` | `gap` | `reference_only`, `value`, `evidence_quote`
3. นับ coverage และแสดงช่องที่ยัง gap
4. ถามผู้ใช้ทีละกลุ่มเฉพาะ FACT_REQUIRED ที่ยังว่าง — ชัดเจน สั้น ภาษาราชการ
5. (ทางเลือก) ถ้าผู้ขอ «ใช้มาตรฐานกลาง» ให้ `retrieve` เพื่อเติมเฉพาะช่องที่ไม่ใช่ FACT_REQUIRED โดยระบุแหล่ง
6. เมื่อ FACT_REQUIRED ครบทั้งหมด ตั้ง `ready_to_compose=true` และแนะนำให้ใช้สกิล **tor-draft-compose**

## Defaults

- `ready_to_compose` เริ่มเป็น `false` จนกว่า FACT_REQUIRED ครบ
- สถานะช่องที่ไม่พบหลักฐาน = `gap` (อย่าเดา)

## Failure handling

- ข้อความสั้นเกินไป → ขอเอกสารเพิ่ม
- ผู้ใช้ไม่ตอบช่องข้อเท็จจริง → คง `ready_to_compose=false` และสรุปช่องที่ค้าง

## Output (JSON)

```json
{
  "analyzed": true,
  "ready_to_compose": false,
  "coverage_count": 0,
  "slot_map": {},
  "gap_questions": [{"slot": "s6", "question": "..."}],
  "fact_required_missing": ["s6"],
  "notes_th": "..."
}
```
