# 27 — โค้ดที่ต้องปรับ และตัดระบบเข้า AWS

เอกสารนี้คือช่องว่างระหว่างสแตก Docker ปัจจุบันกับเป้าหมาย AWS-only ใน [24](24-AWS_CLOUD_OVERVIEW.md)–[26](26-AWS_INSTALL_AND_WIRING.md)  
โครงที่ใส่ไว้ในรีโปแล้ว: `app/infra/aws/` และน็อบ S3/IAM ใน backend

---

## 1. ค่าสภาพแวดล้อม production (ไม่มี hybrid)

ไฟล์ตั้งต้น: `app/infra/aws/env.cloud.example`  
คัดลอกไป Secrets Manager / ECS ไม่ commit ค่ารหัส

ต้องเป็นชุดนี้ใน **task backend**:

```env
DEPLOYMENT_MODE=cloud
LLM_PROVIDER=bedrock
EMBEDDING_PROVIDER=bedrock
VECTOR_STORE_PROVIDER=pgvector
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
COOKIE_SECURE=true
```

ห้ามตั้งใน prod:

- `LLM_PROVIDER=lm_studio|ollama|llama_cpp|sglang`
- `EMBEDDING_PROVIDER=local`
- `LM_STUDIO_BASE_URL` ที่ชี้ GPU ในสำนักงาน

Admin ยังมีตัวเลือก on-prem ใน UI — ซ่อนหรือล็อกด้วย feature flag ในเฟสถัดไปถ้าหน่วยงานห้ามสลับกลับ

---

## 2. สิ่งที่ปรับในโค้ดแล้ว (รอบเอกสารนี้)

| จุด | พฤติกรรม |
|-----|----------|
| `Settings.minio_secure` / `MINIO_SECURE` | `false` ใน Compose ในเครื่อง; `true` บน S3 |
| `Settings.minio_region` / `MINIO_REGION` | เช่น `ap-southeast-1` |
| `Settings.minio_use_iam` / `MINIO_USE_IAM` | ใช้ IAM ของ task กับ MinIO SDK |
| `Settings.redis_tls` / `REDIS_TLS` | `true` → `rediss://` สำหรับ ElastiCache in-transit |
| `build_minio_client()` | `app/export/minio_storage.py` — `main.py` เรียกตัวนี้ |
| `KB_SOURCES_ROOT` | `app/domain/corpus.py` — seed จากโฟลเดอร์ที่ดึงมาจาก S3 |

Compose ในเครื่องไม่ต้องเปลี่ยน: ค่าเริ่มต้นยัง HTTP + access key MinIO และ `REDIS_TLS=false`

---

## 3. งานที่ยังต้องทำก่อน scale แนวนอน

### 3.1 Cookie และ CORS

- `COOKIE_SECURE=true` เมื่อมี HTTPS
- `CORS_ORIGINS` เป็นโดเมนจริง (คั่นด้วยจุลภาคถ้ามีหลาย origin)
- Next และ API อยู่ same-origin หลัง CloudFront จะลดปัญหา CORS

### 3.2 Redis TLS

ทำแล้ว: `REDIS_TLS=true` → `rediss://:{password}@{host}:{port}/0`  
ถ้า `PING` ล้มบน ElastiCache ให้ตรวจ CA ในอิมเมจ ไม่ปิด TLS เพื่อเลี่ยง AUTH

### 3.3 คิวร่างหลาย task

`draft-chat/start` ส่งงานพื้นหลังในโปรเซส  
เมื่อ `desiredCount > 1` ผู้ใช้ที่ตีอีก task จะไม่เห็นสถานะร่าง  
งาน: ย้ายสถานะ job เข้า Redis (มีแบบอย่างแคชเอเจนต์อยู่แล้ว) หรือ **SQS + worker service**

จนกว่าจะเสร็จ: backend service **desiredCount = 1** + deployment แบบ rolling ระวังงานค้าง

### 3.4 มิติเวกเตอร์ Titan

ตาราง `kb_chunks.embedding` เป็น `vector(768)` (Alembic `002`)  
Titan v2 มักได้ 1024 แล้วโค้ดตัดใน `_fit_dimensions`

งาน production ที่ถูกต้อง:

1. Alembic ใหม่: `ALTER ... TYPE vector(1024)` (ข้อมูลเก่าทิ้งแล้ว seed ใหม่)
2. ตั้ง `EMBEDDING_DIMENSIONS` จาก env แทนค่าคงที่ 768 ใน `app/providers/constants.py`
3. ส่ง `dimensions: 1024` (หรือ 768 ถ้า Titan รองรับ) ใน body `invoke_model` ของ Titan v2
4. `python -m app.seed_raw_docs` ทั้งคลัง

อย่าปนเวกเตอร์ Gemma กับ Titan ในตารางเดียวกัน

### 3.5 ต้นฉบับ: เลิก GridFS

งาน:

1. อินเทอร์เฟซเดียวกับ `OriginalDocumentStore.put_file` / `get_bytes`
2. อิมพลีเมนต์ S3 (`tor-prod-originals`)
3. ย้ายเมทาดาทาเข้า PostgreSQL
4. สลับด้วย `ORIGINALS_STORE=s3`
5. ปิด `MONGO_URI` ใน task เมื่อไม่มีผู้อ่านเก่า

DocumentDB ใช้ได้แค่ช่วงเมทาดาทา — **ไม่ใช้ GridFS**

### 3.6 GraphRAG → Neptune

`GraphRAGStore` ผูก Neo4j Bolt  
งาน:

1. แพ็กเกจ `neo4j` ชี้ `bolt://<neptune>:8182` พร้อม IAM auth ตามคู่มือ Neptune
2. ทดสอบ Cypher ใน `upsert_extraction` / wipe / expand บน Neptune (อาจต้องลดคล้าย `DETACH DELETE` ทั้งกราฟ)
3. หรือเขียนสโตร์ Gremlin — งานใหญ่กว่า
4. ธง `GRAPH_PROVIDER=neptune|neo4j|off` เพื่อปิดกราฟชั่วคราวโดยไม่ทำให้ `/health` แดงถ้าตั้งให้กราฟเป็น optional (ตอนนี้ Neo4j ล้มแล้วยังบูตได้)

ขึ้น prod โดย `GRAPH_PROVIDER=off` ได้ถ้าหน่วยงานยอมให้ถาม-ตอบใช้แค่ pgvector ก่อน

### 3.7 Seed จาก S3

`python -m app.storage.s3_kb_sync` ดาวน์โหลด prefix แล้วตั้ง `KB_SOURCES_ROOT` ก่อน `seed_raw_docs`  
บน bastion ใช้ `app/infra/aws/scripts/pull-kb-from-s3.sh` (ต้องมี AWS CLI)

อย่า COPY PDF เข้า Docker image

### 3.8 Health check ชื่อ minio

`GET /health` คืนคีย์ `"minio"` แม้ปลายทางเป็น S3 — ไม่บังคับเปลี่ยนชื่อในเฟสแรก (frontend/ops อาจผูกชื่อนี้)

### 3.9 Cognito (เฟสหลัง)

ตอนนี้ล็อกอินเป็น JWT + cookie ของแอป  
Cognito หมายถึงเขียนใหม่: Hosted UI / Authorization code, แมปกลุ่ม `officer|reviewer|admin`  
อย่าทำพร้อมตัด GridFS ในสปรินต์เดียว

---

## 4. Frontend บน ECS

- Build arg `BACKEND_INTERNAL_URL` ต้อง resolve ใน VPC (Cloud Map)
- `NEXT_PUBLIC_API_URL=/api/v1` ให้เบราว์เซอร์เรียก same-origin
- อย่าใส่ URL Bedrock ในเบราว์เซอร์
- Health ของ task Next: HTTP 200 ที่ `/`

ถ้าแยกโดเมน `api.tor.example.go.th` ต้องตั้ง CORS และ cookie domain — แนะนำโดเมนเดียวผ่าน ALB path

---

## 5. ลำดับตัดระบบจาก Docker ในเครื่อง

1. ขึ้น VPC + RDS + Redis + S3 + Bedrock ตามเอกสาร 26
2. ย้าย schema + `seed_db` (ผู้ใช้จริง)
3. Seed คลังด้วย Titan (เวกเตอร์ใหม่)
4. ชี้ DNS ช่วงทดลอง (เช่น `tor-uat.`) ให้เจ้าหน้าที่กลุ่มเล็ก
5. เทียบโครงการ ECT เดิม: วิเคราะห์ 27 ช่อง + ตรวจไฟล์ + ร่างหนึ่งหมวดบน Bedrock
6. ปิด Compose dev จากเครือข่ายหน่วยงาน (ยังใช้ได้บนเครื่องพัฒนา)

อย่ารีบิลด์คอนเทนเนอร์ backend ทิ้งงานร่างค้าง — เหมือนคำเตือนในหลักฐานเทสต์บน Docker

---

## 6. ทดสอบบนคลาวด์ (ชุดเดิม + LLM จริง)

ฮาร์เนส `app/backend/tests/test_live_ect_tor_full.py` ชี้ `http://127.0.0.1:4000`  
บน AWS:

```bash
export API_BASE=https://tor.example.go.th/api/v1
# ปรับ test ให้อ่าน API_BASE จาก env ถ้ายังฮาร์ดโค้ด
```

ตรวจอย่างน้อย:

- ล็อกอิน HTTPS
- วางแพ็ก ECT → วิเคราะห์
- `POST /review/extract` + `/review/run`
- ร่างหนึ่งหมวดด้วย Bedrock (ทั้ง 13 หมวดใช้เวลานานและคิดเงินโทเคน)

อย่ารัน `live_llm` ต่อ LM Studio ในบัญชี prod

---

## 7. ไฟล์ในรีโปที่เกี่ยวข้อง

```
Discussions/24-AWS_CLOUD_OVERVIEW.md
Discussions/25-AWS_SERVICE_CATALOG.md
Discussions/26-AWS_INSTALL_AND_WIRING.md
Discussions/27-AWS_CODE_AND_CUTOVER.md          ← ไฟล์นี้
Discussions/20-AWS_BEDROCK_SETUP.md             ← ทางลัด EC2+Compose+Bedrock
app/infra/aws/README.md
app/infra/aws/env.cloud.example
app/infra/aws/iam/
app/infra/aws/ecs/
app/infra/aws/terraform/
app/infra/aws/scripts/pull-kb-from-s3.sh
app/infra/aws/ci/github-ecs-deploy.yml.example
app/backend/app/export/minio_storage.py         ← build_minio_client
app/backend/app/config.py                       ← MINIO_* / REDIS_TLS
app/backend/app/storage/s3_kb_sync.py            ← seed จาก S3
app/backend/app/domain/corpus.py                ← KB_SOURCES_ROOT
```
