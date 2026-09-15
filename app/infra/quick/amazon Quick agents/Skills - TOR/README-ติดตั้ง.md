# Amazon Quick — Agents / Skills TOR (v0.7.0)

แพ็กเกจสำหรับติดตั้งบน Amazon Quick Desktop / ทีมบน AWS

## ไฟล์ในโฟลเดอร์นี้

- `tor-agents-skills-v0.7.0.zip` — แตกแล้วได้โฟลเดอร์ `agents-skills` ครบชุด
- `README-ติดตั้ง.md` — สรุปสั้น (ไฟล์นี้)

## ติดตั้งบนเครื่อง (local)

1. รัน MCP sidecar `:8767` — ดู [`../README.md`](../README.md)
2. Quick → Connectors → MCP → `http://127.0.0.1:8767/mcp`
3. แตก zip → Import `SKILL.md` ทีละสกิล (kb-retrieve → intake → compose → review)
4. แนบ tools แล้วสร้าง Agent จาก `agents/*.json`

## ติดตั้งบน AWS Cloud

คู่มือเต็ม: [`../คู่มือติดตั้ง-AWS-cloud.md`](../คู่มือติดตั้ง-AWS-cloud.md)

สรุป:

1. เว็บ + nginx/ALB เปิด `https://<โดเมน>/mcp` พร้อม `QUICK_MCP_AUTH_VALUE`
2. Quick → MCP endpoint คลาวด์ + Auth
3. Import Skills จาก zip ชุดเดียวกัน · ผูก connector คลาวด์
4. ผู้ใช้ถาม/ร่างใน Quick ได้ — ส่งออก Word/อนุมัติใช้เว็บแอป

เอกสาร PN ทั้งชุด: [Discussions/36](../../../../Discussions/36-AWS-PN-USER-SETUP-AND-RUNBOOK.md)
