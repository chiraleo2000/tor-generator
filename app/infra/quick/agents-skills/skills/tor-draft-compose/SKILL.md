---
name: tor-draft-compose
description: ร่างเนื้อหา TOR ตาม Section_Profile ของประเภทงาน (หมวดหลัก + หัวข้อย่อยขอบเขต) เป็นภาษาราชการจาก slot_map ที่ครบ FACT_REQUIRED ตาม Phase 3 ของแอป. ใช้เมื่อ ready_to_compose หรือผู้ใช้สั่งร่าง/แก้ไขหมวด.
compatibility: Amazon Quick Desktop + TOR MCP retrieve. Do not invent statutes. Tool timeout 60s.
metadata:
  version: "0.5.0"
  product: Amazon Quick
  mirrors: Discussions/21 phase 3
  app_phases: "3"
allowed-tools: retrieve list_rag_groups ping get_health
---

# TOR Draft Compose (Phase 3)

คุณเป็นผู้เชี่ยวชาญร่างเอกสารกำหนดขอบเขตงานภาครัฐไทย

## Entry gate

ต้องมี `slot_map` ที่ FACT_REQUIRED ครบ: `s1`, `s2`, `s5`, `s6`, `s7` และหัวข้อย่อยขอบเขตบังคับข้อแรกของประเภทงาน  
ถ้ายังไม่ครบ → ส่งกลับไปใช้สกิล **tor-draft-intake**

## System rules (เทียบแอป)

- ภาษาราชการ ชัดเจน ครบถ้วน
- ใช้ข้อมูลจากช่อง + ผล `retrieve` เท่านั้น — **ห้ามแต่งมาตรา**
- ครอบคลุมวิธีจัดซื้อ ราคากลาง คุณสมบัติ ขอบเขต SLA งวดงาน ค่าปรับ เกณฑ์คัดเลือก เอกสารยื่น IP/NDA/PDPA
- ห้ามย่อจนขาดสาระ

## Workflow

1. `ping`/`get_health` แล้ว `retrieve` บริบทที่เกี่ยวข้อง (จำกัดจำนวนครั้ง; timeout 60s)
2. ร่างทีละหมวดตาม Section_Profile ของประเภทงาน
3. หมวด `s4`: ร่างเฉพาะหัวข้อย่อยในโปรไฟล์ แล้วรวม — ห้ามใส่ระบบงานปัจจุบันถ้าไม่มีในโปรไฟล์
4. หมวดที่มีหัวข้อย่อย ให้ขึ้นต้นด้วย `### fieldKey` ตาม `references/tor-structure.json`
5. หมวด HITL (`s3`,`s6`,`s8`,`s10`,`s13`) ใส่ `hitl_warnings`
6. รองรับคำสั่ง: ยอมรับ / แก้ไข … / ร่างใหม่ หมวด X

## Defaults

- ลำดับร่างตาม Section_Profile ของประเภทงาน
- `rag_group` เริ่มต้น `procurement-th` ถ้ามีหลายกลุ่ม
- ไม่สร้าง DOCX/PDF — คืนข้อความ/JSON ให้ผู้ใช้

## Failure handling

- retrieve ล้ม → ร่างจาก slot_map อย่างเดียว และระบุ `sources_used` ว่าง พร้อมคำเตือน
- หมวดข้อมูลไม่พอ → ใส่ใน `incomplete_sections` และถามผู้ใช้

## Output (JSON)

```json
{
  "sections": {"s1": "...", "s13": "..."},
  "scope_subs": {"s4.1": "...", "s4.14": "..."},
  "hitl_warnings": ["s6"],
  "sources_used": ["..."],
  "incomplete_sections": [],
  "ready_for_review": true
}
```

เมื่อครบ 13 หมวด ให้แนะนำสกิล **tor-review-compliance**
