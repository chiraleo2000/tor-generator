# 26 — ติดตั้ง ตั้งค่า และเชื่อมโยง AWS (ทีละขั้น)

ทำตามลำดับ A→G ใน [24-AWS_CLOUD_OVERVIEW.md](24-AWS_CLOUD_OVERVIEW.md)  
แทนที่ `ACCOUNT_ID`, `tor.example.go.th`, รหัสผ่านตัวอย่างด้วยค่าหน่วยงาน  
Region หลักในเอกสารนี้: **`ap-southeast-1`**

โครง Terraform และไฟล์ IAM/ECS อยู่ที่ `app/infra/aws/` (apply สามรอบ: เครือข่าย → RDS/Redis → ECS ดูข้อ P)

ต้องการบนเครื่องผู้ติดตั้ง: AWS CLI v2, Docker, สิทธิ์ IAM ที่สร้าง VPC/ECS/RDS (หรือรัน Terraform ด้วย role จาก Identity Center)

```bash
aws sts get-caller-identity
aws configure get region
```

---

## A. บัญชี องค์กร และล็อกพื้นฐาน

1. สร้างหรือเลือกบัญชี **production** คนละบัญชีกับ sandbox
2. เปิด **CloudTrail** (ทุก region) เก็บใน S3 ที่ห้ามลบ
3. เปิด **GuardDuty**, **AWS Config** (กฎ S3 public, SG unrestricted)
4. สร้าง **KMS CMK** ชื่อ `tor-prod` ใช้กับ RDS/S3/Secrets
5. สร้าง **AWS Budget** เตือน 50% / 80% / 100% ของเพดานที่กำหนด + กรองบริการ `Amazon Bedrock`
6. (แนะนำ) AWS Organizations SCP: ห้ามปิด CloudTrail, ห้ามสร้าง IAM user access key โดยไม่มีแท็ก

---

## B. VPC และ endpoint

สร้าง VPC เช่น `10.40.0.0/16`:

| Subnet | ตัวอย่าง CIDR | ใช้กับ |
|--------|----------------|--------|
| public-a / public-b | `10.40.0.0/24`, `10.40.1.0/24` | NAT, ALB ถ้าไม่ใช้ CloudFront origin เป็น internal-only |
| private-app-a/b | `10.40.10.0/24`, `10.40.11.0/24` | ECS tasks |
| private-data-a/b | `10.40.20.0/24`, `10.40.21.0/24` | RDS, ElastiCache, Neptune |

NAT Gateway ใน public subnet อย่างน้อยหนึ่ง AZ (สอง AZ ถ้าต้องการ HA ของ outbound)

Gateway endpoint: **S3**  
Interface endpoints (private DNS เปิด):

- `com.amazonaws.ap-southeast-1.ecr.api` และ `.ecr.dkr`
- `logs`, `monitoring`, `secretsmanager`, `kms`, `ssm`, `ssmmessages`, `ec2messages`
- `bedrock-runtime` และ `bedrock` (ชื่อบริการตามเอกสาร AWS ของ region)
- `ecs`, `ecs-agent`, `ecs-telemetry` ตามที่ Fargate ต้องการในบัญชีนั้น

Security group แยก: `sg-alb`, `sg-ecs-fe`, `sg-ecs-be`, `sg-rds`, `sg-redis`, `sg-neptune`  
กฎ: ALB:443 จาก CloudFront prefix หรือ 0.0.0.0/0 ถ้ายังไม่มี CloudFront → FE/BE จาก ALB เท่านั้น → DB จาก `sg-ecs-be` เท่านั้น

อย่าเปิด 5432 ออกอินเทอร์เน็ต

---

## C. S3

สร้างบัคเก็ต (ชื่อต้องโกลบอล — ใส่คำนำหน้าบัญชี):

| บัคเก็ต | ใช้ |
|---------|-----|
| `tor-prod-exports` | DOCX/PDF ที่ส่งออก (`MINIO_BUCKET`) |
| `tor-prod-originals` | ไฟล์ต้นฉบับแทน GridFS |
| `tor-prod-kb-source` | PDF คลังบังคับสำหรับ seed |
| `tor-prod-logs` | CloudTrail / access log (บล็อก public) |

ทุกใบ: Block Public Access ทั้งสี่ข้อ, SSE-KMS ด้วย `tor-prod`, versioning เปิด, bucket key เปิด  
ECS task role ได้อ่าน/เขียนเฉพาะ prefix ที่ต้องใช้ ไม่ใช่ `s3:*` ทั้งบัญชี

อัปโหลดคลังจากเครื่อง (หลังมีสิทธิ์):

```bash
aws s3 sync "documents/sources" s3://tor-prod-kb-source/sources/ --sse aws:kms --exclude "*" --include "*.pdf"
```

บน Windows ถ้าชื่อโฟลเดอร์ไทยพัง ให้ zip แล้วอัปโหลดจาก WSL หรือเครื่อง Linux

---

## D. RDS PostgreSQL + pgvector

1. Subnet group ใน `private-data-*`
2. เอนจิน **PostgreSQL 16**, คลาสอย่างน้อย `db.t3.medium` (prod ใช้ Multi-AZ)
3. เข้ารหัส KMS, ไม่ public, พอร์ต 5432, SG `sg-rds`
4. รหัสผ่านเริ่มต้นเก็บใน Secrets Manager (`tor/prod/rds`) — เปิด rotation เมื่อพร้อม
5. Parameter group: ตามค่าเริ่มต้นก่อน แล้วค่อยจูน `shared_preload_libraries` ถ้า AWS รองรับ pgvector แบบนั้นในรุ่นที่เลือก
6. จาก SSM session ที่ task หรือ bastion:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

7. รัน Alembic จาก **one-shot ECS task** หรือเครื่องใน VPC:

```bash
export POSTGRES_HOST=<rds-endpoint>
export POSTGRES_USER=tor_user
export POSTGRES_PASSWORD=<from secrets>
cd app/backend
alembic upgrade head
python -m app.seed_db
```

`seed_db` สร้างบัญชี `officer@example.go.th` — **เปลี่ยนรหัสทันที** หรือปิดผู้ใช้เดโมใน prod

ตรวจ: `psql` `\dx` ต้องมี `vector`

---

## E. ElastiCache

1. Redis 7 หรือ Valkey, subnet group ข้อมูล, SG `sg-redis`
2. Encryption in-transit + at-rest, AUTH token ใน Secrets `tor/prod/redis`
3. ไม่มี public endpoint

ค่าแอป:

```env
REDIS_HOST=tor-prod.xxxxx.cache.amazonaws.com
REDIS_PORT=6379
REDIS_PASSWORD=<auth token>
REDIS_TLS=true
```

`REDIS_TLS=true` ให้แอปสร้าง `rediss://` (`Settings.redis_url` ใน `app/config.py`)  
ถ้า `PING` ล้มเพราะใบรับรอง ให้ตรวจว่า task ใช้ Amazon CA (อิมเมจ Debian/Ubuntu มีแล้ว) ไม่ต้องปิด TLS

---

## F. Bedrock

1. คอนโซล Bedrock ใน **region ที่ task ใช้** → Model access ขอโมเดลแชทและ Titan Embed
2. ทดสอบจากเครื่องที่มีสิทธิ์ (ไม่ใช่คีย์ใน Git):

```bash
aws bedrock-runtime converse --region ap-southeast-1 --model-id <MODEL_ID> --messages ...
```

ใช้ AWS CLI ตามเอกสารรุ่นปัจจุบันของ `converse`

3. ผูกสิทธิ์กับ **task role** (ไม่ใช่ execution role) ตาม `app/infra/aws/iam/ecs-task-role.json`
4. ตั้ง

```env
DEPLOYMENT_MODE=cloud
LLM_PROVIDER=bedrock
EMBEDDING_PROVIDER=bedrock
BEDROCK_REGION=ap-southeast-1
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```

เว้นคีย์ว่างไว้เพื่อให้ boto3 ใช้ task role

5. หลัง seed คลัง: Admin → ทดสอบการเชื่อมต่อ ต้องผ่านโดยไม่มี LM Studio

---

## G. ECR และอิมเมจ

```bash
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION=ap-southeast-1
aws ecr create-repository --repository-name tor-backend --region $REGION
aws ecr create-repository --repository-name tor-frontend --region $REGION
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"

docker build -t tor-backend:prod ./app/backend
docker build -t tor-frontend:prod ./app/frontend \
  --build-arg NEXT_PUBLIC_API_URL=/api/v1 \
  --build-arg BACKEND_INTERNAL_URL=http://backend.tor.local:4000/api/v1

docker tag tor-backend:prod "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/tor-backend:prod"
docker tag tor-frontend:prod "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/tor-frontend:prod"
docker push "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/tor-backend:prod"
docker push "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/tor-frontend:prod"
```

ปรับ `BACKEND_INTERNAL_URL` ให้ตรง Cloud Map หรือชื่อบริการ ECS ที่ frontend resolve ได้  
ถ้าให้ ALB ส่ง `/api/v1` ตรงไป backend แทน rewrite ของ Next ให้ตั้ง `NEXT_PUBLIC_API_URL=/api/v1` เหมือนเดิม (เบราว์เซอร์ same-origin) แล้วที่ CloudFront/ALB path route `/api/*` → target group backend — **เลือกอย่างใดอย่างหนึ่ง** อย่าพร็อกซีซ้ำสองชั้นโดยไม่ตั้ง timeout

Timeout พร็อกซี Next ใน Docker คือ 300s — บน ALB ตั้ง idle timeout ≥ 300 (ร่างยาวแนะนำ 900)

---

## H. IAM ของ ECS

สองบทบาท:

| Role | ใช้ |
|------|-----|
| **execution** | ดึงอิมเมจ ECR, เขียนล็อก, อ่าน Secrets ตอนสตาร์ท task |
| **task** | Bedrock, S3, KMS decrypt ของข้อมูลแอป, X-Ray |

ไฟล์ตัวอย่าง: `app/infra/aws/iam/ecs-execution-role.json`, `ecs-task-role.json`  
อย่าใส่ `AdministratorAccess`

---

## I. ECS cluster, ALB, งานบริการ

1. Cluster Fargate `tor-prod`
2. Cloud Map namespace `tor.local` — บริการ `backend` พอร์ต 4000
3. Task definition จาก `app/infra/aws/ecs/*.json` แทนที่ ARN
4. Service frontend desired 2, backend desired **1** จนกว่าคิวร่างจะออกจากหน่วยความจำ (เอกสาร 24 ข้อเสี่ยง 3) จากนั้นค่อย 2+
5. ALB:
   - HTTPS 443 + ACM
   - Target group FE `:3000` health `/`
   - Target group BE `:4000` health **`/health`** (แอป mount ทั้ง `/health` และ `/api/v1/health`)
6. Health backend ต้องชี้ RDS, Redis, S3 (ฟิลด์ `minio` ใน JSON คือที่เก็บวัตถุ — จะ healthy เมื่อคุย S3 ได้)

ตัวอย่างตรวจ:

```bash
curl.exe -sS https://tor.example.go.th/api/v1/health
```

ต้องมี `"status":"healthy"` และบริการย่อย `up`

---

## J. Secrets ใน task definition

ใช้ `valueFrom` ชี้ ARN:

```json
{
  "name": "POSTGRES_PASSWORD",
  "valueFrom": "arn:aws:secretsmanager:ap-southeast-1:ACCOUNT:secret:tor/prod/rds:password::"
}
```

รูปแบบ JSON key ใน secret ต้องตรง  
`JWT_SECRET` ความยาว ≥ 32  
`COOKIE_SECURE=true`  
`CORS_ORIGINS=https://tor.example.go.th`

---

## K. เชื่อม MinIO SDK → S3

```env
MINIO_ENDPOINT=s3.ap-southeast-1.amazonaws.com
MINIO_BUCKET=tor-prod-exports
MINIO_SECURE=true
MINIO_REGION=ap-southeast-1
MINIO_USE_IAM=true
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
```

`MINIO_USE_IAM=true` ให้ SDK ใช้ task role (ดูโค้ด `build_minio_client` ใน `app/export/minio_storage.py`)  
ถ้ายังใช้คีย์ชั่วคราวระหว่างย้าย ให้ใส่ access/secret จาก Secrets แล้วตั้ง `MINIO_USE_IAM=false`

อย่าตั้ง `secure=false` กับ S3 สาธารณะ

---

## L. Seed คลังบนคลาวด์

รัน **task ครั้งเดียว** จากอิมเมจ backend (task role อ่านบัคเก็ตคลังได้ — มี boto3 แล้ว ไม่ต้องติดตั้ง AWS CLI):

```bash
export KB_SOURCE_BUCKET=tor-prod-kb-source
export KB_LOCAL_DIR=/tmp/kb
export KB_SOURCE_PREFIX=sources/
python -m app.storage.s3_kb_sync
```

โมดูลนี้ซิงก์ S3 แล้วตั้ง `KB_SOURCES_ROOT` ก่อน `python -m app.seed_raw_docs`  
บน bastion ที่มี AWS CLI ใช้ `app/infra/aws/scripts/pull-kb-from-s3.sh` แทนได้

อย่า COPY PDF เข้า Docker image

หลังเปลี่ยน embedding provider **ต้อง seed ใหม่** — มิติเวกเตอร์คนละชุดกับ Gemma 768

ตรวจถาม-ตอบ: ล็อกอินแล้วถามงวดจ่าย ต้องมีคำตอบและชิปอ้างอิง

---

## M. โดเมน ขอบ และ WAF

1. ACM ใบรับรองโดเมน
2. Route 53 alias → CloudFront (แนะนำ) หรือ ALB
3. CloudFront origin = ALB, HTTPS only, HTTP/2
4. WAF: AWS Managed Core + anonymous IP + rate limit ต่อ IP สำหรับ `/api/v1/auth/login` และ `/api/v1/chat`
5. (ตัวเลือก) AWS Shield Standard มีอยู่แล้ว; Advanced ตามงบ

คุกกี้ `tor_access_token`: Secure + HttpOnly — แอปมี `COOKIE_SECURE`

---

## N. ล็อก เตือน สำรอง

- Log group `/ecs/tor-backend`, `/ecs/tor-frontend` retention 90 วัน (หรือตามระเบียบ)
- Alarm: ALB 5xx, unhealthy host, RDS CPU, Redis evictions, ECS CPU
- Alarm Bedrock: ใช้เมตริก invocation / throttles
- AWS Backup: RDS รายวัน + retention ตามระเบียบพัสดุ/บัญชี
- อย่าเก็บเนื้อหา TOR ทั้งฉบับใน X-Ray annotations

---

## O. เช็กลิสต์ก่อนเปิดให้เจ้าหน้าที่

- [ ] Model access Bedrock อนุมัติแล้วใน region ของ task
- [ ] Task role เรียก Converse ได้; ไม่มี access key ใน env
- [ ] RDS `vector` extension + alembic head + ผู้ใช้จริง (ไม่ใช้รหัสเดโม)
- [ ] Redis AUTH+TLS ตามที่เปิด
- [ ] S3 Block Public + ทดสอบอัปโหลด/ส่งออก
- [ ] `/health` healthy ผ่าน HTTPS
- [ ] ล็อกอิน ร่างขั้นที่ ๐ วิเคราะห์หนึ่งโครงการ
- [ ] ถาม-ตอบคลังได้หลัง seed
- [ ] ตรวจ TOR สแตนด์อโลนอัปโหลดไฟล์ได้
- [ ] WAF ไม่บล็อกเส้นทางปกติของเจ้าหน้าที่
- [ ] Budget Bedrock เปิดแล้ว
- [ ] สำรอง RDS ทดสอบ restore ในบัญชีทดลองอย่างน้อยหนึ่งครั้ง

---

## P. รัน Terraform (ทางลัดเมื่อพร้อม)

จาก `app/infra/aws/terraform`:

```bash
cp terraform.tfvars.example terraform.tfvars
# ตั้ง bucket_prefix ให้โกลบอล เช่น ACCOUNTID-tor
terraform init
terraform plan
terraform apply
```

สามรอบ (ค่าเริ่มต้นคือรอบ 1 — ยังไม่มี RDS/ECS):

1. `enable_managed_data=false` `enable_ecs=false` — VPC, NAT, S3, ECR, IAM, KMS, Secrets เปล่า
2. `enable_managed_data=true` — RDS PostgreSQL 16 Multi-AZ + ElastiCache (คิดเงินรายเดือน)
3. `enable_ecs=true` พร้อม `certificate_arn` — ALB + Fargate หลังดันอิมเมจ `:prod` ไป ECR

รายละเอียดตัวแปรดู `app/infra/aws/terraform/README.md`  
อย่า apply ในบัญชีจริงโดยไม่ plan และไม่ตั้งงบเตือน Bedrock
