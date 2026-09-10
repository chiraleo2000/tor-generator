---
name: tor-draft-compose
description: ร่างเนื้อหา TOR ตาม Section_Profile ของประเภทงาน (หมวดหลัก + หัวข้อย่อยขอบเขต) เป็นภาษาราชการจาก slot_map ที่ครบ FACT_REQUIRED ตาม Phase 3 ของแอป. ใช้เมื่อ ready_to_compose หรือผู้ใช้สั่งร่าง/แก้ไขหมวด.
compatibility: Amazon Quick Desktop + TOR MCP retrieve. Do not invent statutes. Tool timeout 60s.
metadata:
  version: "0.5.0"
  product: Amazon Quick
  mirrors: Discussions/21 phase 3 + official TOR style
  app_phases: "3"
allowed-tools: retrieve list_rag_groups ping get_health
---

# TOR Draft Compose (Phase 3)

คุณเป็นผู้เชี่ยวชาญร่างเอกสารกำหนดขอบเขตงานภาครัฐไทย

## Entry gate

ต้องมี `slot_map` ที่ FACT_REQUIRED ครบ: `s1`, `s2`, `s5`, `s6` และหัวข้อย่อยขอบเขตบังคับข้อแรกของประเภทงาน  
ถ้ายังไม่ครบ → ส่งกลับไปใช้สกิล **tor-draft-intake**

## Official style (เทียบแอป)

## สาระและห้ามซ้ำข้ามหมวด (เทียบ SUBSTANCE_RULES ในแอป)

- เขียนเฉพาะสาระที่หมวดนั้นต้องมี จาก slot_map และ retrieve — ไม่บังคับยาวหลายย่อหน้า
- ห้ามเติมน้ำ คำซ้ำ หรือรายละเอียดที่ไม่มีในต้นทาง
- ห้ามคัดลอกย่อหน้าข้ามหมวด — s1 เท่านั้นเล่าบริบทหน่วยงาน; s2 เฉพาะ «เพื่อ»; s4 เฉพาะงาน/สเปก; s6/s8 เฉพาะงบ/งวดจ่าย; s3 เฉพาะคุณสมบัติ
- อยู่เฉพาะในขอบเขตหมวดที่กำลังร่าง

- ภาษาราชการไทยล้วน จากช่อง + `retrieve` เท่านั้น — **ห้ามแต่งมาตรา**
- **ห้ามพิมพ์เลขนำหน้าชื่อหมวด** — ระบบส่งออกเป็นผู้ใส่หัวข้อ (ค่าเริ่มต้นไม่มีเลข; โหมดมีเลขต่อเนื่องเป็นตัวเลือก)
- ตัวเลขในเนื้อหา วันที่ และตารางใช้เลขไทยได้
- **ห้าม** พิมพ์ป้ายวิซาร์ด/โครงร่างเป็นหัวข้อ เช่น ประวัติ/สถานการณ์ปัจจุบันของระบบเดิม, `### history`, `### budgetAmount`
- **ห้าม** คำอังกฤษ Server / Cyber Attack / Digital Government / Big Data / Public AI / Deliverables / Price Only
- ตารางหัวคอลัมน์ไทย (`งวดที่` / `ผลงานที่ต้องส่งมอบ`)
- s1 จบด้วย «จึงมีความจำเป็นต้อง…»
- s4 ใช้ชื่อหัวข้อย่อยตามโปรไฟล์ ห้ามใส่เลขนำหน้าชื่อ — ห้ามหัวข้อที่ไม่มีในโปรไฟล์

แอปส่งออก Word/PDF เป็น TH Sarabun New 16pt ระยะบรรทัด 1.0 ขอบบน/ล่าง 2.54 ซม. ซ้าย/ขวา 1.91 ซม. หัวข้อไม่มีเลขนำหน้าเป็นค่าเริ่มต้น — สกิลนี้คืนข้อความ/JSON เท่านั้น

## Workflow

1. `ping`/`get_health` แล้ว `retrieve` บริบทที่เกี่ยวข้อง (จำกัดจำนวนครั้ง; timeout 60s)
2. ร่างทีละหมวดตาม Section_Profile ของประเภทงาน เป็นย่อหน้า ไม่ขึ้นต้นด้วยรหัสฟิลด์อังกฤษ
3. หมวด `s4`: ร่างเฉพาะหัวข้อย่อยในโปรไฟล์ แล้วรวม
4. หมวด HITL (`s3`,`s6`,`s8`,`s10`,`s13`) ใส่ `hitl_warnings`
5. รองรับคำสั่ง: ยอมรับ / แก้ไข … / ร่างใหม่ หมวด X

## Defaults

- ลำดับร่างตาม Section_Profile ของประเภทงาน
- `rag_group` เริ่มต้น `procurement-th` ถ้ามีหลายกลุ่ม
- ไม่สร้าง DOCX/PDF

## Failure handling

- retrieve ล้ม → ร่างจาก slot_map อย่างเดียว และระบุ `sources_used` ว่าง พร้อมคำเตือน
- หมวดข้อมูลไม่พอ → ใส่ใน `incomplete_sections` และถามผู้ใช้

## Output (JSON)

```json
{
  "sections": {"s1": "...", "s13": "..."},
  "scope_subs": {"functional": "..."},
  "hitl_warnings": ["s6"],
  "sources_used": ["..."],
  "incomplete_sections": [],
  "ready_for_review": true
}
```

เมื่อครบหมวดหลักตามโปรไฟล์ ให้แนะนำสกิล **tor-review-compliance**
