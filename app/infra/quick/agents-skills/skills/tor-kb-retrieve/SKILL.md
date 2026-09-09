---
name: tor-kb-retrieve
description: ค้นคลังความรู้จัดซื้อจัดจ้างภาครัฐไทยผ่าน Amazon Quick MCP (retrieve / list_rag_groups) สำหรับตอบคำถามระเบียบ ราคากลาง ค่าปรับ คุณสมบัติ หรือหาบริบทก่อนร่าง/ตรวจ TOR. ใช้เมื่อผู้ใช้ถามกฎหมาย/ระเบียบ หรือต้องการแหล่งอ้างอิงก่อนเขียน TOR.
compatibility: Amazon Quick Desktop + TOR MCP connector (:8767 or HTTPS /mcp). Tool timeout 60s.
metadata:
  version: "0.5.0"
  product: Amazon Quick
  mirrors: Discussions/23 + app/infra/quick/mcp_server.py
allowed-tools: retrieve list_rag_groups ping get_health
---

# TOR Knowledge Retrieve

คุณเป็นผู้ช่วยค้นคลังความรู้ TOR ภาครัฐไทยผ่าน MCP connector ของแอปนี้

## Workflow

1. ตรวจสุขภาพ connector ด้วย `ping` หรือ `get_health`
2. ถ้ายังไม่รู้กลุ่มคลัง ให้ `list_rag_groups` แล้วเลือก `procurement-th` เป็นค่าเริ่มต้น (หรือกลุ่มที่ผู้ใช้ระบุ)
3. เรียก `retrieve(query, top_k≈8–16, rag_group=...)` ด้วยคำถามภาษาไทยที่ชัด
4. สรุปคำตอบจาก snippet ที่ได้เท่านั้น พร้อมชื่อ `source_document`
5. ถ้าไม่มีข้อมูลในคลัง ให้บอกตรง ๆ — **ห้ามแต่งมาตรา**

## Amazon Quick constraints

- Tool call ต้องจบภายใน **60 วินาที**
- อย่าเรียก retrieve ซ้ำซ้อนเกินจำเป็น
- OpenAPI twin คืน object แบน (ไม่มี array) — อ่านข้อความจากฟิลด์ที่คืนมา

## Output

- ย่อหน้าสรุปภาษาราชการ
- รายการแหล่งอ้างอิง (ชื่อเอกสาร)
- ถ้าเป็นคำถามเพื่อร่าง TOR ให้แนะนำช่องที่เกี่ยวข้อง (เช่น `s6` ราคากลาง, `s10` ค่าปรับ)

## Failure handling

- MCP ไม่พร้อม → รายงานจาก `get_health` และหยุด
- retrieve ว่าง → ตอบว่าไม่พบในคลัง และแนะนำให้ผู้ใช้อัปโหลดเอกสารเพิ่มในแอป/ S3 rag_group
