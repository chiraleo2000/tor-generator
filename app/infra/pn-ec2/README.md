# PN EC2 deploy package — MCP + TOR webapp (S3 knowledge store)

แพ็กเกจแยกสำหรับขึ้น **AWS EC2** (ไม่มี Fargate)  
เอกสารเต็ม (ผู้ใช้ + งานมือ): [Discussions/36-AWS-PN-USER-SETUP-AND-RUNBOOK.md](../../../Discussions/36-AWS-PN-USER-SETUP-AND-RUNBOOK.md) · deploy เทคนิค [35](../../../Discussions/35-AWS-PN-DEV-AND-DEPLOY.md) · แผน [33](../../../Discussions/33-AWS-PN-CLOUD-MINIMUM-COST-PLAN.md) · เครื่องมือ [34](../../../Discussions/34-AWS-PN-TOOLS-LIST.md)

## ขั้นเร็ว (ตั้งค่าด้วย `.env`)

```bash
cd app/infra/pn-ec2
cp .env.example .env
# แก้ค่า changeme_* อย่างน้อย:
#   PN_S3_BUCKET, PN_S3_VECTOR_BUCKET, MINIO_BUCKET, JWT_SECRET,
#   QUICK_MCP_AUTH_VALUE, PN_PUBLIC_HOST, CORS_ORIGINS,
#   POSTGRES_PASSWORD, REDIS_PASSWORD
bash scripts/bootstrap-ec2.sh
# หรือ:
docker compose -f docker-compose.pn.yml --env-file .env up -d --build
```

เปิด nginx หน้าเครื่อง:

```bash
cp nginx/pn.conf.example nginx/pn.conf   # ถ้ายังไม่มี
docker compose -f docker-compose.pn.yml --profile with-nginx --env-file .env up -d
```

## ตั้งเครื่องมือบน AWS (สรุป)

| ลำดับ | บน AWS Console / CLI | คู่กับ `.env` |
|-------|----------------------|---------------|
| 1 | Region **ap-southeast-1** | `AWS_REGION`, `BEDROCK_REGION` |
| 2 | **EC2** t3.small/medium + Elastic IP | `PN_PUBLIC_HOST` |
| 3 | **IAM instance profile** จาก `iam/ec2-instance-profile.json` (แทน ARN บัคเก็ต) | เว้น `AWS_ACCESS_KEY_ID` ว่างบน EC2 |
| 4 | **SG**: 443 จากสำนักงาน/VPN; SSM แทน SSH กว้าง | — |
| 5 | **S3** บัคเก็ตคลังอ็อบเจ็กต์ (Block Public Access) | `PN_S3_BUCKET`, `MINIO_*` |
| 6 | **S3 Vectors** vector bucket + indexes มิติ **1024** | `PN_S3_VECTOR_BUCKET`, `rag-groups.yaml` |
| 7 | **Bedrock** model access: แชท + **`cohere.embed-v4:0`** | `BEDROCK_MODEL_ID`, `BEDROCK_EMBEDDING_MODEL_ID` |
| 8 | **Budgets** เตือน EC2+Bedrock+S3 | — |
| 9 | TLS (Let's Encrypt บน EC2) | `PN_PUBLIC_SCHEME=https`, `COOKIE_SECURE=true` |

## สิ่งที่ Compose รัน

| บริการ | บทบาท |
|--------|--------|
| frontend / backend | webapp ร่าง TOR + API `/api/v1/pn/kb/*` |
| mcp-rag + amazon-quick | MCP ค้นคลัง S3 Vectors (`retrieve`, `list_rag_groups`) |
| postgres / redis / mongo | state บน **volume EC2** (ไม่ใช่ RDS; ไม่เก็บเวกเตอร์คลัง) |
| nginx (profile `with-nginx`) | `/` UI · `/api` · `/mcp` |

คลังความรู้: **S3 objects** + **S3 Vectors** (`PN_RETRIEVE_BACKEND=s3_vectors`)

### Ingest / MCP (สั้น)

| งาน | วิธี |
|-----|------|
| อัปโหลด + ฝังเวกเตอร์ | `POST /api/v1/pn/kb/upload` form `ingest=true` (+ `rag_group`) |
| ฝังจากอ็อบเจ็กต์ที่มีแล้ว | `POST /api/v1/pn/kb/ingest` `{"object_key":"...","rag_group":"..."}` |
| ทดสอบค้นหา | `POST /api/v1/pn/kb/search` หรือ MCP `list_rag_groups` → `retrieve` |

## Sync dataset ขึ้น S3

```bash
# หลัง build dataset (documents/exports/...)
# ใน .env ตั้ง PN_DATASET_LOCAL_PATH=/path/to/rag-pdfs
bash scripts/sync-dataset-to-s3.sh
```

PowerShell: `scripts/sync-dataset-to-s3.ps1`

## ตรวจสุขภาพ

```bash
bash scripts/healthcheck.sh
```

Amazon Quick: `https://$PN_PUBLIC_HOST/mcp` + header ตาม `QUICK_MCP_AUTH_*`

## คู่มือผู้ใช้ (Local → AWS + งานมือ)

อ่านเต็ม: [Discussions/36](../../../Discussions/36-AWS-PN-USER-SETUP-AND-RUNBOOK.md)

สรุปบทบาท:

| ใคร | ทำอะไร |
|-----|--------|
| ผู้ดูแล | สร้าง EC2/S3/Vectors/Bedrock/IAM · กรอก `.env` · TLS · ต่อ Quick |
| Admin แอป | อัปโหลดคลัง `ingest=true` · ตรวจ search |
| ผู้ใช้ทั่วไป | ใช้เว็บร่าง TOR / ถามผ่าน Quick — ไม่ต้องเข้า AWS Console |

## ห้าม commit

ไฟล์ `.env` (มีใน `.gitignore`) — commit ได้เฉพาะ `.env.example`
