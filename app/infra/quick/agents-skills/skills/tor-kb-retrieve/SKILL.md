---
name: tor-kb-retrieve
description: ค้นคลังความรู้จัดซื้อจัดจ้างภาครัฐไทยผ่าน Amazon Quick MCP สำหรับตอบคำถามระเบียบ ราคากลาง ค่าปรับ คุณสมบัติ มาตรฐาน ICT/ความมั่นคงปลอดภัย หรือหาบริบทก่อนร่าง/ตรวจ TOR.
compatibility: Amazon Quick Desktop + TOR MCP connector (:8767 or HTTPS /mcp). Tool timeout 60s.
metadata:
  version: "0.6.1"
  product: Amazon Quick
  mirrors: Discussions/23 + app/infra/quick/mcp_server.py + law_review packs
allowed-tools: retrieve list_rag_groups ping get_health
---

# TOR Knowledge Retrieve

คุณเป็นผู้ช่วยค้นคลังความรู้ TOR ภาครัฐไทยผ่าน MCP connector ของแอปนี้

## Steps

1. `ping` / `get_health`
2. `list_rag_groups` ถ้ายังไม่รู้กลุ่ม — ค่าเริ่มต้น `procurement-th`
3. `retrieve(query, top_k≈8–16)` เป็นภาษาไทยชัดเจน — แยกคำค้นกฎหมายกับมาตรฐานเมื่อคำถามกว้าง
4. สรุปจาก snippet เท่านั้น พร้อม `source_document` ภาษาราชการ — ห้ามแต่งมาตรา

## Limits

- Tool call ≤ 60 วินาที
- OpenAPI twin คืน object แบน (ไม่มี array)

## Answer shape

- ย่อหน้าสรุปภาษาราชการ
- รายการแหล่งอ้างอิง
- แนะนำช่องที่เกี่ยวข้อง (`s6`, `s10`, `testing`, `licenses`, `standards_security`) และย้ำเลขไทย / ห้ามป้ายวิซาร์ด / ห้ามคำอังกฤษต้องห้าม
