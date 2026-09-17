# คู่มือติดตั้ง Amazon Quick Agents/Skills บน AWS Cloud

เวอร์ชันแพ็กเกจ **v0.7.1** · Region แนะนำ **`ap-southeast-1`**  
เอกสารนี้สำหรับ **ผู้ดูแลระบบ / IT** ที่จะเปิดให้เจ้าหน้าที่ใช้ Amazon Quick ร่าง-ตรวจ TOR ผ่าน MCP ของแอปบนคลาวด์

> **ไม่ใช่ QuickSight** · Quick เป็น workplace AI ที่เรียกคลังความรู้ของแอปผ่าน HTTPS `/mcp`

แพ็กเกจ zip: [`amazon Quick agents/Skills - TOR/tor-agents-skills-v0.7.1.zip`](amazon%20Quick%20agents/Skills%20-%20TOR/tor-agents-skills-v0.7.1.zip)  
ขั้นตอนบน Desktop (ท้องถิ่น): [`README.md`](README.md)

---

## 1. เลือกเส้นทาง AWS

| เส้น | เมื่อใช้ | เอกสารคู่ |
|------|----------|-----------|
| **ก — PN EC2 + Compose (แนะนำเริ่ม)** | หน่วยงานเล็ก–กลาง · เครื่องเดียว · MCP + เว็บร่วมโฮสต์ | [Discussions/36](../../../Discussions/36-AWS-PN-USER-SETUP-AND-RUNBOOK.md) · [`app/infra/pn-ec2/`](../pn-ec2/) |
| **ข — ECS / Fargate (production HA)** | ต้องการ ALB · RDS · ไม่แพตช์ OS เอง | [Discussions/24](../../../Discussions/24-AWS_CLOUD_OVERVIEW.md)–[27](../../../Discussions/27-AWS_CODE_AND_CUTOVER.md) · [31](../../../Discussions/31-MCP-RAG-AWS-QUICKSTART.md) |

ทั้งสองเส้น **LLM บนคลาวด์เป็น Amazon Bedrock** (`DEPLOYMENT_MODE=cloud`) — ห้ามชี้ production ไป LM Studio

```text
เจ้าหน้าที่ ──► Amazon Quick Desktop
                    │  MCP HTTPS
                    ▼
              https://<โดเมน>/mcp   ← nginx / ALB
                    │
                    ▼
              amazon-quick :8767  →  mcp-rag / backend RAG
                    │
                    ▼
              คลัง (pgvector หรือ S3 Vectors) + Bedrock embed
```

---

## 2. สิ่งที่ต้องมีก่อน (Checklist ผู้ดูแล)

- [ ] เว็บแอป TOR ขึ้นบน AWS แล้ว (`https://<โดเมน>` login ได้)
- [ ] บริการคลัง/RAG พร้อม (seed หรือ ingest อย่างน้อย 1 กลุ่ม เช่น `procurement-th`)
- [ ] โดเมน + **HTTPS (TLS)** ชี้โฮสต์ที่เปิด `/mcp`
- [ ] Security Group เปิด **443** จากเครือข่ายสำนักงาน/VPN (ไม่เปิด DB/Redis สู่ internet)
- [ ] ค่า `QUICK_MCP_AUTH_VALUE` เป็นโทเคนสุ่ม (ไม่ใช่ `changeme_…`)
- [ ] มีสิทธิ์ Amazon Quick **Enterprise / ทีม** ที่สร้าง Connectors ได้
- [ ] ไฟล์ zip Agents/Skills v0.7.1

---

## 3. เส้น ก — PN EC2 (แนะนำ)

### 3.1 ตั้งค่าบนเซิร์ฟเวอร์

1. ตาม [36](../../../Discussions/36-AWS-PN-USER-SETUP-AND-RUNBOOK.md) ให้ `docker compose` ของ PN รันครบ รวม **amazon-quick** และ **nginx (profile `with-nginx`)**
2. ใน `.env` บน EC2 ให้มีอย่างน้อย:

```env
PN_PUBLIC_HOST=tor.example.go.th
QUICK_MCP_AUTH_HEADER=Authorization
QUICK_MCP_AUTH_VALUE=<โทเคนสุ่มยาว>
QUICK_RAG_MCP_URL=http://mcp-rag:8765/mcp
```

3. nginx ต้อง proxy:

| Path สาธารณะ | ปลายทางภายใน |
|--------------|--------------|
| `/` | frontend `:3000` |
| `/api` | backend `:4000` |
| `/mcp` | amazon-quick `:8767` |

4. ตรวจบนเซิร์ฟเวอร์:

```bash
curl -sf https://$PN_PUBLIC_HOST/api/v1/health
curl -sf -X POST "https://$PN_PUBLIC_HOST/mcp" \
  -H "Content-Type: application/json" \
  -H "Authorization: $QUICK_MCP_AUTH_VALUE" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

คาดหวัง: health ผ่าน · MCP ตอบ `tor-amazon-quick` (หรือชื่อ serverInfo ตามอิมเมจ)

### 3.2 ลงทะเบียน Connector ใน Amazon Quick

1. เปิด **Amazon Quick** (Enterprise) → **Connectors** → **Create for your team**
2. เลือก **Model Context Protocol (MCP)**
3. Endpoint: `https://<PN_PUBLIC_HOST>/mcp`
4. Auth: header ชื่อตาม `QUICK_MCP_AUTH_HEADER` (ปกติ `Authorization`) · ค่า = `QUICK_MCP_AUTH_VALUE`
5. บันทึกแล้วทดสอบ tools:
   - `ping` / `get_health`
   - `list_rag_groups`
   - `retrieve` ด้วย `query` ภาษาไทย + `rag_group` (เช่น `procurement-th`) · `top_k` 3–8
6. ต้องได้ข้อความจากเอกสารคลังจริงภายใน **≤ 60 วินาที**

> ถ้า MCP อยู่ใน VPC เท่านั้น: ใช้ **Quick VPC connection** ตามเอกสาร AWS · จุด OAuth (ถ้ามี) ยังต้องอยู่สาธารณะ

### 3.3 ติดตั้ง Skills + Agents (บน Quick Desktop ของผู้ใช้/ต้นแบบทีม)

1. แตก `tor-agents-skills-v0.7.1.zip`
2. **Agents & skills** → **Skills** → **Import from file** → นำเข้า `SKILL.md` ทีละไฟล์:

| ลำดับ | สกิล | งาน |
|------:|------|-----|
| 1 | `tor-kb-retrieve` | ถามระเบียบ/มาตรฐานจากคลัง |
| 2 | `tor-draft-intake` | วิเคราะห์เอกสารเข้าช่อง |
| 3 | `tor-draft-compose` | ร่างหมวด TOR |
| 4 | `tor-review-compliance` | ตรวจ TOR ทั้งฉบับ |

3. ในแต่ละสกิล แนบ MCP tools จาก connector ข้อ 3.2:  
   `retrieve` · `list_rag_groups` · `ping` · `get_health`
4. สร้าง Agent:
   - คัดลอก `prompt` จาก `agents/tor-draft-agent.json` หรือ `tor-review-agent.json`
   - Capabilities → เลือก connector TOR บนคลาวด์
   - Response mode: **Smart** สำหรับร่าง/ตรวจทั้งฉบับ
5. (ถ้ามี) แก้ URL ใน JSON ให้เป็น `https://<โดเมน>/mcp` และใส่ header auth ก่อนแจกให้ทีม

---

## 4. เส้น ข — ECS / ALB (สรุป)

ใช้เมื่อสแตก production เป็น ECS ตามเอกสาร 24–27

1. รันบริการที่เทียบเท่า sidecar `amazon-quick` (หรือ expose MCP จากบริการ retrieve ที่รองรับ Draft 7) หลัง **ALB + ACM**
2. Path rule: `https://<โดเมน>/mcp` → target group ของ MCP (พอร์ตภายในตาม Compose/Task)
3. เก็บ `QUICK_MCP_AUTH_VALUE` ใน **Secrets Manager** — อย่า commit
4. ลงทะเบียน Quick Connector และ Import Skills **เหมือนข้อ 3.2–3.3**
5. ถ้าแอปเรียก MCP พาร์ทเนอร์แยก: ดู [31](../../../Discussions/31-MCP-RAG-AWS-QUICKSTART.md) (`MCP_RAG_SERVERS_JSON`) — คนละเรื่องกับ connector ที่ Quick เรียกเข้ามาที่ `/mcp` ของคุณ

---

## 5. คู่มือสั้นสำหรับผู้ใช้ปลายทาง (หลัง IT ติดตั้งแล้ว)

| งาน | ทำอย่างไร |
|-----|-----------|
| ถามระเบียบ / ราคากลาง | เปิด Quick → ใช้สกิล **tor-kb-retrieve** หรือถาม Agent ที่ต่อ MCP แล้ว |
| เริ่มร่างจากเอกสาร | ส่งข้อความ/สรุปโครงการให้ **tor-draft-intake** จน `ready_to_compose` |
| ร่างหมวด | ใช้ **tor-draft-compose** (ภาษาราชการ · ห้ามป้ายวิซาร์ด/คำอังกฤษต้องห้าม) |
| ตรวจร่าง | วาง TOR ให้ **tor-review-compliance** — จะดึงกฎหมาย+มาตรฐานจากคลัง |
| ส่งออก Word/PDF ราชการ | ใช้**เว็บแอป** Phase 4 (Quick ไม่สร้าง DOCX ให้) |
| อนุมัติโครงการ | ใช้**เว็บแอป** — Quick ไม่แทนระบบอนุมัติ |

กฎเหล็กที่ผู้ใช้ควรรู้:

- ตอบ/ร่างเป็น**ภาษาไทยราชการ**
- อ้างมาตราได้เฉพาะที่มีในผล `retrieve` — **ห้ามแต่งกฎหมาย**
- Tool หมดเวลา 60 วินาที — ถามทีละประเด็นถ้าคำถามกว้าง

---

## 6. เกณฑ์ผ่านก่อนเปิดใช้จริง

- [ ] `https://<โดเมน>/api/v1/health` ผ่าน
- [ ] MCP `initialize` / `tools/list` ผ่านพร้อม auth
- [ ] `retrieve` คืนภาษาไทย + ชื่อเอกสารจริง
- [ ] Skills 4 ตัวถูก Import และผูก connector แล้ว
- [ ] Agent ร่าง/ตรวจตอบได้โดยไม่ 401
- [ ] Security Group ไม่เปิดพอร์ตฐานข้อมูลสู่ internet
- [ ] ไม่มี `changeme_` ใน `QUICK_MCP_AUTH_VALUE`

---

## 7. แก้ปัญหาเบื้องต้น

| อาการ | ตรวจอะไร |
|--------|----------|
| Quick 401 / Unauthorized | โทเคนไม่ตรง · ชื่อ header ผิด · ลืมส่ง `Authorization` |
| Timeout > 60s | คลังใหญ่เกินไป · ลด `top_k` · ตรวจ latency Bedrock/embed · อย่ายิงหลาย retrieve พร้อมกัน |
| ได้ข้อความ stub / ว่าง | `QUICK_RAG_MCP_URL` ชี้ผิด · ยังไม่ ingest/seed · `rag_group` ผิด |
| Connector หา tools ไม่เจอ | แก้ tools บนเซิร์ฟเวอร์แล้วไม่ได้สร้าง connector ใหม่ |
| VPC เข้าไม่ถึง | ตั้ง Quick VPC connection หรือเปิด path ผ่าน ALB สาธารณะอย่างปลอดภัย |
| CORS บนเว็บ (คนละเรื่องกับ Quick) | `CORS_ORIGINS` ต้องเป็น `https://` + โดเมนจริง |

หมุนโทเคน: เปลี่ยน `QUICK_MCP_AUTH_VALUE` → restart compose/task → อัปเดตค่าใน Quick Connector

---

## 8. เอกสารอ้างอิง

| เอกสาร | เนื้อหา |
|--------|---------|
| [`README.md`](README.md) | ติดตั้ง sidecar ท้องถิ่น + Import Skills ละเอียด |
| [`agents-skills/README.md`](agents-skills/README.md) | โครงสร้างแพ็กเกจ Agents/Skills |
| [32-AMAZON-QUICK.md](../../../Discussions/32-AMAZON-QUICK.md) | ภาพรวม Quick ในรีโป |
| [36-AWS-PN-USER-SETUP-AND-RUNBOOK.md](../../../Discussions/36-AWS-PN-USER-SETUP-AND-RUNBOOK.md) | คู่มือ PN Local→EC2 ทั้งชุด |
| [38-AWS-WEBAPP-DEPLOYMENT-PLAN.md](../../../Discussions/38-AWS-WEBAPP-DEPLOYMENT-PLAN.md) | แผน deploy webapp เส้น ก/ข |
| [31-MCP-RAG-AWS-QUICKSTART.md](../../../Discussions/31-MCP-RAG-AWS-QUICKSTART.md) | MCP/Custom RAG ฝั่งแอปเรียกออก (ECS) |
