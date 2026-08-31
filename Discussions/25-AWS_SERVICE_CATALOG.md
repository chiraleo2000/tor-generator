# 25 — แคตตาล็อกบริการ AWS (จับคู่จากสแตกปัจจุบัน)

อ้างอิงสแตก Docker ใน `docker-compose.yml` และชั้นใน [`16-BACKEND_ARCHITECTURE.md`](16-BACKEND_ARCHITECTURE.md)  
เป้าหมาย: **บริการจัดการของ AWS** ไม่ใช่คอนเทนเนอร์ฐานข้อมูลใน Compose

---

## 1. จับคู่หลัก (ต้องมี)

| ชิ้นปัจจุบัน | บริการ AWS | เหตุผล | โน้ตเชื่อมโยง |
|--------------|------------|--------|----------------|
| Next.js 14 SSR | **ECS Fargate** + **ECR** | SSR + rewrite `/api/v1` ต้องการโปรเซส Node ไม่ใช่แค่ S3 static | `BACKEND_INTERNAL_URL=http://backend:4000/api/v1` ใน Docker → บน ECS ใช้ชื่อบริการ Cloud Map เช่น `http://backend.tor.local:4000/api/v1` หรือ ALB internal |
| FastAPI | **ECS Fargate** + **ECR** | คิว LLM, SSE, งานร่างยาว | CPU 1–2 vCPU / 2–4 GB; timeout ALB 300–900 วินาที สำหรับวิเคราะห์/ร่าง |
| PostgreSQL + pgvector | **RDS PostgreSQL 16** (หรือ Aurora PostgreSQL) | ตารางแอป + `kb_chunks.embedding` | `CREATE EXTENSION vector;` — ตรวจเวอร์ชัน RDS ที่รองรับ pgvector ใน region |
| Redis 7 | **ElastiCache Redis หรือ Valkey** | เซสชัน, rate limit, คิวรับ LLM, แคชเอเจนต์ | เปิด AUTH + encryption in-transit; URL `rediss://` |
| MinIO | **S3** | ส่งออก DOCX/PDF, อัปโหลดไฟล์โครงการ | SDK MinIO พูดกับ `s3.<region>.amazonaws.com` เมื่อ `MINIO_SECURE=true` + IAM |
| MongoDB GridFS | **S3** (แนะนำ) หรือ **DocumentDB** | ต้นฉบับคลัง | DocumentDB ไม่เหมาะกับ GridFS — ดูข้อ 3 |
| Neo4j GraphRAG | **Neptune** (openCypher) | กราฟกฎหมายคู่ pgvector | ต้องอะแดปเตอร์ไดรเวอร์ — ดูข้อ 4 และเอกสาร 27 |
| LM Studio / SGLang | **Bedrock** | แชท ร่าง รีวิว | `LLM_PROVIDER=bedrock` |
| EmbeddingGemma 768-d | **Bedrock Titan Embeddings** | ฝังคลัง | `EMBEDDING_PROVIDER=bedrock` แล้ว **seed ใหม่** |
| ไฟล์คลัง `documents/sources` | **S3** บัคเก็ต `tor-kb-source` | seed ไม่ใช้ bind-mount | Task one-shot อ่านจาก S3 |
| `.env` รหัสผ่าน | **Secrets Manager** | รหัส RDS, Redis, JWT | ECS inject เป็น env จาก secret ARN |
| โลจิก JWT ในแอป | คงไว้ระยะแรก หรือ **Cognito** ภายหลัง | Cognito แทนที่ `/auth/login` ทั้งก้อน | อย่าผสม cookie แอปกับ Cognito Hosted UI ในเฟสเดียวกัน |
| โฮสต์ไฟล์ช่วย `/help` | CloudFront + S3 หรืออยู่ในอิมเมจ Next | มีอยู่แล้วใน `public/help` | |

---

## 2. ขอบเครือข่าย ความปลอดภัย สังเกตการณ์ (ควรมีครบ)

| ความต้องการ | บริการ AWS | ใช้ทำอะไร |
|-------------|------------|-----------|
| DNS สาธารณะ | **Route 53** | `tor.example.go.th` → CloudFront หรือ ALB |
| TLS | **ACM** | ใบรับรองที่ us-east-1 ถ้าหน้า CloudFront; region เดียวกับ ALB ถ้าจบที่ ALB |
| CDN + กันโจมตีชั้น 7 | **CloudFront** + **WAF** | จำกัดเรต, geo, AWS managed rules |
| โหลดบาลานซ์ | **ALB** | path `/` → frontend, `/api/*` → backend (หรือให้ Next พร็อกซีอย่างเดียว) |
| เครือข่ายส่วนตัว | **VPC**, subnet สาธารณะ/ส่วนตัว, **NAT Gateway** | Task ไม่มี public IP |
| ไม่ผ่าน NAT | **VPC Interface/Gateway Endpoints** | S3, ECR, CloudWatch, Secrets, KMS, Bedrock Runtime, ECS |
| เข้าเครื่อง debug | **SSM Session Manager** (ไม่เปิด SSH 22) | ECS Exec หรือ bastion เล็ก ๆ |
| เข้ารหัสคีย์ | **KMS** | RDS, S3, Secrets, EBS ถ้ามี |
| ตรวจ API | **CloudTrail** | ทุกบัญชี prod |
| ภัยคุกคาม | **GuardDuty** | VPC + S3 + ECS |
| มาตรฐานบัญชี | **AWS Config** + **Security Hub** | กฎ S3 สาธารณะ, SG เปิดกว้าง |
| สำรอง | **AWS Backup** | RDS, ถ้ามี DocumentDB/Neptune |
| ล็อกแอป | **CloudWatch Logs** | awslogs ไดรเวอร์ของ Fargate |
| เมตริกคอนเทนเนอร์ | **Container Insights** | CPU/RAM task |
| เทรซ SSE/ร่าง | **X-Ray** (ตัวเลือก) | อย่าส่งเนื้อหา TOR ทั้งฉบับเข้า segment |
| งบและโทเคน | **Budgets**, Cost Anomaly, Bedrock invocation metrics | เตือนเมื่อร่างขนาน |
| คิวงานยาว | **SQS** + worker (เฟสถัดไป) | แทน job ร่างในหน่วยความจำเมื่อ scale แนวนอน |
| อีเมลระบบ | **SES** | ยังไม่มีในแอป — เผื่อรีเซ็ตรหัส |
| ลงทะเบียนคอนเทนเนอร์ | **Cloud Map** | ชื่อ `backend.tor.local` |

---

## 3. ต้นฉบับเอกสาร: S3 แทน GridFS

`OriginalDocumentStore` (`app/storage/mongo_store.py`) ใช้ GridFS  
**DocumentDB** รองรับ Mongo API ชุดย่อย และ GridFS ไม่ใช่เส้นทางที่ AWS แนะนำ

ทางที่เข้ากับ AWS ล้วน:

1. เก็บไบต์ใน S3 `s3://tor-originals/{scope}/{owner_id}/{sha256}`
2. เก็บเมทาดาทาใน PostgreSQL (ตารางใหม่) หรือคอลเลกชัน DocumentDB แบบเอกสารบาง ๆ **ไม่มี GridFS**

เฟส D ยังชี้ `MONGO_URI` ไป DocumentDB ได้เฉพาะเมทาดาทา ถ้ายังไม่ย้ายโค้ด — แต่ **อย่าคาดว่า GridFS ทำงาน**  
ลำดับที่ถูก: ทำที่เก็บ S3 ตามเอกสาร 27 แล้วค่อยปิด Mongo

---

## 4. GraphRAG: Neptune แทน Neo4j

`GraphRAGStore` ใช้ Cypher ผ่าน `neo4j.AsyncGraphDatabase` (`bolt://neo4j:7687`)

| ทางเลือก | ข้อดี | ข้อเสีย |
|----------|--------|---------|
| **Neptune openCypher** | บริการจัดการ, IAM auth, อยู่ใน VPC | ต้องเปลี่ยน URI/ไดรเวอร์; Cypher ไม่ครบทุกอย่างของ Neo4j |
| ปิดกราฟชั่วคราว | ขึ้น prod เร็ว; RAG ยังมี pgvector | ถาม-ตอบขาด expansion ตามมาตรา |
| Neo4j บน ECS | โค้ดไม่แตะ | **ไม่ใช่ AWS-native** — นอกขอบชุดนี้ |

แนะนำ: ขึ้น **pgvector ก่อน** (ถาม-ตอบใช้ได้) แล้ว accordingly เปิด Neptune เมื่ออะแดปเตอร์พร้อม  
อย่าเปิด Neptune ทิ้งว่าง — คิดเงินรายชั่วโมง

---

## 5. Bedrock (LLM + embeddings)

| งานในแอป | API Bedrock | โมเดลตั้งต้น (ปรับตาม model access) |
|-----------|-------------|-------------------------------------|
| ร่างหมวด, แชท KB, intake, ReviewAgent | `Converse` / `ConverseStream` | Claude 3.5 Sonnet หรือโมเดลที่หน่วยงานอนุมัติใน `ap-southeast-1` |
| ฝังคลังและเอกสารของฉัน | `InvokeModel` Titan Embed | `amazon.titan-embed-text-v2:0` |

มีโค้ดอยู่แล้ว: `app/providers/llm/bedrock_provider.py`, `app/providers/embedding/bedrock_provider.py`  
สิทธิ์ IAM: `bedrock:Converse`, `bedrock:ConverseStream`, `bedrock:InvokeModel` จำกัด ARN

**อย่า** ใช้ `EMBEDDING_PROVIDER=local` บน task production — นั่นคือ hybrid LLM และนอกนโยบาย Cloud ล้วน ([29](29-TBW-AWS-CLOUD-ONLY.md))

คลังถาม-ตอบ**อนุญาตสองแหล่งข้อมูล** (`global` + `mine`, หรือ Custom RAG HTTP) โดยยังฝังด้วย Bedrock — ไม่ใช่การเปิด `DEPLOYMENT_MODE=hybrid`

มิติ: Titan v2 ค่าเริ่มต้นมัก **1024**; โค้ดปัจจุบัน `_fit_dimensions` ตัดเหลือ 768 ให้ตรงคอลัมน์ RDS — ใช้ได้แต่คุณภาพด้อยกว่าการย้ายคอลัมน์เป็น 1024 (เอกสาร 27)

---

## 6. บริการที่ “เกือบทั้งหมด” แต่ยังไม่ผูกแอป (เผื่อขยาย)

ใส่ในบัญชี prod ได้เลยแม้แอปยังไม่เรียก — เป็นชั้นบัญชี:

- **Organizations** + **SCPs** (ห้ามปิด CloudTrail, ห้ามสร้าง SG 0.0.0.0/0 ต่อ DB)
- **IAM Identity Center** สำหรับคน ไม่ใช้ IAM user แชร์
- **AWS Chatbot** แจ้ง Slack/Teams เมื่อเตือน
- **Inspector** สแกนอิมเมจ ECR
- **Macie** ถ้าคลังมีข้อมูลอ่อนไหว
- **PrivateLink** ให้หน่วยงานอื่นเรียก API โดยไม่ผ่านอินเทอร์เน็ต
- **Bedrock Knowledge Bases** — ยังไม่แทน `seed_raw_docs` + pgvector ใน v0.2.4; เป็นแหล่งคลาวด์เสริมได้ในอนาคต (TBW T10/เอกสาร 29) ไม่ใช่เหตุผลเปิด hybrid
- **Step Functions** กำกับ pipeline ingest คลัง
- **EventBridge** ตั้งเวลา seed / สำรอง
- **OpenSearch Serverless** ถ้าเลิก pgvector (ต้องเขียน vector provider ใหม่ — ไม่ทำในรอบนี้)

---

## 7. แผนผังพอร์ตและความลับ

| ทรัพยากร | พอร์ตใน VPC | ใครเข้าได้ |
|----------|-------------|------------|
| ALB | 443 | CloudFront หรือโลกตาม WAF |
| Frontend task | 3000 | เฉพาะ SG ของ ALB |
| Backend task | 4000 | SG ของ ALB และ SG ของ frontend |
| RDS | 5432 | SG ของ backend เท่านั้น |
| ElastiCache | 6379 | SG ของ backend |
| Neptune | 8182 / bolt ตามเอนจิน | SG ของ backend |
| DocumentDB | 27017 | SG ของ backend (ถ้าใช้) |

ชื่อลับใน Secrets Manager (ตัวอย่าง):

- `tor/prod/rds` → JSON `{username,password,host,port,dbname}`
- `tor/prod/redis` → `{host,port,auth_token}`
- `tor/prod/jwt` → `{jwt_secret}`
- **ไม่มี** `AWS_ACCESS_KEY_ID` ในลับของ task

---

## 8. อิมเมจและ CI

| งาน | บริการ |
|-----|--------|
| เก็บอิมเมจ | **ECR** สองรีโพ `tor-frontend`, `tor-backend` |
| บิลด์บน GitHub | OIDC → บทบาท `tor-github-deploy` (ไฟล์ตัวอย่างใน `app/infra/aws/iam/github-oidc-deploy.json`) |
| บิลด์บน AWS | **CodeBuild** + **CodePipeline** จาก CodeCommit/GitHub |
| สแกนช่องโหว่ | ECR scan + Inspector |

Build context ยังเป็น `./app/frontend` และ `./app/backend` เหมือน Compose  
อย่าคัดลอก `documents/` เข้าอิมเมจ backend — ดึงคลังจาก S3 ตอน seed
