# Amazon Quick connector (ไม่ใช่ QuickSight)

Sidecar ท้องถิ่นให้ [Amazon Quick](https://aws.amazon.com/quick/) (workplace AI) เรียกคลังความรู้ของแอป TOR ผ่าน **remote MCP** หรือ **OpenAPI 3.0**

Compose ตั้ง `QUICK_RAG_MCP_URL=http://mcp-rag:8765/mcp` เพื่อให้ `retrieve` ใช้ **คลัง pgvector เดียวกับแชท TOR** (ไม่ใช่ stub) — ยกเลิก env นี้เฉพาะตอน unit test ออฟไลน์

เอกสารนี้ **ไม่ใช่** คู่มือติดตั้ง TOR บน AWS ล้วน (`Discussions/31`) — Quick เป็นลูกค้าคลังความรู้ที่คุยกับ HTTP บนพอร์ต **8767**

**ติดตั้งบน AWS Cloud:** [`คู่มือติดตั้ง-AWS-cloud.md`](คู่มือติดตั้ง-AWS-cloud.md) (เส้น PN EC2 + ECS/ALB + คู่มือผู้ใช้สั้น)

แพ็กเกจ Agents/Skills (พร้อม zip): [`amazon Quick agents/Skills - TOR/`](amazon%20Quick%20agents/Skills%20-%20TOR/)  
รายละเอียดไฟล์ต้นทาง: [`agents-skills/README.md`](agents-skills/README.md)

---

## ข้อจำกัดจากเอกสาร AWS

- Remote MCP เท่านั้น (ไม่มี stdio) · HTTP JSON-RPC ที่ `/` หรือ `/mcp`
- `tools/list` → `inputSchema.required` ต้องเป็น **array แบบ Draft 7** ไม่ใช่ boolean ต่อ property
- Tool call หมดเวลาที่ **60 วินาที**
- สูงสุด **100** เครื่องมือ — รายการถูกแช่แข็งตอนลงทะเบียน connector
- OpenAPI: JSON 3.0+ · ห้าม `type: array` ใน request/response · ทุก operation ต้องมี `operationId` + คำอธิบาย

---

## รัน sidecar บนเครื่อง

```bash
docker compose -p tor-app --env-file .env up -d mcp-rag
docker compose -p tor-app --env-file .env --profile amazon-quick up -d amazon-quick
```

| จุดตรวจ | URL |
|---------|-----|
| Health | `GET http://127.0.0.1:8767/health` (ดู `rag.reachable`) |
| REST retrieve | `POST http://127.0.0.1:8767/retrieve` body `{"query":"..."}` |
| MCP | `POST http://127.0.0.1:8767/mcp` |

- **8767** = Amazon Quick sidecar  
- **8765** = `mcp-rag` (pgvector จริง)  
- **8766** = stub ทางเลือก (profile `mcp-stub`)

โปรดักชัน: ใส่ TLS ด้านหน้า · คง `retrieve` ต่ำกว่า 60 วินาที · ตั้ง `QUICK_MCP_AUTH_VALUE` ถ้าต้องการ Bearer

---

## ติดตั้ง Agent / Skills ใน Amazon Quick (ภาษาไทย)

เป้าหมาย: ให้ Quick Desktop มีสกิลร่าง/ตรวจ TOR และ agent ที่เรียก MCP `retrieve` ได้เหมือนเวิร์กโฟลว์แอป (ขั้น 0–4)

### ขั้นตอนที่ 0 — เตรียมไฟล์

1. แตก zip จากโฟลเดอร์  
   `app/infra/quick/amazon Quick agents/Skills - TOR/`  
   หรือใช้โฟลเดอร์ต้นทาง `app/infra/quick/agents-skills/` โดยตรง
2. ใน zip มีอย่างน้อย:
   - `skills/*/SKILL.md` — นำเข้า Quick ได้โดยตรง
   - `agents/*.json` — คัดลอก `prompt` ไปวางใน Agent
   - `references/*.json` — อ้างอิงโครงหมวด + กฎตรวจ (แนบในสกิลถ้าต้องการ)
   - `manifest.json` — ดัชนีเวอร์ชันแพ็กเกจ

### ขั้นตอนที่ 1 — ลงทะเบียน MCP connector (ทำก่อน Agent)

1. เปิด **Amazon Quick Desktop** (ต้องมีสิทธิ์ทีม/องค์กรตามที่หน่วยงานเปิดให้)
2. ไปที่ **Connectors** → **Create for your team** → **Model Context Protocol (MCP)**
3. ใส่ Endpoint:
   - ทดสอบบนเครื่อง: `http://127.0.0.1:8767/mcp`
   - ทีม/คลาวด์: `https://<โฮสต์สาธารณะหรือ VPC>/mcp`
4. Auth:
   - ท้องถิ่น: ไม่ต้องใส่ (ถ้าไม่ได้ตั้ง `QUICK_MCP_AUTH_VALUE`)
   - โปรดักชัน: ใส่ Bearer ตามค่าที่ตั้งไว้
5. บันทึก connector แล้วทดสอบถามสั้น ๆ เช่น «หลักประกันผลงาน» — ต้องได้ `source_document` จากคลังจริง ไม่ใช่ข้อความ stub
6. **ทางเลือก OpenAPI:** Import ไฟล์ `openapi-tor.json` ในโฟลเดอร์นี้แทน MCP
7. ถ้าแก้รายการ tools ใน sidecar แล้ว → **ลบแล้วสร้าง connector ใหม่** (รายการ tools ถูกแช่แข็งตอนลงทะเบียน)

> เซิร์ฟเวอร์ในเครือข่ายส่วนตัวอาจต้องใช้ Quick VPC connection · จุด OAuth (ถ้ามี) ต้องอยู่บนอินเทอร์เน็ตสาธารณะตามเอกสาร AWS

### ขั้นตอนที่ 2 — นำเข้า Skills (แนะนำลำดับนี้)

1. เปิด **Agents & skills** → **Skills** → **+ Create** → **Import from file**
2. เลือกไฟล์ `SKILL.md` **ทีละสกิล** ตามลำดับ:

| ลำดับ | โฟลเดอร์ | ใช้เมื่อ |
|------:|----------|---------|
| 1 | `skills/tor-kb-retrieve/SKILL.md` | ถามระเบียบ / ราคากลาง / มาตรฐานจากคลัง |
| 2 | `skills/tor-draft-intake/SKILL.md` | วิเคราะห์เอกสารเข้าช่อง (Phase 0–2) |
| 3 | `skills/tor-draft-compose/SKILL.md` | ร่างหมวด TOR (Phase 3) |
| 4 | `skills/tor-review-compliance/SKILL.md` | ตรวจ TOR ทั้งฉบับ (Phase 4 /review) |

3. ในรายละเอียดแต่ละสกิล **แนบ MCP tools** จาก connector TOR:  
   `retrieve` · `list_rag_groups` · `ping` · `get_health`
4. (ทางเลือก) แนบ reference: `references/tor-structure.json` และ `references/compliance-rules.json`

### ขั้นตอนที่ 3 — ตั้ง Agents (แชท / Mission Control)

1. สร้าง Agent ใหม่ (หรือ scheduled task)
2. คัดลอกข้อความจากฟิลด์ **`prompt`** ใน:
   - `agents/tor-draft-agent.json` — ช่วยร่างครบ intake → compose
   - `agents/tor-review-agent.json` — ช่วยตรวจ TOR / Phase 4
3. **Capabilities** → เลือก MCP connector TOR ที่ลงทะเบียนในขั้นตอนที่ 1
4. Response mode แนะนำ:
   - **Smart** — ร่าง/ตรวจทั้งฉบับ
   - **Balanced** — ถามคลังสั้น ๆ
5. (โปรดักชัน) แก้ `mcpServers.tor-rag.url` ใน JSON ให้เป็น URL จริง และใส่ `Authorization` ถ้ามี auth

### ขั้นตอนที่ 4 — ทดสอบเร็วใน Quick

พิมพ์คำสั่งประมาณนี้:

```text
use tor-kb-retrieve: หลักประกันผลงาน / ราคากลาง
use tor-draft-intake: (วางข้อความโครงการ ≥20 ตัวอักษร)
use tor-draft-compose: ร่างหมวด s6 จาก slot_map นี้ ...
use tor-review-compliance: (วาง TOR เต็มฉบับ)
```

คาดหวัง: มีการเรียก `retrieve` และอ้างชื่อเอกสารจากคลัง · ห้ามแต่งมาตราที่ไม่มีในบริบท

### สิ่งที่ Quick ไม่ทำแทนเว็บแอป

| ความสามารถ | ยังอยู่ที่เว็บแอป |
|------------|-------------------|
| อัปโหลดโครงการ / สถานะอนุมัติ | `/projects`, dashboard |
| ส่งออก DOCX/PDF (TH Sarabun) | Phase 4 export |
| RuleEngine คะแนน bit-identical | backend `rule_engine` |
| Ingest คลังเข้า S3 Vectors | API PN KB |

Quick = **ผู้ช่วยค้นคลัง + ร่าง/ตรวจข้อความ** คู่กับแอป ไม่ใช่ระบบอนุมัติ

---

## ติดตั้งบน AWS Cloud (สรุป)

คู่มือเต็มภาษาไทย: **[`คู่มือติดตั้ง-AWS-cloud.md`](คู่มือติดตั้ง-AWS-cloud.md)**

| เส้น | Endpoint ที่ใส่ใน Quick | เอกสารคู่ |
|------|-------------------------|-----------|
| **ก PN EC2** (แนะนำเริ่ม) | `https://<โดเมน>/mcp` + `QUICK_MCP_AUTH_VALUE` | [Discussions/36](../../../Discussions/36-AWS-PN-USER-SETUP-AND-RUNBOOK.md) |
| **ข ECS + ALB** | `https://<โดเมน>/mcp` หลัง ACM/ALB | [Discussions/24](../../../Discussions/24-AWS_CLOUD_OVERVIEW.md)–[27](../../../Discussions/27-AWS_CODE_AND_CUTOVER.md) · [31](../../../Discussions/31-MCP-RAG-AWS-QUICKSTART.md) |

ลำดับสั้นบนคลาวด์:

1. ให้เว็บ + RAG ขึ้น HTTPS แล้ว · nginx/ALB ส่ง `/mcp` → sidecar `:8767`
2. ตั้งโทเคน `QUICK_MCP_AUTH_VALUE` (ห้าม `changeme_`)
3. Quick → Connectors → MCP → URL คลาวด์ + Auth
4. Import Skills จาก zip · ผูก tools · สร้าง Agent จาก `agents/*.json`
5. ทดสอบ `retrieve` ≤ 60 วินาที ได้เอกสารจริง

ผู้ใช้ปลายทางใช้สกิลใน Quick ได้ทันทีหลัง IT ทำข้อ 1–4 — ส่งออก Word/อนุมัติยังทำในเว็บแอป

---

## ไฟล์ในรีโป

| Path | บทบาท |
|------|--------|
| `mcp_server.py` | Remote MCP + REST `/health` `/retrieve` |
| `openapi-tor.json` | OpenAPI 3.0 สำหรับ connector แบบ OpenAPI |
| `agents-skills/` | ต้นทาง Agents + Skills (JSON + `SKILL.md`) |
| `amazon Quick agents/Skills - TOR/` | **zip พร้อมแจก** สำหรับติดตั้งบน Quick |
| `คู่มือติดตั้ง-AWS-cloud.md` | แนวทางติดตั้งบน AWS + คู่มือผู้ใช้สั้น |
| Compose profile `amazon-quick` | รัน sidecar พอร์ต 8767 |

เอกสารเพิ่ม: [Discussions/32-AMAZON-QUICK.md](../../../Discussions/32-AMAZON-QUICK.md) · [36 PN runbook](../../../Discussions/36-AWS-PN-USER-SETUP-AND-RUNBOOK.md)
