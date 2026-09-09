# 34 — เครื่องมือ AWS ที่ต้องใช้ (PN) — EC2 ไม่มี Fargate

คู่กับแผน [33](33-AWS-PN-CLOUD-MINIMUM-COST-PLAN.md) · deploy [35](35-AWS-PN-DEV-AND-DEPLOY.md) · **คู่มือผู้ใช้/งานมือ** [36](36-AWS-PN-USER-SETUP-AND-RUNBOOK.md) · Region: **`ap-southeast-1`**  
PDF: [34-AWS-PN-TOOLS-LIST.pdf](34-AWS-PN-TOOLS-LIST.pdf)  
แพ็กเกจ EC2 + **`.env`:** [`app/infra/pn-ec2/`](../app/infra/pn-ec2/) (`cp .env.example .env`)

---

## ต้องมี

| เครื่องมือ | ใช้ทำอะไร |
|------------|-----------|
| **EC2** (t3.small / t3.medium) | รัน MCP + webapp/API ด้วย Docker Compose |
| **S3** | ต้นฉบับ · หลาย `rag_group` ใต้ prefix |
| **S3 Vectors** | embedding ต่อกลุ่ม |
| **Bedrock** (Cohere Embed 4) | ฝังตอน ingest และตอนค้น |
| **IAM instance profile** | สิทธิ์จาก EC2 → Bedrock/S3 |
| **Security Group** | จำกัด 443 / SSM |
| **Budgets** | คุมงบ |

HTTPS: **nginx บน EC2** (ไม่บังคับ ALB)  
ความลับ: `.env` หรือ Secrets Manager

---

## ไม่ใช้ใน PN

**ECS Fargate** · ALB (ยกเว้นหน่วยงานบังคับ) · RDS · OpenSearch · Neptune · EC2 GPU · DocumentDB

---

## หลาย RAG บน S3 เดียว

```text
s3://{bucket}/rags/{rag_group}/sources/...
s3://{bucket}/rags/{rag_group}/manifest/...
```

คอนฟิก: `app/infra/pn/rag-groups.yaml`

---

## Ingest — API บน EC2 (ง่ายสุด)

```bash
curl -X POST "https://<ec2-โดเมน>/api/v1/pn/kb/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@ระเบียบ.pdf" \
  -F "rag_group=procurement-th" \
  -F "ingest=true"
```

`ingest=true` = เก็บ S3 → chunk ~4096 → Cohere Embed 4 → **S3 Vectors**  
หรือฝังทีหลัง: `POST /api/v1/pn/kb/ingest` ด้วย `object_key`  
ทดสอบค้น: `POST /api/v1/pn/kb/search` · MCP **ไม่ใช้** ingest

---

## ค้น — MCP บน EC2 (เลือกกลุ่มได้)

```text
Quick / Claude Code
  → https://<ec2>/mcp
  → list_rag_groups | retrieve(query, rag_group=...)
  → Embed 4 → S3 Vectors
```

| ชั้น | เครื่องมือ |
|------|------------|
| Host | **EC2** + nginx |
| MCP | `retrieve` · `list_rag_groups` · `ping` · `get_health` |
| ฝัง/ค้น | Bedrock Embed 4 · S3 Vectors |

---

## ต้นทุนคร่าว ๆ (ประเมินใหม่)

| รายการ | / เดือน |
|--------|---------|
| EC2 t3.small + ดิสก์ | ~$18–25 |
| EC2 t3.medium + ดิสก์ | ~$33–45 |
| Embed 4 (query เบา) | มัก &lt; $1 |
| S3 Vectors @ 1 TB | ~$60 |
| **ปี 1 รวมแนวโน้ม** | ~**$25–70** |
| **ปี 2 (+1 TB)** | ~**$90–160** |

ตัด Fargate + ALB ออกจากแผน PN แล้ว — รายละเอียดใน [33 §6](33-AWS-PN-CLOUD-MINIMUM-COST-PLAN.md)

---

## Checklist

1. สร้าง EC2 + IAM role + SG  
2. Docker Compose: webapp + MCP  
3. S3 + S3 Vectors + Bedrock Embed 4  
4. nginx HTTPS  
5. ทดสอบ upload API + MCP `retrieve` ตาม `rag_group`  
