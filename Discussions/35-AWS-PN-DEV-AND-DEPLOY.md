# 35 — พัฒนาและ Deploy PN บน AWS EC2 (MCP + Webapp + S3)

**แผนขึ้น webapp ทั้งสองเส้นทาง (EC2 vs ECS):** [38-AWS-WEBAPP-DEPLOYMENT-PLAN.md](38-AWS-WEBAPP-DEPLOYMENT-PLAN.md) — อิมเมจ UI build จาก **`app/frontend`**

คู่มือทีละขั้นสำหรับแพ็กเกจ **[`app/infra/pn-ec2/`](../app/infra/pn-ec2/)**  
แผนต้นทุน: [33](33-AWS-PN-CLOUD-MINIMUM-COST-PLAN.md) · รายการเครื่องมือ: [34](34-AWS-PN-TOOLS-LIST.md)  
**คู่มือผู้ใช้ / งานที่ต้องทำเอง / Local→Cloud:** [36](36-AWS-PN-USER-SETUP-AND-RUNBOOK.md)  
**ไม่มี Fargate** · คลังความรู้ = **S3 + S3 Vectors** · Embedding = **Cohere Embed 4**

PDF: สร้างด้วย `python Discussions/_export_pn_plan_pdf.py`

---

## 0. สิ่งที่ได้

| ชิ้น | ที่อยู่ |
|------|---------|
| โฟลเดอร์ deploy | `app/infra/pn-ec2/` |
| ค่าคอนฟิกทั้งหมด | **`.env`** (คัดลอกจาก `.env.example`) |
| Webapp ร่าง TOR | Compose `frontend` + `backend` |
| MCP | `amazon-quick` :8767 → `mcp-rag` |
| คลัง | S3 prefixes ตาม `rag-groups.yaml` |

```text
cp app/infra/pn-ec2/.env.example app/infra/pn-ec2/.env
# แก้ changeme_* → bootstrap → HTTPS → sync dataset → Quick
```

---

## 1. ตั้งเครื่องมือบน AWS (ทำครั้งแรก)

ทำใน region **`ap-southeast-1`**

### 1.1 บัญชีและงบ

1. บัญชี AWS (หรือ OU แยก PN)
2. **Billing → Budgets** เตือน EC2 + Bedrock + S3
3. เปิด CloudTrail ในบัญชี prod/PN

### 1.2 Bedrock

1. Bedrock → **Model access**
2. เปิดโมเดลแชทที่หน่วยงานอนุมัติ (ใส่ใน `BEDROCK_MODEL_ID`)
3. เปิด **`cohere.embed-v4:0`** → ค่าใน `.env`: `BEDROCK_EMBEDDING_MODEL_ID=cohere.embed-v4:0`

### 1.3 S3 (ฐานข้อมูลไฟล์คลัง)

1. สร้างบัคเก็ต เช่น `pn-tor-kb-<หน่วยงาน>`  
2. Block Public Access ทั้งหมด · เข้ารหัสตามนโยบาย  
3. ใส่ชื่อเดียวกันใน `.env`:

```env
PN_S3_BUCKET=pn-tor-kb-example
MINIO_BUCKET=pn-tor-kb-example
MINIO_ENDPOINT=s3.ap-southeast-1.amazonaws.com
MINIO_SECURE=true
MINIO_REGION=ap-southeast-1
MINIO_USE_IAM=true
```

โครง prefix (อัตโนมัติตอน upload / sync):

```text
s3://{bucket}/rags/procurement-th/sources/
s3://{bucket}/rags/procurement-th/manifest/
s3://{bucket}/rags/agency-extra/...
```

### 1.4 S3 Vectors

1. สร้าง index มิติ **1024** ให้ตรง `.env` / `rag-groups.yaml`  
   - `procurement-th-embed4-v1`  
   - `agency-extra-embed4-v1` (ถ้าใช้กลุ่มสอง)
2. ค่าใน `.env`: `PN_S3_VECTOR_BUCKET=...` และ indexes ใน `rag-groups.yaml` / `PN_S3_VECTOR_INDEX_*`

### 1.5 IAM สำหรับ EC2

1. สร้าง Role ชนิด EC2  
2. แนบนโยบายจาก [`app/infra/pn-ec2/iam/ec2-instance-profile.json`](../app/infra/pn-ec2/iam/ec2-instance-profile.json)  
3. **แทน** `changeme-pn-tor-kb` ด้วยชื่อบัคเก็ตจริง  
4. Attach เป็น **instance profile** ของเครื่อง EC2  
5. บน `.env` ของ EC2: **เว้นว่าง** `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`

### 1.6 EC2

1. AMI Amazon Linux 2023 หรือ Ubuntu 22.04  
2. Instant type: **t3.small** (เบา) หรือ **t3.medium** (webapp+MCP สบายกว่า)  
3. Disk ≥ 30 GB gp3  
4. Security Group:  
   - inbound **443** จาก IP สำนักงาน/VPN  
   - **22** แคบหรือปิดแล้วใช้ **SSM Session Manager**  
5. Elastic IP → ใส่โดเมนหรือ hostname ใน `PN_PUBLIC_HOST`  
6. ติดตั้ง: Docker + Compose plugin + git + awscli

---

## 2. ตั้งค่า `.env` ให้ครบ (ศูนย์กลาง config)

```bash
cd app/infra/pn-ec2
cp .env.example .env
```

แก้ค่าที่จำเป็นอย่างน้อย:

| ตัวแปร | ตัวอย่าง / หมายเหตุ |
|--------|---------------------|
| `PN_PUBLIC_HOST` | โดเมนหรือ DNS ของ Elastic IP |
| `CORS_ORIGINS` | `https://` + host เดียวกัน |
| `PN_S3_BUCKET` / `MINIO_BUCKET` | ชื่อบัคเก็ตจริง |
| `JWT_SECRET` | สุ่ม ≥ 32 ตัวอักษร |
| `QUICK_MCP_AUTH_VALUE` | สุ่ม — ใส่ใน Amazon Quick ด้วย |
| `POSTGRES_PASSWORD` / `REDIS_PASSWORD` | สุ่มบนเครื่อง |
| `BEDROCK_MODEL_ID` | โมเดลแชทที่เปิดในบัญชี |
| `BEDROCK_EMBEDDING_MODEL_ID` | คง `cohere.embed-v4:0` |

หมวดใน `.env.example` (อ่านไฟล์นั้นเป็นคำอธิบายเต็ม):

1. AWS region / keys  
2. Public host / พอร์ต  
3. โหมด cloud  
4. Bedrock chat + Embed 4  
5. S3  
6. multi-RAG / chunk 4096  
7. MCP  
8. JWT  
9. Postgres/Redis บน volume EC2  
10. Rate limits  
11. Checklist คอนโซล AWS  

**ห้าม commit `.env`**

---

## 3. Deploy บน EC2

```bash
# บนเครื่อง EC2
git clone <repo> && cd <repo>/app/infra/pn-ec2
cp .env.example .env && nano .env

chmod +x scripts/*.sh
./scripts/bootstrap-ec2.sh

# เปิด reverse proxy
cp nginx/pn.conf.example nginx/pn.conf
docker compose -f docker-compose.pn.yml --profile with-nginx --env-file .env up -d

# TLS: ใช้ certbot บนโฮสต์แล้ว mount certs ไป nginx/certs (ดู README โฟลเดอร์)
./scripts/healthcheck.sh
```

อัปเดตแอปวันหลัง:

```bash
git pull
docker compose -f docker-compose.pn.yml --env-file .env up -d --build
```

---

## 4. Dataset และ ingest

### 4.1 สร้างแพ็กเกจบนเครื่อง dev

```bash
python documents/exports/build_pn_aws_dataset.py --version 0.6.1
# ได้ documents/exports/tor-pn-aws-dataset-v0.6.1.zip
```

แตก zip แล้วใน `.env` บนเครื่องที่มี AWS CLI:

```env
PN_DATASET_LOCAL_PATH=/path/to/extracted/rag-pdfs
PN_S3_SOURCES_PREFIX=rags/procurement-th/sources/
```

```bash
./scripts/sync-dataset-to-s3.sh
```

### 4.2 อัปโหลดผ่าน API (ง่ายสุดต่อไฟล์)

```bash
curl -X POST "https://$PN_PUBLIC_HOST/api/v1/pn/kb/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@ระเบียบ.pdf" \
  -F "rag_group=procurement-th" \
  -F "ingest=true"
```

Pipeline: extract → chunk ~4096 → Bedrock **Cohere Embed 4** → `PutVectors` บน `PN_S3_VECTOR_BUCKET`  
(ข้อความเต็มเก็บที่ `rags/{group}/chunks/...` บน object bucket)

ฝังจากอ็อบเจ็กต์ที่มีแล้ว:

```bash
curl -X POST "https://$PN_PUBLIC_HOST/api/v1/pn/kb/ingest" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"object_key":"rags/procurement-th/sources/...","rag_group":"procurement-th"}'
```

---

## 5. ต่อ Amazon Quick / Claude Code (MCP)

1. Quick Enterprise → Connectors → **MCP**  
2. URL: `https://$PN_PUBLIC_HOST/mcp`  
3. Auth header = ค่า `QUICK_MCP_AUTH_HEADER` / `QUICK_MCP_AUTH_VALUE`  
4. เรียก `list_rag_groups` แล้ว `retrieve` พร้อม `rag_group`  
5. ต้องตอบภายใน 60 วินาที · [32](32-AMAZON-QUICK.md)

---

## 6. เกณฑ์ผ่าน

- [ ] `.env` ถูกสร้างจาก `.env.example` และไม่มี `changeme_` ค้างในค่าสำคัญ  
- [ ] EC2 + IAM + S3 + Bedrock Embed 4 พร้อม  
- [ ] `docker compose ... up` แล้ว webapp + MCP healthy  
- [ ] Sync หรือ upload ขึ้น S3 เห็นอ็อบเจกต์ใต้ `rags/.../sources/`  
- [ ] `ingest=true` หรือ `/pn/kb/ingest` แล้วมีเวกเตอร์ใน S3 Vectors  
- [ ] MCP `retrieve` / `POST /pn/kb/search` คืน chunk ตาม `rag_group`  
- [ ] Quick/Claude เรียก MCP ได้  
- [ ] ไม่ใช้ Fargate ในสแตกนี้  

---

## 7. อ้างอิงไฟล์

| ไฟล์ | บทบาท |
|------|--------|
| [`app/infra/pn-ec2/.env.example`](../app/infra/pn-ec2/.env.example) | คอนฟิกครบ |
| [`app/infra/pn-ec2/docker-compose.pn.yml`](../app/infra/pn-ec2/docker-compose.pn.yml) | สแตกบน EC2 |
| [`app/infra/pn-ec2/iam/ec2-instance-profile.json`](../app/infra/pn-ec2/iam/ec2-instance-profile.json) | สิทธิ์ AWS |
| [`app/infra/pn-ec2/rag-groups.yaml`](../app/infra/pn-ec2/rag-groups.yaml) | หลาย RAG |
| [`app/infra/pn-ec2/README.md`](../app/infra/pn-ec2/README.md) | สรุปสั้นในโฟลเดอร์ |
