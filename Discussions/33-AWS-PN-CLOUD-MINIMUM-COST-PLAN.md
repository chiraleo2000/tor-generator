# 33 — PN Cloud: Cohere Embed 4 → S3 Vectors → MCP (บน EC2)

Region: **`ap-southeast-1`** · ผู้ใช้จำกัด · **ไม่มี Fargate**  
ไม่ใช่ production เต็มชุด ECS [24](24-AWS_CLOUD_OVERVIEW.md)–[27](27-AWS_CODE_AND_CUTOVER.md) — ใกล้ทางลัด [20](20-AWS_BEDROCK_SETUP.md) แต่ล็อก Embed 4 + S3 Vectors + multi-RAG

ฉบับ PDF: [33-AWS-PN-CLOUD-MINIMUM-COST-PLAN.pdf](33-AWS-PN-CLOUD-MINIMUM-COST-PLAN.pdf) · เครื่องมือ: [34](34-AWS-PN-TOOLS-LIST.md) · deploy + `.env`: [35](35-AWS-PN-DEV-AND-DEPLOY.md) · **คู่มือผู้ใช้ Local→AWS + งานมือ:** [36](36-AWS-PN-USER-SETUP-AND-RUNBOOK.md) · แพ็กเกจ: [`app/infra/pn-ec2/`](../app/infra/pn-ec2/)

## การตัดสินใจที่ล็อกแล้ว

| รายการ | ค่าที่ใช่ |
|--------|-----------|
| Compute | **EC2 1 เครื่อง** (Docker Compose) — รัน MCP + webapp/API |
| Embedding | **Cohere Embed 4** บน Bedrock (`cohere.embed-v4:0`) |
| Vector DB | **Amazon S3 Vectors** |
| ต้นฉบับ / หลาย RAG | **S3** หนึ่งบัคเก็ต · หลาย `rag_group` |
| ค้น / RAG | **MCP** บน EC2 (+ OpenAPI) · เลือก `rag_group` ได้ |
| ขนาด chunk | **~4,096 tokens / chunk** |
| นำเข้า | **API บน EC2** (+ โค้ดเรียก API เดียวกัน) |
| ไม่ใช้ | **ECS Fargate** · ALB (ทางเลือก) · RDS/OpenSearch/Neptune |

```text
                    ┌──────────── EC2 (Compose) ────────────┐
[ผู้ใช้ / โค้ด] ──► │  Webapp + API  /pn/kb/*               │
                    │  MCP :8767  (retrieve, list_rag_groups)│
                    └──────────┬──────────────┬─────────────┘
                               │              │
                         Bedrock Embed 4   S3 + S3 Vectors
```

หลาย RAG: `app/infra/pn/rag-groups.yaml` · API `/api/v1/pn/kb/*` · MCP `list_rag_groups` + `retrieve(rag_group=...)`

---

## 1. ทำไมเป็น EC2 (ไม่ใช่ Fargate)

| | **EC2 (แผนนี้)** | Fargate (ยกเลิกใน PN) |
|--|------------------|------------------------|
| รัน MCP + webapp | เครื่องเดียว Compose | หลาย task / บริการแยก |
| เข้าถึง S3 / KB | IAM instance profile | task role |
| ดูแล | SSH/SSM + Docker — ทีมคุ้นแบบ [20](20-AWS_BEDROCK_SETUP.md) | ต้องรู้ ECS/ALB |
| ต้นทุนคงที่ | ชัดเจนรายเดือนต่อ instance | จ่ายตาม vCPU-ชม. + มักมี ALB |
| Deploy แอป | `git pull` / `docker compose up` บนเครื่อง | push image → ECS service |

PN ใช้ EC2 เป็นทั้ง **MCP host**, **หน้า/API จัดการ Knowledge Base (S3)**, และ **แหล่ง deploy แอป** ของโครงการนี้

---

## 2. เครื่องมือบนเครื่อง EC2

| ชิ้น | ที่รัน / บริการ | บทบาท |
|------|-----------------|--------|
| EC2 (เช่น **t3.small** หรือ **t3.medium**) | Amazon Linux 2023 / Ubuntu | host เดียว |
| Docker Compose | บน EC2 | ยกสแตกแอป + MCP |
| MCP | `app/infra/quick/mcp_server.py` (:8767) | Quick / Claude Code |
| Webapp + API | Next.js + FastAPI (Compose) | อัปโหลด/ตรวจ/ดูคลัง S3 |
| S3 | บัคเก็ตโครงการ | ต้นฉบับ + multi-RAG prefix |
| S3 Vectors | index ต่อ `rag_group` | embedding chunks |
| Bedrock | Embed 4 | ingest + query |
| IAM instance profile | บน EC2 | `bedrock:InvokeModel`, S3, S3 Vectors |
| HTTPS | **nginx บน EC2** + ใบรับรอง (Let's Encrypt หรือ ACM นำเข้า) | ไม่บังคับ ALB |
| ความลับ | `.env` บนเครื่อง **หรือ** Secrets Manager | MCP/API token |
| งบ | AWS Budgets | เพดาน Bedrock + EC2 |

**มิติเวกเตอร์:** ล็อกตอนสร้าง index (เช่น **1024**) — เปลี่ยนมิติ = index ใหม่ + re-embed ทั้งคลัง

---

## 3. นโยบาย Chunk = ~4,096 tokens

| กติกา | ค่า |
|-------|-----|
| `target_chunk_tokens` | **4096** |
| `overlap_tokens` | **256–512** |
| `top_k` ค่าเริ่ม MCP | **3** (สูงสุดแนะนำ **5**) |
| งบข้อความต่อคำขอ | ~**12K tokens** (3 × 4096) |
| Timeout Quick | &lt; **60 วินาที** |

อย่าคืนทั้งไฟล์ต้นฉบับใน MCP — คืนเฉพาะ chunk + ชื่อแหล่ง + score

---

## 4. Ingest และค้น

### Ingest — ง่ายสุด = API บน EC2

```text
POST /api/v1/pn/kb/upload  (+ rag_group)
  → S3 sources/ + manifest + verify
  → (ขั้นถัดไป) chunk 4096 → Embed 4 → S3 Vectors
```

| วิธี | ใช้ไหม |
|------|--------|
| API บน webapp (EC2) | **แนะนำ** |
| โค้ดเรียก API เดียวกัน | ได้ |
| Direct AWS SDK | ได้ แต่ยากกว่า |
| MCP | **ไม่ใช้ ingest** |

### ค้น — MCP บน EC2

```text
list_rag_groups → เลือก id
retrieve(query, rag_group=...) → Embed 4 → S3 Vectors → ชิ้นข้อความ
```

Amazon Quick ชี้ `https://<ec2-หรือ-โดเมน>/mcp` (nginx proxy ไป :8767)

---

## 5. Workflows

### A — ติดตั้งครั้งแรก

```text
1. สร้าง EC2 + IAM role (Bedrock + S3 + S3 Vectors) + SG (22/SSM, 80/443)
2. สร้าง S3 + S3 Vectors index ต่อ rag_group
3. เปิด Bedrock → cohere.embed-v4:0
4. ติดตั้ง Docker · clone รีโป · docker compose up (webapp + MCP + deps ที่ต้องใช้)
5. ตั้ง nginx HTTPS · Budgets · allow-list ผู้ใช้
6. Sync คลังเริ่มต้น · batch ingest
7. ต่อ Amazon Quick → https://.../mcp
8. ทดสอบ upload API + retrieve MCP
```

### B — Deploy / อัปเดตแอปบน EC2

```text
SSM หรือ SSH → git pull → docker compose build/up -d
(หรือ CI ไปยัง EC2 ทีหลัง — ไม่ใช้ Fargate)
```

### C — เพิ่มเอกสาร / ค้นประจำวัน

เหมือนเดิม: upload ผ่าน API · ค้นผ่าน MCP ด้วย `rag_group`

---

## 6. ประเมินต้นทุนใหม่ (ไม่มี Fargate)

ตัวเลข order-of-magnitude ใน **ap-southeast-1** — ตรวจ Pricing Calculator ก่อนจัดซื้อ

### 6.1 Compute (แทน Fargate + ALB)

| ตัวเลือก EC2 | ประมาณ On-Demand / เดือน* | เหมาะเมื่อ |
|--------------|---------------------------|-----------|
| **t3.small** (2 vCPU / 2 GB) | ~**$15–20** | MCP + API เบา ๆ, ผู้ใช้จำกัด |
| **t3.medium** (2 vCPU / 4 GB) | ~**$30–40** | webapp + MCP + Compose หลายบริการ |
| EBS gp3 ~30–50 GB | ~**$3–5** | ดิสก์ระบบ |
| Elastic IP (ติดเครื่อง) | **$0** | |
| nginx HTTPS บนเครื่อง | **$0** | ไม่เปิด ALB |

\*ยังไม่รวม Savings Plans / Reserved — จอง 1 ปีมักถูกกว่า

**เทียบของเก่า (ยกเลิกใน PN):** Fargate เล็ก + ALB มัก ~$20–40/เดือน และดูแลคนละแบบ — ย้ายมา EC2 เครื่องเดียวต้นทุนคงที่ใกล้เคียงหรือถูกกว่าเมื่อไม่จ่าย ALB

### 6.2 ข้อมูล + AI (เหมือนเดิม)

| รายการ | ประมาณการ |
|--------|-----------|
| Cohere Embed 4 | **~$0.12 / 1M tokens** |
| Seed 10M tokens | ~$1.20 |
| Seed 500M tokens | ~$60 |
| Query 10k×~100 token/เดือน | ~$0.12 |
| S3 ต้นฉบับ | น้อยตอนเริ่ม |
| S3 Vectors ~1 TB | ~**$60 / เดือน** |
| S3 Vectors ~2 TB | ~**$120 / เดือน** |

### 6.3 รวมแนวโน้มรายเดือน

| สถานการณ์ | ประมาณการ (ไม่รวมแชท Quick หนัก) |
|-----------|----------------------------------|
| **ปี 1** — EC2 t3.small + คลังยังเล็ก | ~**$25–50 / เดือน** |
| **ปี 1** — EC2 t3.medium + ใช้งานปกติ | ~**$40–70 / เดือน** |
| **ปี 2** — + S3 Vectors ~1 TB | ~**$90–160 / เดือน** |
| **ปี 2** — + ~2 TB | ~**$150–220 / เดือน** |

งบระเบิดเร็วสุดยังเป็น **LLM แชทของ Amazon Quick** ไม่ใช่ EC2 หรือ embed คำถามสั้น

### 6.4 สิ่งที่ตัดออกจากงบ PN

- ECS Fargate (CPU/RAM-ชม.)
- ALB (ถ้าใช้ nginx บน EC2)
- NAT Gateway หลายตัว (ถ้า EC2 อยู่ public subnet + SG เข้ม — PN ยอมได้; หรือใช้ VPC endpoint S3/Bedrock ลด outbound)

---

## 7. ความปลอดภัย (administrative)

- SG: เปิด 443 เฉพาะ IP สำนักงาน / VPN · SSM แทนการเปิด SSH กว้าง
- IAM instance profile จำกัด ARN โมเดล Embed 4 + บัคเก็ตโครงการ
- ผู้ใช้ webapp allow-list · MCP auth จาก Secrets หรือ env
- บัคเก็ต Block Public Access + SSE-KMS
- AWS Budgets เตือน EC2 + Bedrock

---

## 8. เกณฑ์ผ่าน

- [ ] EC2 ขึ้น Compose: webapp + MCP healthy  
- [ ] IAM จากเครื่องเรียก Embed 4 + S3 ได้  
- [ ] `POST /api/v1/pn/kb/upload` เก็บ+ตรวจบน S3 ตาม `rag_group`  
- [ ] MCP `list_rag_groups` + `retrieve(rag_group=...)` ผ่าน HTTPS  
- [ ] Quick ต่อ MCP ได้ &lt; 60s · ได้แหล่งเอกสารจริง  
- [ ] Chunk ≤ 4096 tokens · ไม่มี Fargate ในสแตก PN  

---

## สรุปหนึ่งหน้า

| หัวข้อ | คำตอบ |
|--------|--------|
| Compute | **EC2 + Docker Compose** (ไม่มี Fargate) |
| รันอะไรบน EC2 | MCP + webapp/API จัดการ KB/S3 (+ deploy แอป) |
| Embedding | Cohere Embed 4 |
| Vector DB | S3 Vectors (หลาย index / `rag_group`) |
| Ingest | API บน EC2 |
| ค้น | MCP บน EC2 เลือก `rag_group` |
| งบปี 1 (คร่าว ๆ) | ~**$25–70 / เดือน** ตามขนาด EC2 |
| งบปี 2 (+1 TB เวกเตอร์) | ~**$90–160 / เดือน** |
