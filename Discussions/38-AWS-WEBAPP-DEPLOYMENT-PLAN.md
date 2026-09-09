# 38 — แผน Deploy Webapp TOR บน AWS Cloud

แอปปัจจุบัน **v0.5.0** · Region **`ap-southeast-1`**  
แหล่งซอร์สที่ build เป็นคอนเทนเนอร์: **[`app/frontend`](../app/frontend)** (Next.js 14) + **[`app/backend`](../app/backend)** (FastAPI)

> **อย่าใช้โฟลเดอร์ `frontend/` ที่รากรีโป** — บนดิสก์ท้องถิ่นอาจเหลือแค่ไฟล์สร้างอัตโนมัติ (`src/lib/tor-profiles.generated.ts`) ไม่มี `Dockerfile` / `package.json` จึง **build ขึ้น AWS ไม่ได้**  
> Compose ที่รากใช้ `context: ./app/frontend` · แพ็กเกจ PN (`app/infra/pn-ec2/docker-compose.pn.yml`) ใช้ `context: ../../frontend` ซึ่งชี้มาที่ **`app/frontend`** เช่นกัน

เอกสารคู่:

| เส้นทาง | เมื่อใช้ | เอกสาร |
|---------|----------|--------|
| **ก — PN เร็ว (แนะนำเริ่ม)** | หน่วยงานเล็ก · งบจำกัด · MCP + webapp เครื่องเดียว | [33](33-AWS-PN-CLOUD-MINIMUM-COST-PLAN.md)–[36](36-AWS-PN-USER-SETUP-AND-RUNBOOK.md) · [`app/infra/pn-ec2/`](../app/infra/pn-ec2/) |
| **ข — Production ECS** | HA, ALB, RDS, ไม่แพตช์ OS เอง | [24](24-AWS_CLOUD_OVERVIEW.md)–[27](27-AWS_CODE_AND_CUTOVER.md) · [`app/infra/aws/`](../app/infra/aws/) |

LLM บนคลาวด์เป็น **Amazon Bedrock เท่านั้น** (`DEPLOYMENT_MODE=cloud`) — ห้ามชี้ task production ไป LM Studio

---

## 1. ภาพรวมบริการ (webapp)

```text
เจ้าหน้าที่ ──HTTPS──► หน้า Next.js :3000
                         │  rewrite /api/v1
                         ▼
                    FastAPI :4000
                         │
     ┌───────────┬───────┼────────┬─────────────┐
     ▼           ▼       ▼        ▼             ▼
  Postgres    Redis     S3     Bedrock      MCP :8767
  (+pgvector)          เอกสาร   แชท+embed    (Quick / retrieve)
```

| ชั้น | บริการ AWS (เส้น ก PN) | บริการ AWS (เส้น ข ECS) |
|------|------------------------|-------------------------|
| UI webapp | คอนเทนเนอร์ `frontend` บน **EC2 + Docker Compose** จาก `app/frontend` | **ECS Fargate** อิมเมจ ECR `tor-frontend` จาก `app/frontend` |
| API | คอนเทนเนอร์ `backend` บน EC2 เดียวกัน | **ECS Fargate** `tor-backend` จาก `app/backend` |
| HTTPS | **nginx บน EC2** + Let's Encrypt (หรือ ACM นำเข้า) | **ACM** + **ALB** (+ CloudFront/WAF ตาม 24) |
| DNS | Elastic IP / Route 53 ชี้ EC2 | **Route 53** → CloudFront หรือ ALB |
| LLM / embed | **Bedrock** (แชทตามที่อนุมัติ + PN ล็อก Embed 4) | **Bedrock** (IAM task role) |
| ไฟล์ / ส่งออก | **S3** (MinIO SDK, `MINIO_SECURE=true`) | **S3** |
| คลังเวกเตอร์ | **S3 Vectors** (PN) | **RDS pgvector** (+ MCP JSON ใน Secrets ตาม 31) |
| เซสชัน / คิว | Redis บน volume EC2 | **ElastiCache** TLS |
| ฐานแอป | Postgres บน volume EC2 | **RDS PostgreSQL 16** + `vector` |
| ความลับ | `.env` บนเครื่อง หรือ Secrets Manager | **Secrets Manager** + **KMS** |
| สิทธิ์ | IAM **instance profile** | IAM **task role** + execution role |
| สังเกตการณ์ | CloudWatch (ตัวเลือก) + `healthcheck.sh` | CloudWatch Logs + Container Insights |
| งบ | **AWS Budgets** กรอง EC2 + Bedrock + S3 | เดียวกัน + Cost Anomaly |

Next.js เป็น **SSR** จึงต้องมีโปรเซส Node — **อย่า** วางแค่ `out/` ลง S3 แล้วถือว่าเป็นแอปจริง

---

## 2. สิ่งที่ต้องมีก่อน deploy

1. บัญชี AWS (แยก sandbox กับ prod) · เปิด CloudTrail · ตั้ง **Budget** เตือน Bedrock
2. Region **ap-southeast-1**
3. Bedrock → Model access: โมเดลแชทที่หน่วยงานอนุมัติ + โมเดลฝังตามเส้นทาง (PN = `cohere.embed-v4:0`)
4. โดเมนหรือ hostname (`PN_PUBLIC_HOST` / `tor.example.go.th`)
5. Git clone รีโปบนเครื่อง build หรือบน EC2 — โฟลเดอร์เว็บคือ **`app/frontend`**
6. ค่าความลับ: `JWT_SECRET`, รหัส Postgres/Redis, โทเคน MCP — **ไม่ commit**

---

## 3. เส้น ก — PN บน EC2 (webapp + MCP)

ใช้เมื่อต้องการขึ้นใช้งานเร็ว ต้นทุนคงที่ต่อเครื่อง · รายละเอียดคำสั่งอยู่ใน [35](35-AWS-PN-DEV-AND-DEPLOY.md) และ [36](36-AWS-PN-USER-SETUP-AND-RUNBOOK.md)

### 3.1 สร้างบน AWS Console

| ลำดับ | งาน | ผลที่ต้องได้ |
|--------|------|----------------|
| 1 | EC2 Amazon Linux 2023 / Ubuntu · **t3.small** หรือ **t3.medium** · ดิสก์พอสำหรับอิมเมจ Docker | instance + (แนะนำ) Elastic IP |
| 2 | Security group: **443** จากสำนักงาน/VPN · **ไม่เปิด 22 สาธารณะ** (ใช้ SSM) | SG |
| 3 | IAM role ชนิด EC2 จาก [`iam/ec2-instance-profile.json`](../app/infra/pn-ec2/iam/ec2-instance-profile.json) แทนชื่อบัคเก็ตจริง | instance profile |
| 4 | S3 บัคเก็ตคลัง · Block Public Access | `PN_S3_BUCKET` |
| 5 | S3 Vectors index มิติ **1024** ตาม `rag-groups.yaml` | `PN_S3_VECTOR_BUCKET` |
| 6 | (ทางเลือก) Route 53 A/AAAA ชี้ Elastic IP | `PN_PUBLIC_HOST` |

### 3.2 บนเครื่อง EC2

```bash
# ติดตั้ง Docker Engine + Compose plugin แล้ว clone รีโป
cd app/infra/pn-ec2
cp .env.example .env
# แก้ changeme_* : PN_S3_BUCKET, PN_S3_VECTOR_BUCKET, MINIO_BUCKET,
# JWT_SECRET, QUICK_MCP_AUTH_VALUE, PN_PUBLIC_HOST, CORS_ORIGINS,
# POSTGRES_PASSWORD, REDIS_PASSWORD, BEDROCK_MODEL_ID
bash scripts/bootstrap-ec2.sh
# หรือ
docker compose -f docker-compose.pn.yml --env-file .env up -d --build
```

Compose **build frontend จาก `app/frontend`** แล้วรันคู่ `backend` · nginx (profile `with-nginx`) ส่ง `/` → UI, `/api` → API, `/mcp` → Amazon Quick

เว้น `AWS_ACCESS_KEY_ID` ว่างบน EC2 ให้ใช้ instance profile

### 3.3 ตรวจว่า webapp ขึ้น

```bash
bash scripts/healthcheck.sh
# เบราว์เซอร์: https://$PN_PUBLIC_HOST  (ล็อกอิน officer หลัง seed_db)
```

หน้าสร้างโครงการต้องเลือก **หมวดใหญ่ ๗ ประเภท** (Section_Profile) — ไม่มีค่าเริ่มต้น

---

## 4. เส้น ข — ECS Fargate (production)

โครง Terraform / task ยังเป็น **skeleton** จนกว่าจะ `plan` และเปิดแฟล็กใน `terraform.tfvars` — อย่า `apply` ในบัญชีจริงโดยไม่มีงบเตือน Bedrock

ลำดับเฟสเต็มอยู่ใน [24](24-AWS_CLOUD_OVERVIEW.md) §3 และ [26](26-AWS_INSTALL_AND_WIRING.md)

### 4.1 รอบโครงสร้าง (Terraform)

จาก [`app/infra/aws/terraform/`](../app/infra/aws/terraform/)

1. รอบ 1: VPC, NAT, S3, ECR, KMS, IAM, CloudWatch (แฟล็ก data/ECS ยังปิด)
2. รอบ 2: `enable_managed_data=true` → RDS + ElastiCache
3. รอบ 3: `enable_ecs=true` + `certificate_arn` → ALB + ECS frontend/backend + Cloud Map `backend.tor.local`

ค่าแอป: คัดลอก [`env.cloud.example`](../app/infra/aws/env.cloud.example) เข้า Secrets Manager อย่าใส่ access key ใน task ถ้ามี task role

Build-arg อิมเมจ UI:

| ARG | ค่าบน ECS |
|-----|-----------|
| `NEXT_PUBLIC_API_URL` | `/api/v1` |
| `BACKEND_INTERNAL_URL` | `http://backend.tor.local:4000/api/v1` |

### 4.2 Build และ push อิมเมจ webapp

ทำบน CI (`app/infra/aws/ci/ecs-deploy.yml`) หรือเครื่องที่มีสิทธิ์ ECR:

```bash
REG="$ACCOUNT.dkr.ecr.ap-southeast-1.amazonaws.com"
docker build -t "$REG/tor-frontend:${GIT_SHA}" ./app/frontend \
  --build-arg NEXT_PUBLIC_API_URL=/api/v1 \
  --build-arg BACKEND_INTERNAL_URL=http://backend.tor.local:4000/api/v1
docker build -t "$REG/tor-backend:${GIT_SHA}" ./app/backend
docker push "$REG/tor-frontend:${GIT_SHA}"
docker push "$REG/tor-backend:${GIT_SHA}"
```

Task definition ตัวอย่าง: [`ecs/frontend.task-definition.json`](../app/infra/aws/ecs/frontend.task-definition.json) · desiredCount UI = 2 ตาม [`ecs/services.yml`](../app/infra/aws/ecs/services.yml) · **backend เริ่มที่ 1** จนกว่า Draft job จะทน scale แนวนอน

ALB: path `/` → target group frontend `:3000` · `/api/*` → backend `:4000` (หรือให้ Next rewrite อย่างเดียวแล้ว FE พูดกับ Cloud Map)

Health: frontend `GET /` = 200 · backend `GET /health`

### 4.3 หลังขึ้นบริการ

1. งาน one-shot: [`scripts/pull-kb-from-s3.sh`](../app/infra/aws/scripts/pull-kb-from-s3.sh) แล้ว `python -m app.seed_db` / seed คลัง
2. ตรวจล็อกอิน + สร้างโครงการ (บังคับหมวดใหญ่) + ร่างสั้นหนึ่งหมวดบน Bedrock
3. เปิด WAF บน CloudFront/ALB ตาม [26](26-AWS_INSTALL_AND_WIRING.md)
4. อย่ารัน `pytest -m live_llm` ต่อ LM Studio ในบัญชี prod ([27](27-AWS_CODE_AND_CUTOVER.md))

---

## 5. ตัวแปรที่ webapp ต้องเห็น

| ตัวแปร | ความหมาย |
|--------|----------|
| `NEXT_PUBLIC_API_URL` | พาธที่เบราว์เซอร์เรียก API — บน AWS ให้เป็น `/api/v1` (ผ่าน nginx/ALB) **ห้าม** ใส่โฮสต์ Docker ชื่อ `backend` |
| `BACKEND_INTERNAL_URL` | URL ที่ Next SSR เรียก FastAPI ในเครือข่ายส่วนตัว |
| `CORS_ORIGINS` | origin HTTPS ของโดเมนจริง |
| `COOKIE_SECURE` | `true` เมื่อมี TLS |
| `DEPLOYMENT_MODE` | `cloud` |
| `LLM_PROVIDER` / `EMBEDDING_PROVIDER` | `bedrock` |

รายการเต็มเส้น ก: [`app/infra/pn-ec2/.env.example`](../app/infra/pn-ec2/.env.example) · เส้น ข: [`app/infra/aws/env.cloud.example`](../app/infra/aws/env.cloud.example)

---

## 6. เช็คลิสต์ตัดระบบ (webapp)

- [ ] อิมเมจ build จาก **`app/frontend`** และ **`app/backend`** ของแท็ก/SHA ที่จะขึ้น
- [ ] HTTPS ใช้ได้ · cookie Secure · CORS ตรงโดเมน
- [ ] `/health` ของ API healthy · หน้า `/` โหลด
- [ ] Bedrock invoke ได้จาก role (ไม่มี LM Studio ใน prod)
- [ ] S3 อัปโหลด/ส่งออก DOCX-PDF ได้
- [ ] seed ผู้ใช้ทดลองแล้วเปลี่ยนรหัส
- [ ] Budget + CloudWatch alarm
- [ ] สำรอง RDS (เส้น ข) หรือ snapshot volume (เส้น ก)
- [ ] หมวดใหญ่ ๗ ประเภทบนหน้าสร้างโครงการทำงาน

---

## 7. สิ่งที่ยังไม่ทำในเฟสนี้

- Cognito แทน JWT ในแอป
- Neptune แทน Neo4j (เส้น ข ขึ้น pgvector ก่อน)
- Scale backend > 1 โดยไม่มี Draft_Job_Store ทนหลาย task
- วาง `frontend/` ที่รากรีโปเป็นสำเนา Next.js — **ห้าม** ทำซ้ำต้นไม้ `app/frontend`

เมื่อจะเลื่อนจากเส้น ก → ข: ย้าย state Postgres/Redis ขึ้น RDS/ElastiCache ตาม [27](27-AWS_CODE_AND_CUTOVER.md) แล้วชี้ DNS จาก EC2 ไป ALB
