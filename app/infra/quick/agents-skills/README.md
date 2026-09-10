# Amazon Quick — Agents & Skills สำหรับร่าง/ตรวจ TOR

แพ็กเกจนี้สะท้อนกระบวนการของแอป TOR v0.5.0 (5 ขั้นร่าง + ตรวจสอบล้วน) ให้รันบน **Amazon Quick** (workplace AI) โดยเรียกคลังความรู้ผ่าน MCP connector ที่มีอยู่แล้ว — **ไม่ใช่ QuickSight**

| แอป (Next.js/FastAPI) | Amazon Quick |
|------------------------|--------------|
| Phase 0–2 intake | Skill `tor-draft-intake` |
| Phase 3 compose | Skill `tor-draft-compose` |
| Phase 4 + `/review` | Skill `tor-review-compliance` |
| `/chat` KB Q&A | Skill `tor-kb-retrieve` |
| Orchestration | Agents `tor-draft-agent` / `tor-review-agent` |
| pgvector / S3 Vectors RAG | MCP `retrieve` บน `:8767` หรือ `https://<ec2>/mcp` |

## โครงสร้าง

```text
agents-skills/
  manifest.json                 # ดัชนีทั้งหมด
  agents/
    tor-draft-agent.json        # Agent ร่าง TOR
    tor-review-agent.json       # Agent ตรวจ TOR
  skills/
    tor-kb-retrieve/            # skill.json + SKILL.md
    tor-draft-intake/
    tor-draft-compose/
    tor-review-compliance/
  references/
    tor-structure.json          # 13 หมวด + 27 ช่อง + phase gates
    compliance-rules.json       # RuleEngine + law queries
```

- **`skill.json`** — คำจำกัดความแบบพกพา (instructions, tools, structured_output) สำหรับ Automate Custom Agent / เก็บใน repo
- **`SKILL.md`** — ไฟล์ที่ Amazon Quick Desktop **Import from file** รับโดยตรง
- **`agents/*.json`** — รูปแบบ agent (name, prompt, mcpServers, tools) ใช้วาง prompt + แนบ MCP ใน Quick / Amazon Q CLI

## สิ่งที่ต้องมีก่อนใช้

1. MCP sidecar สุขภาพดี  
   `docker compose --profile amazon-quick up -d amazon-quick`  
   หรือ PN EC2: `https://<โดเมน>/mcp` ([Discussions/36](../../../../Discussions/36-AWS-PN-USER-SETUP-AND-RUNBOOK.md))
2. ลงทะเบียน connector ใน Quick → MCP endpoint  
   ดู [app/infra/quick/README.md](../README.md) และ [Discussions/32](../../../../Discussions/32-AMAZON-QUICK.md)
3. (โปรดักชัน) ใส่ `QUICK_MCP_AUTH_VALUE` แล้วอัปเดต `mcpServers.tor-rag.headers` ใน agent JSON

## นำเข้า Skills (Quick Desktop)

1. **Agents & skills** → **Skills** → **+ Create** → **Import from file**
2. เลือกไฟล์ `SKILL.md` ทีละสกิล (แนะนำลำดับ):
   - `tor-kb-retrieve`
   - `tor-draft-intake`
   - `tor-draft-compose`
   - `tor-review-compliance`
3. ในรายละเอียดสกิล แนบ MCP tools: `retrieve`, `list_rag_groups`, `ping`, `get_health`
4. (ทางเลือก) แนบ reference: `tor-structure.json`, `compliance-rules.json`

## ตั้ง Agents

### แชท / Mission Control (Quick Desktop)

1. สร้าง agent หรือ scheduled task
2. วางข้อความจากฟิลด์ `prompt` ใน `agents/tor-draft-agent.json` หรือ `tor-review-agent.json`
3. Capabilities → เลือก MCP connector TOR
4. Response mode: **Smart** สำหรับร่าง/ตรวจทั้งฉบับ, **Balanced** สำหรับถามคลังสั้น ๆ

### Amazon Q Developer CLI (ถ้าใช้คู่กัน)

คัดลอก JSON ไปที่ `.amazonq/cli-agents/tor-draft-agent.json` แล้วแก้ `mcpServers.tor-rag.url` ให้ชี้ endpoint จริง

### Quick Automate Custom Agent

คัดลอก `instructions` + `structured_output` จาก `skill.json` ใส่ขั้น Custom Agent; Actions = MCP / REST ตาม connector

## การแมปกระบวนการแอป

```text
ผู้ใช้ส่งเอกสาร
  → tor-draft-intake     (slot_map, gap_questions, ready_to_compose)
  → tor-draft-compose    (sections s1–s13 + scope_subs)
  → tor-review-compliance (quality_score, findings ก/ข, suggestions)
```

กฎที่สะท้อนจากแอป:

- FACT_REQUIRED: `s1,s2,s5,s6,s7` + หัวข้อย่อยขอบเขตบังคับข้อแรกของประเภทงาน
- HITL เตือน: `s3,s6,s8,s10,s13`
- คะแนนผ่านโทน ≥ 70 (คำเตือน ไม่บล็อก)
- ร่างเป็นภาษาราชการไทย เลขไทย ห้ามป้ายวิซาร์ด/`### history` และคำอังกฤษต้องห้าม
- ห้ามแต่งมาตรา — `legal_basis` ต้องมาจาก retrieve
- Tool timeout 60 วินาทีต่อครั้ง
- ส่งออก Word/PDF ของแอป: TH Sarabun New 16pt ระยะบรรทัด 1.0 ขอบบน/ล่าง 2.54 ซม. ซ้าย/ขวา 1.91 ซม. (Quick คืนข้อความอย่างเดียว)

## สิ่งที่ Quick **ไม่** ทำแทนแอป

| ความสามารถ | ยังอยู่ที่เว็บแอป |
|------------|-------------------|
| อัปโหลด GridFS / โครงการ / สถานะอนุมัติ | `/projects`, dashboard |
| ส่งออก DOCX/PDF (TH Sarabun) | Phase 4 export |
| RuleEngine ตัวเลข bit-identical | backend `rule_engine` (Quick เป็น checklist + LLM ใกล้เคียง) |
| Ingest S3 Vectors | `POST /api/v1/pn/kb/...` |

Quick เป็น **ลูกค้าคลังความรู้ + ผู้ช่วยร่าง/ตรวจ** คู่กับแอป ไม่ใช่ทดแทนระบบอนุมัติ

## ทดสอบเร็ว

```text
use tor-kb-retrieve: หลักประกันผลงาน / ราคากลาง
use tor-draft-intake: (วางข้อความโครงการ ≥20 ตัวอักษร)
use tor-draft-compose: ร่างหมวด s6 จาก slot_map นี้ ...
use tor-review-compliance: (วาง TOR เต็มฉบับ)
```

คาดหวัง: `retrieve` คืน `source_document` จากคลังจริง ไม่ใช่ข้อความ stub
