# คู่มือติดตั้งเว็บแอป TOR และบริการ RAG บน AWS

เวอร์ชันแอป **v0.7.1** · Region **`ap-southeast-1` (สิงคโปร์)**  
เครื่องที่ใช่ในคู่มือนี้: **EC2 `t3.medium` เครื่องเดียว** · คลังและไฟล์อยู่บน **S3 เป็นหลัก**

แพ็กเกจที่รันจริง: [`app/infra/pn-ec2/`](app/infra/pn-ec2/)  
ต้นทางออกแบบ: Discussions 33, 35, 36, 38 และ [`app/infra/quick/คู่มือติดตั้ง-AWS-cloud.md`](app/infra/quick/คู่มือติดตั้ง-AWS-cloud.md)

คู่มือนี้เป็นฉบับเดียวจบ ไม่ใช้ ECS Fargate, ALB, RDS หรือ ElastiCache  
Postgres / Redis / Mongo รันใน Docker บนดิสก์ของ EC2 เพื่อเก็บสถานะแอป (ผู้ใช้ โครงการ คิว)  
**ไฟล์ต้นฉบับ ไฟล์ส่งออก และคลังความรู้ อยู่บน S3** ส่วนเวกเตอร์สำหรับค้นอยู่บน **S3 Vectors** (บริการเวกเตอร์ของ S3 ไม่ใช่ฐานข้อมูลแยก)

> ถ้าคำสั่งในคู่มือนี้ขัดกับไฟล์ใน `app/infra/pn-ec2/` ให้ยึดไฟล์ในแพ็กเกจนั้นเป็นค่าที่รันจริง

อิมเมจ Docker ของ `frontend` / `backend` **ชุดเดียวกับเครื่องพัฒนา** — สลับผู้ให้บริการด้วย env (`LLM_PROVIDER=lm_studio` ท้องถิ่น หรือ `bedrock` / `openai` / `claude` บน VM) อย่า hardcode หน้าต่าง 131k, คิดแบบ thinking หรือมิติเวกเตอร์ 768 เมื่อรันบน Bedrock (Cohere embed-v4 มิติ 1024)

---

## 1. สิ่งที่ได้เมื่อทำจบ

- เว็บ `https://<โดเมน>` ล็อกอิน ร่าง และตรวจ TOR ได้
- API `https://<โดเมน>/api/v1/health` ตอบว่าพร้อม
- เอกสารคลังอยู่บน S3 และค้นหาได้หลังฝังเวกเตอร์
- Amazon Quick เรียก `https://<โดเมน>/mcp` แล้วได้ชิ้นเอกสารจริงภายใน 60 วินาที

```text
เจ้าหน้าที่ / Amazon Quick
        │  HTTPS :443  (เฉพาะ IP สำนักงานหรือ VPN)
        ▼
   EC2 t3.medium
   nginx
   ├─ /      → frontend  Next.js :3000     build จาก app/frontend
   ├─ /api   → backend   FastAPI :4000     build จาก app/backend
   └─ /mcp   → amazon-quick :8767 → mcp-rag
                    │
        Amazon Bedrock
        ├─ แชท / ร่าง / ตรวจ   ตามโมเดลที่หน่วยงานอนุมัติ
        └─ ฝังเวกเตอร์         cohere.embed-v4:0  (มิติ 1024)
                    │
        S3 บัคเก็ตไฟล์          PDF, DOCX, manifest, ชิ้นข้อความ, ไฟล์ส่งออก
        S3 Vectors              embedding ต่อกลุ่มเอกสาร
```

| ชิ้น | ที่รัน | หมายเหตุ |
|------|--------|----------|
| หน้าเว็บ | คอนเทนเนอร์ `frontend` | ต้องเป็นโปรเซส Node เพราะเป็น SSR อย่าวางโฟลเดอร์ `out/` ลง S3 แล้วถือว่าเป็นแอป |
| API | คอนเทนเนอร์ `backend` | รวม `/api/v1/pn/kb/*` สำหรับคลังบน S3 |
| จุดที่ Quick เรียก | `amazon-quick` :8767 | ผู้ใช้ภายนอกเข้าที่ `/mcp` ผ่าน nginx เท่านั้น |
| ค้นคลัง | `mcp-rag` | อ่าน S3 Vectors |
| สถานะแอป | Postgres, Redis, Mongo, Neo4j บนดิสก์ EC2 | ไม่ใช่ที่เก็บเวกเตอร์คลัง |
| ไฟล์ | S3 | Block Public Access |
| เวกเตอร์ | S3 Vectors มิติ 1024 | คนละทรัพยากรกับบัคเก็ตไฟล์ |

ซอร์สที่ build ต้องเป็น **`app/frontend`** และ **`app/backend`**  
อย่าใช้โฟลเดอร์ `frontend/` ที่รากรีโป เพราะมักไม่มี `Dockerfile`  
Compose ของแพ็กเกจนี้อยู่ที่ `app/infra/pn-ec2/` และชี้ build ไป `app/frontend` อยู่แล้ว

---

## 2. ค่าที่ล็อกไว้ — อย่าเปลี่ยนเอง

| รายการ | ค่าที่ใช้ |
|--------|----------|
| เครื่อง | **EC2 `t3.medium`** (2 vCPU / 4 GB) |
| ดิสก์ | gp3 **อย่างน้อย 50 GB** (ขั้นต่ำที่ยอมรับได้ 30 GB) |
| ระบบปฏิบัติการ | Amazon Linux 2023 หรือ Ubuntu 22.04 |
| Region | `ap-southeast-1` |
| โหมดแอป | `DEPLOYMENT_MODE=cloud` |
| โมเดลตอบ | `LLM_PROVIDER=bedrock` |
| โมเดลฝัง | `EMBEDDING_PROVIDER=bedrock` และ `BEDROCK_EMBEDDING_MODEL_ID=cohere.embed-v4:0` |
| ที่เก็บไฟล์ | S3 ผ่าน MinIO SDK (`MINIO_SECURE=true`, `MINIO_USE_IAM=true`) |
| ที่เก็บเวกเตอร์ | `PN_RETRIEVE_BACKEND=s3_vectors` |
| มิติเวกเตอร์ | **1024** |
| ขนาดชิ้นข้อความ | ประมาณ **4096** โทเคน เหลื่อม 384 |
| ค้นต่อครั้ง | `top_k` เริ่มที่ 3 ไม่เกิน 5 |
| สิทธิ์ AWS | IAM instance profile ของเครื่อง **ไม่ใส่ access key ใน `.env`** |

ค่าใช้จ่ายโดยประมาณใน `ap-southeast-1` (ไม่ใช่ใบเสนอราคา ตรวจ Pricing Calculator ก่อนจัดซื้อ):

| รายการ | ประมาณการ |
|--------|-----------|
| EC2 t3.medium | ประมาณ 30–40 USD/เดือน |
| ดิสก์ gp3 50 GB | ประมาณ 4–5 USD/เดือน |
| Elastic IP ที่ผูกเครื่องอยู่ | 0 USD |
| ปีแรก คลังยังไม่ใหญ่ | ประมาณ **40–70 USD/เดือน** ไม่รวมแชทหนัก |
| S3 Vectors ประมาณ 1 TB (ปีหลังเมื่อคลังใหญ่) | บวกประมาณ 60 USD/เดือน |

งบที่ระเบิดเร็วที่สุดคือ **โทเคน Bedrock และแชทของ Amazon Quick** ไม่ใช่ค่าเครื่อง  
ตั้ง AWS Budget ก่อนเปิดโมเดล

สิ่งที่คู่มือนี้ไม่ติดตั้ง: ECS, Fargate, ALB, RDS, OpenSearch, Neptune, NAT หลายตัว

---

## 3. กติกาที่ห้ามผิด

1. บน EC2 **เว้นว่าง** `AWS_ACCESS_KEY_ID` และ `AWS_SECRET_ACCESS_KEY` ให้เครื่องใช้ instance profile
2. `NEXT_PUBLIC_API_URL` ต้องเป็น **`/api/v1`** ห้ามใส่ชื่อโฮสต์ Docker `backend` ให้เบราว์เซอร์เห็น  
   `BACKEND_INTERNAL_URL=http://backend:4000/api/v1` ใช้ได้ เพราะเป็นที่อยู่ภายใน Compose ที่ Next เรียกเอง
3. เมื่อมี HTTPS ให้ตั้ง `COOKIE_SECURE=true` และ `CORS_ORIGINS=https://<โดเมนจริง>`
4. เปิดพอร์ต **443** จาก IP สำนักงานหรือ VPN เท่านั้น ใช้ SSM Session Manager แทนการเปิด SSH กว้าง
5. ห้ามเปิด 5432, 6379, 27017, 7687, 8765, 8767 สู่อินเทอร์เน็ต ผู้ใช้เข้า MCP ผ่าน `/mcp` บนพอร์ต 443
6. ห้าม commit `.env` ใบรับรอง และโทเคน ห้ามเหลือคำว่า `changeme_` ในค่าสำคัญ
7. หลัง seed ผู้ใช้ทดลอง `officer@example.go.th` ให้เปลี่ยนรหัสทันทีหรือปิดบัญชีเดโม
8. หน้าสร้างโครงการต้องเลือก **หมวดใหญ่ 7 ประเภท** ไม่มีค่าเริ่มต้น ถ้าไม่มีตัวเลือกแสดง อย่าเปิดใช้จริง
9. ห้ามชี้เครื่องนี้ไป LM Studio หรือ Ollama ในสำนักงาน แชทและฝังเวกเตอร์ใช้ Bedrock เท่านั้น  
   เครื่องพัฒนาในสำนักงานใช้โมเดลท้องถิ่นได้ แต่โดเมนที่เจ้าหน้าที่ใช้ห้ามชี้กลับไปที่นั่น
10. Amazon Quick ไม่ใช่ QuickSight และไม่สร้างไฟล์ DOCX/PDF การส่งออกทำบนเว็บแอป
11. อ้างมาตรากฎหมายได้เฉพาะชิ้นที่ผลการค้นคืนมา ห้ามให้โมเดลแต่งกฎหมาย
12. บัคเก็ตไฟล์กับ vector bucket เป็นคนละอย่าง อย่าใส่ชื่อเดียวกันแล้วเข้าใจว่าเป็นที่เก็บเดียวกัน
13. เปลี่ยนมิติเวกเตอร์ไม่ได้บน index เดิม ต้องสร้าง index ใหม่แล้วฝังคลังใหม่
14. MCP ใช้ค้นอย่างเดียว ไม่ใช่ช่องอัปโหลดเอกสาร

---

## 4. คนและเครื่องมือก่อนเริ่ม

| บทบาท | ทำอะไร |
|--------|--------|
| ผู้ดูแล AWS | สร้าง EC2, IAM, S3, S3 Vectors, เปิด Bedrock, DNS, ใบรับรอง, งบ, กรอก `.env` |
| Admin ในแอป | สร้างผู้ใช้ อัปโหลดคลังลง S3 พร้อมฝังเวกเตอร์ ตรวจผลการค้น |
| ผู้ใช้ทั่วไป | เข้าเว็บหรือ Quick ไม่ต้องเข้า Console |

บนเครื่องผู้ดูแลตอนเตรียมงาน: Git, AWS CLI v2, Python 3.11 ขึ้นไป (ใช้สร้างชุดเอกสาร)  
บน EC2 ต้องมี: Docker Engine, คำสั่ง `docker compose` (มีเว้นวรรค), Git

ตรวจสิทธิ์ก่อนสร้างของ:

```bash
aws sts get-caller-identity
aws configure get region
```

ต้องเห็นบัญชีที่ตั้งใจใช้ และ region เป็น `ap-southeast-1`

เตรียมโดเมน เช่น `tor.example.go.th` ให้ชี้ Elastic IP ของเครื่องนี้  
สุ่มความลับบน Linux ด้วย `openssl rand -hex 32` อย่างน้อยสี่ค่า: `JWT_SECRET`, `QUICK_MCP_AUTH_VALUE`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD` (และ `NEO4J_PASSWORD` ถ้าเปิด Neo4j)

---

## 5. สร้างของบน AWS (ทำครั้งแรก)

ทำทั้งหมดใน region **`ap-southeast-1`** ส่วนนี้เป็นงานบน Console สคริปต์ในรีโปสร้างให้ไม่ครบ

### 5.1 งบและบันทึก

1. Billing → Budgets เตือนเมื่อใช้ไป 50 / 80 / 100 เปอร์เซ็นต์ กรองบริการ EC2, S3 และ **Amazon Bedrock**
2. เปิด CloudTrail ของบัญชีนี้

### 5.2 เปิดโมเดล Bedrock

1. Amazon Bedrock → Model access
2. เปิดโมเดลแชทที่หน่วยงานอนุมัติ แล้วจด model id ไว้ใส่ `BEDROCK_MODEL_ID`  
   ไฟล์ตัวอย่างใช้ `anthropic.claude-3-5-sonnet-20241022-v2:0` เป็นค่าตั้งต้นเท่านั้น ใช้ตัวที่เปิดใน region นี้ได้จริง
3. เปิด **`cohere.embed-v4:0`**
4. รอสถานะ Access granted ก่อนอัปโหลดคลังหรือร่าง TOR

### 5.3 สร้างบัคเก็ตไฟล์บน S3

ใช้เก็บ PDF/DOCX, manifest, JSON ของชิ้นข้อความ และไฟล์ที่เว็บส่งออก

1. ชื่อเช่น `pn-tor-kb-<หน่วยงาน>` ต้องไม่ซ้ำทั้งโลก
2. Region `ap-southeast-1`
3. เปิด **Block Public Access ทั้งสี่ข้อ**
4. เข้ารหัส SSE-S3 หรือ SSE-KMS ตามนโยบายหน่วยงาน แนะนำเปิด versioning
5. จดชื่อนี้ใส่ทั้ง `PN_S3_BUCKET` และ `MINIO_BUCKET`

ไม่ต้องสร้างโฟลเดอร์ล่วงหน้า ระบบสร้าง prefix เองตอนอัปโหลด:

```text
s3://{ชื่อบัคเก็ต}/rags/procurement-th/sources/
s3://{ชื่อบัคเก็ต}/rags/procurement-th/manifest/
s3://{ชื่อบัคเก็ต}/rags/procurement-th/chunks/
s3://{ชื่อบัคเก็ต}/rags/agency-extra/...
```

### 5.4 สร้าง S3 Vectors สำหรับค้น

เวกเตอร์ไม่อยู่ใน Postgres บนเครื่อง

1. สร้าง **vector bucket** คนละใบกับบัคเก็ตไฟล์ → `PN_S3_VECTOR_BUCKET`
2. สร้าง index มิติ **1024** ให้ชื่อตรง [`app/infra/pn-ec2/rag-groups.yaml`](app/infra/pn-ec2/rag-groups.yaml)

| กลุ่มเอกสาร | ใช้เมื่อ | ชื่อ index |
|-------------|----------|------------|
| `procurement-th` | กฎหมายและระเบียบจัดซื้อจัดจ้าง | `procurement-th-embed4-v1` |
| `agency-extra` | เอกสารเฉพาะหน่วยงาน | `agency-extra-embed4-v1` |

ชื่อหน้าจอ S3 Vectors อาจต่างตามรุ่น Console ใช้คำสั่ง `s3vectors` ของ AWS CLI ตามเอกสารปัจจุบันของ region ได้

### 5.5 สร้าง IAM role ให้เครื่อง EC2

1. IAM → Roles → Create role ชนิด EC2
2. ใส่นโยบายจาก [`app/infra/pn-ec2/iam/ec2-instance-profile.json`](app/infra/pn-ec2/iam/ec2-instance-profile.json)
3. ก่อนแนบ ให้แทนชื่อในไฟล์
   - `changeme-pn-tor-kb` → ชื่อบัคเก็ตไฟล์จริง
   - `changeme-pn-tor-vectors` → ชื่อ vector bucket จริง
4. ค้นในนโยบายว่าไม่มีคำว่า `changeme-` เหลือ
5. ตั้งชื่อ role เช่น `tor-pn-ec2`
6. ถ้าจะเข้าเครื่องด้วย Session Manager ให้แนบนโยบาย `AmazonSSMManagedInstanceCore` เพิ่ม

สิทธิ์ที่เครื่องต้องมี คือเรียก Bedrock ได้, อ่านเขียนบัคเก็ตไฟล์ของโครงการได้, ใส่และค้นเวกเตอร์ใน vector bucket ได้  
อย่าแนบ `AdministratorAccess`

### 5.6 สร้าง EC2 t3.medium

1. Launch instance
   - AMI: Amazon Linux 2023 หรือ Ubuntu 22.04
   - Type: **`t3.medium`**
   - Disk: gp3 50 GB
2. วางใน subnet ที่ออกอินเทอร์เน็ตได้ เพื่อเรียก Bedrock และดึงอิมเมจฐาน  
   Security Group ต้องแคบตามตารางด้านล่าง ถหน่วยงานห้ามให้เครื่องมีที่อยู่สาธารณะ ให้ใส่ VPC endpoint ของ S3 และ `bedrock-runtime` แล้วให้ออกเน็ตผ่าน NAT แทน
3. Security Group ชื่อเช่น `sg-tor-pn`

| พอร์ต | อนุญาตจาก | หมายเหตุ |
|-------|-----------|----------|
| 443 | IP สำนักงานหรือ VPN เท่านั้น | เว็บ, API และ `/mcp` |
| 80 | ช่วงขอใบรับรองเท่านั้น | ปิดได้หลังได้ใบ ถ้าไม่ได้ใช้พอร์ต 80 ต่ออายุใบ |
| 22 | ปิด หรือจำกัด IP ผู้ดูแลคนเดียว | ใช้ SSM แทน |

4. ตอน launch ให้เลือก instance profile `tor-pn-ec2` ถ้าแนบทีหลังแล้วคำสั่ง `aws` บนเครื่องยังไม่เห็น role ให้รีสตาร์ท instance
5. จอง Elastic IP แล้วผูกกับเครื่องนี้
6. สร้างระเบียน DNS ชนิด A ชี้ Elastic IP ชื่อโฮสต์นี้คือค่า `PN_PUBLIC_HOST` (ไม่ใส่ `https://`)

เข้าเครื่อง:

```bash
aws ssm start-session --target i-xxxxxxxx --region ap-southeast-1
```

---

## 6. ติดตั้ง Docker และวางโค้ดบนเครื่อง

Amazon Linux 2023:

```bash
sudo dnf update -y
sudo dnf install -y docker git
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user
```

ออกจากเซสชันแล้วเข้าใหม่ เพื่อให้กลุ่ม `docker` มีผล จากนั้นติดตั้ง Compose plugin:

```bash
sudo mkdir -p /usr/libexec/docker/cli-plugins
sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
  -o /usr/libexec/docker/cli-plugins/docker-compose
sudo chmod +x /usr/libexec/docker/cli-plugins/docker-compose
docker compose version
```

บน Ubuntu 22.04 ใช้แพ็กเกจ Docker ของดิสโทรนั้นได้ ผลที่ต้องได้คือคำสั่ง `docker compose` ใช้ได้

โคลนรีโป (ใส่ URL ของหน่วยงาน):

```bash
git clone <URL-repo-ของหน่วยงาน> tor-app
cd tor-app
```

ต้องเห็นไฟล์ `app/frontend/Dockerfile` และ `app/backend/Dockerfile`

---

## 7. กรอกไฟล์ `.env`

```bash
cd ~/tor-app/app/infra/pn-ec2
cp .env.example .env
chmod 600 .env
nano .env
```

สร้างไฟล์บน EC2 โดยตรง อย่า commit และเลี่ยงการส่งไฟล์นี้ทางแชต

### 7.1 ค่าที่ต้องเปลี่ยน

| ตัวแปร | ใส่ค่าอะไร |
|--------|------------|
| `PN_PUBLIC_HOST` | โดเมนจริง ไม่ใส่ `https://` |
| `CORS_ORIGINS` | `https://` ตามด้วยโดเมนเดียวกัน |
| `COOKIE_SECURE` | `true` |
| `PN_S3_BUCKET` และ `MINIO_BUCKET` | ชื่อบัคเก็ตไฟล์บน S3 |
| `PN_S3_VECTOR_BUCKET` | ชื่อ vector bucket |
| `JWT_SECRET` | สุ่ม ความยาวอย่างน้อย 32 ตัว |
| `QUICK_MCP_AUTH_VALUE` | สุ่ม เก็บไว้ตั้ง Amazon Quick |
| `POSTGRES_PASSWORD` | สุ่ม |
| `REDIS_PASSWORD` | สุ่ม |
| `NEO4J_PASSWORD` | สุ่ม |
| `BEDROCK_MODEL_ID` | โมเดลแชทที่เปิดสิทธิ์แล้ว |
| `AWS_ACCESS_KEY_ID` และ `AWS_SECRET_ACCESS_KEY` | เว้นว่าง |

### 7.2 ค่าที่คงไว้

```env
AWS_REGION=ap-southeast-1
AWS_DEFAULT_REGION=ap-southeast-1
BEDROCK_REGION=ap-southeast-1
DEPLOYMENT_MODE=cloud
PIN_ON_PREM_LLM=false
LLM_PROVIDER=bedrock
EMBEDDING_PROVIDER=bedrock
BEDROCK_EMBEDDING_MODEL_ID=cohere.embed-v4:0
EMBEDDING_DIMENSIONS=1024
PN_RETRIEVE_BACKEND=s3_vectors
PN_DEFAULT_RAG_GROUP=procurement-th
PN_CHUNK_TARGET_TOKENS=4096
PN_CHUNK_OVERLAP_TOKENS=384
PN_RETRIEVE_TOP_K=3
PN_RETRIEVE_TOP_K_MAX=5
PN_S3_VECTOR_INDEX_PROCUREMENT=procurement-th-embed4-v1
PN_S3_VECTOR_INDEX_AGENCY=agency-extra-embed4-v1
MINIO_ENDPOINT=s3.ap-southeast-1.amazonaws.com
MINIO_SECURE=true
MINIO_REGION=ap-southeast-1
MINIO_USE_IAM=true
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
NEXT_PUBLIC_API_URL=/api/v1
BACKEND_INTERNAL_URL=http://backend:4000/api/v1
REDIS_TLS=false
QUICK_MCP_AUTH_HEADER=Authorization
QUICK_RAG_MCP_URL=http://mcp-rag:8765/mcp
```

`REDIS_TLS=false` ถูกต้อง เพราะ Redis อยู่ในเครื่องเดียวกัน ไม่ได้ไป ElastiCache  
ชื่อ index ต้องตรงกันสามที่: หน้า S3 Vectors, ตัวแปร `PN_S3_VECTOR_INDEX_*`, และ `rag-groups.yaml`

ตรวจว่าไม่มีค่าตัวอย่างค้าง:

```bash
grep -n changeme .env || echo "ไม่มีคำว่า changeme"
```

---

## 8. ยกแอปขึ้นและเปิด HTTPS

```bash
cd ~/tor-app/app/infra/pn-ec2
chmod +x scripts/*.sh
./scripts/bootstrap-ec2.sh
```

สคริปต์จะเตือนถ้า `.env` ยังเป็นตัวอย่าง แล้วสร้างคอนเทนเนอร์  
ครั้งแรกใช้เวลานานเพราะ build จาก `app/frontend` และ `app/backend`

ดูสถานะถ้าค้าง:

```bash
docker compose -f docker-compose.pn.yml --env-file .env ps
docker compose -f docker-compose.pn.yml --env-file .env logs -f backend
```

บริการที่ต้องเห็น: `frontend`, `backend`, `mcp-rag`, `amazon-quick`, `postgres`, `redis`, `mongo`  
`neo4j` เป็นกราฟเสริมบนเครื่อง ไม่ใช่ที่เก็บคลัง S3

เปิด reverse proxy:

```bash
cp nginx/pn.conf.example nginx/pn.conf
docker compose -f docker-compose.pn.yml --profile with-nginx --env-file .env up -d
```

nginx ส่งทางนี้:

| ที่อยู่สาธารณะ | ปลายทางในเครื่อง |
|----------------|------------------|
| `/` | หน้าเว็บ พอร์ต 3000 |
| `/api/` | API พอร์ต 4000 รอได้นานถึง 600 วินาที สำหรับร่างหมวดยาว |
| `/mcp` | Amazon Quick sidecar พอร์ต 8767 จำกัด 60 วินาที |
| `/health-mcp` | ตรวจสุขภาพของ sidecar |

ไฟล์ตัวอย่าง `pn.conf` ฟังพอร์ต 80 เป็นหลัก **ต้องแก้ `server_name` เป็นโดเมนจริง และเพิ่มการฟังพอร์ต 443** ก่อนให้เจ้าหน้าที่ล็อกอิน อย่าปล่อยให้ใช้ HTTP ในเครือข่ายที่ไม่ไว้ใจ

ออกใบรับรองอย่างใดอย่างหนึ่ง:

1. Let's Encrypt ด้วย certbot บนเครื่อง แล้ววางใบใน `app/infra/pn-ec2/nginx/certs/`
2. ใบที่หน่วยงานออกเอง วางในโฟลเดอร์เดียวกัน แล้วชี้ `ssl_certificate` ใน `nginx/pn.conf`

ก่อนขอใบแบบ HTTP ต้องให้ DNS ชี้ Elastic IP แล้ว และเปิดพอร์ต 80 ช่วงขอใบ หลังได้ใบแล้วปิดพอร์ต 80 ได้ถ้าไม่ได้ใช้ต่ออายุด้วยวิธีนั้น  
จากนั้นตั้ง `PN_PUBLIC_SCHEME=https` กับ `COOKIE_SECURE=true` แล้วเปิด nginx profile อีกครั้ง

---

## 9. ตรวจว่าเครื่องและเว็บพร้อม

บน EC2 ตรวจว่า role ทำงานโดยไม่มีคีย์:

```bash
aws sts get-caller-identity
aws s3 ls "s3://ชื่อบัคเก็ตไฟล์" --region ap-southeast-1
```

คำสั่งแรกต้องโชว์ role ของ instance ถ้าคำสั่งที่สองถูกปฏิเสธ ให้กลับไปตรวจว่าแทนชื่อบัคเก็ตในนโยบายแล้ว และแนบ instance profile แล้ว

ตรวจแอป:

```bash
cd ~/tor-app/app/infra/pn-ec2
./scripts/healthcheck.sh
```

จากเครื่องที่ Security Group อนุญาต:

```bash
curl -sf "https://โดเมน/api/v1/health"
curl -sf -X POST "https://โดเมน/mcp" \
  -H "Content-Type: application/json" \
  -H "Authorization: ค่าQUICK_MCP_AUTH_VALUE" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

คาดหวังว่า health ของ API ผ่าน และ MCP ตอบชื่อเซิร์ฟเวอร์แนว `tor-amazon-quick`

ถ้ายังไม่มีผู้ใช้:

```bash
docker compose -f docker-compose.pn.yml --env-file .env exec backend python -m app.seed_db
```

บัญชีเดโมคือ `officer@example.go.th` เปลี่ยนรหัสทันทีหลังเข้าเว็บได้  
เปิด `https://<โดเมน>` แล้วตรวจว่าหน้าสร้างโครงการมีหมวดใหญ่ 7 ประเภท

---

## 10. โหลดคลังความรู้ขึ้น S3 แล้วฝังเวกเตอร์

มีไฟล์บน S3 อย่างเดียวค้นไม่เจอ ต้องฝังเวกเตอร์หลังอัปโหลด  
ระบบจะดึงข้อความ ตัดชิ้นประมาณ 4096 โทเคน เรียก Cohere Embed 4 แล้วใส่ S3 Vectors

MCP คืนเฉพาะชิ้นข้อความ ชื่อแหล่ง และคะแนน ไม่คืนทั้งไฟล์

### 10.1 ส่งทั้งชุดขึ้น S3

บนเครื่องพัฒนา จากราก repo:

```bash
python documents/exports/build_pn_aws_dataset.py --version 0.7.1
```

ได้ไฟล์ `documents/exports/tor-pn-aws-dataset-v0.7.1.zip` แตกแล้วตั้งใน `.env` ของเครื่องที่มี AWS CLI:

```env
PN_DATASET_LOCAL_PATH=/path/to/extracted/rag-pdfs
PN_S3_SOURCES_PREFIX=rags/procurement-th/sources/
```

```bash
cd app/infra/pn-ec2
./scripts/sync-dataset-to-s3.sh
```

บน Windows ใช้ `.\scripts\sync-dataset-to-s3.ps1`  
เครื่องที่รันสคริปต์ล็อกอิน AWS CLI ได้ด้วย `aws sso login` หรือโปรไฟล์ชั่วคราว ไม่ต้องใส่คีย์ลง `.env` ของ EC2  
บน Windows ถ้าชื่อโฟลเดอร์ไทยทำให้คำสั่ง sync พัง ให้ zip แล้วอัปโหลดจาก WSL หรือจาก EC2

หลัง sync ยังไม่มีเวกเตอร์ ต้องทำข้อ 10.2 หรือ 10.3

### 10.2 อัปโหลดทีละไฟล์พร้อมฝัง (วิธีที่ใช้ง่ายสุด)

ล็อกอินเป็น Admin แล้วเอาโทเคน:

```bash
curl -X POST "https://โดเมน/api/v1/pn/kb/upload" \
  -H "Authorization: Bearer โทเคน" \
  -F "file=@ระเบียบ.pdf" \
  -F "rag_group=procurement-th" \
  -F "ingest=true"
```

### 10.3 ฝังไฟล์ที่มีบน S3 แล้ว

```bash
curl -X POST "https://โดเมน/api/v1/pn/kb/ingest" \
  -H "Authorization: Bearer โทเคน" \
  -H "Content-Type: application/json" \
  -d '{"object_key":"rags/procurement-th/sources/ชื่อไฟล์.pdf","rag_group":"procurement-th"}'
```

### 10.4 ทดค้นก่อนต่อ Quick

```bash
curl -X POST "https://โดเมน/api/v1/pn/kb/search" \
  -H "Authorization: Bearer โทเคน" \
  -H "Content-Type: application/json" \
  -d '{"query":"ราคากลางที่ปรึกษา","rag_group":"procurement-th","top_k":3}'
```

ดูกลุ่ม: `GET /api/v1/pn/kb/groups`  
ดูไฟล์ในกลุ่ม: `GET /api/v1/pn/kb/objects?rag_group=procurement-th` หรือเปิด S3 Console ที่ prefix เดียวกัน

เอกสารเฉพาะหน่วยงานให้อัปโหลดด้วย `rag_group=agency-extra` เพื่อไม่ปน index กับคลังกฎหมาย

---

## 11. ต่อ Amazon Quick

ทำหลัง HTTPS ใช้ได้ และค้นคลังเจอเอกสารจริงแล้ว  
Quick เป็นผู้ช่วยที่เรียกคลังผ่าน `/mcp` ไม่ใช่ QuickSight และไม่แทนหน้าอนุมัติหรือการส่งออก Word

zip ของสกิล: `app/infra/quick/amazon Quick agents/Skills - TOR/tor-agents-skills-v0.7.1.zip`

### 11.1 สร้าง Connector

1. Amazon Quick ระดับทีม → Connectors → สร้างให้ทีม → เลือก Model Context Protocol (MCP)
2. Endpoint: `https://<โดเมน>/mcp`
3. Header ชื่อ `Authorization` ค่าเท่ากับ `QUICK_MCP_AUTH_VALUE`
4. ทดสอบ `list_rag_groups` แล้ว `retrieve` ด้วยคำถามภาษาไทย, `rag_group=procurement-th`, `top_k` เป็น 3
5. ต้องได้ข้อความจากเอกสารจริงภายใน 60 วินาที
6. ถ้าแก้เครื่องมือบนเซิร์ฟเวอร์แล้ว Quick ไม่เห็นรายการใหม่ ให้สร้าง connector ใหม่ ของเก่าจำชุดเครื่องมือเดิม

Claude Code หรือไคลเอนต์ MCP อื่นใช้ URL และโทเคนชุดเดียวกัน ใช้ได้เฉพาะค้น

ถ้า Quick อยู่นอก VPC และเข้าเครื่องโดยตรงไม่ได้ ให้ใช้การเชื่อมต่อ VPC ของ Quick ตามเอกสาร AWS อย่าเปิดพอร์ตฐานข้อมูลเพื่อแก้ปัญหานี้

### 11.2 นำเข้าสกิลและสร้างตัวแทน

แตก zip แล้วใน Quick: Agents and skills → Skills → Import from file นำเข้า `SKILL.md` ตามลำดับ

| ลำดับ | สกิล | งาน |
|------:|------|-----|
| 1 | `tor-kb-retrieve` | ถามระเบียบหรือมาตรฐานจากคลัง |
| 2 | `tor-draft-intake` | วิเคราะห์เอกสารเข้าจนพร้อมร่าง |
| 3 | `tor-draft-compose` | ร่างหมวด TOR |
| 4 | `tor-review-compliance` | ตรวจ TOR ทั้งฉบับจากคลัง |

ในแต่ละสกิลให้แนบเครื่องมือ `retrieve`, `list_rag_groups`, `ping`, `get_health`  
สร้างตัวแทนโดยคัดลอกคำสั่งจาก `agents/tor-draft-agent.json` หรือ `agents/tor-review-agent.json` แล้วเลือก connector ของโดเมนนี้  
งานร่างหรือตรวจทั้งฉบับใช้โหมดตอบ Smart  
ถ้าไฟล์ JSON มี URL ตัวอย่าง ให้แก้เป็น `https://<โดเมน>/mcp` ก่อนแจกให้ทีม

### 11.3 ผู้ใช้ทำอะไรที่ไหน

| งาน | ที่ทำ |
|-----|--------|
| ถามระเบียบหรือราคากลาง | Quick หรือแชทในเว็บ |
| เริ่มร่างจากเอกสาร | สกิล `tor-draft-intake` |
| ร่างหมวด | สกิล `tor-draft-compose` เป็นภาษาราชการ |
| ตรวจร่าง | สกิล `tor-review-compliance` |
| ส่งออก DOCX หรือ PDF | เว็บแอป ขั้นที่ 4 |
| อนุมัติโครงการ | เว็บแอป |

บอกผู้ใช้ให้ถามทีละประเด็น ถ้าคำถามกว้างจะหมดเวลา 60 วินาที และอย่าให้ `top_k` เกิน 5

---

## 12. เปิดให้เจ้าหน้าที่ใช้

1. สร้างผู้ใช้จริง แล้วเปลี่ยนรหัสหรือปิดบัญชีเดโม
2. โหลดคลังตามข้อ 10 แล้วค้นคำที่อยู่ในไฟล์นั้นให้เจอ
3. ทดด้วยบัญชีเจ้าหน้าที่ ไม่ใช่แค่ health check
   - สร้างโครงการและเลือกหมวดใหญ่ 7 ประเภท
   - วิเคราะห์หนึ่งโครงการ
   - ร่างสั้นหนึ่งหมวดบน Bedrock
   - ถามคลังหนึ่งคำถามที่ต้องมีแหล่งอ้างอิง
   - อัปโหลดไฟล์บนหน้าตรวจ TOR
   - ส่งออก DOCX หรือ PDF หนึ่งไฟล์ เพื่อพิสูจน์ว่าเขียน S3 ได้
4. บันทึก URL วิธีตั้งรหัสใหม่ และคนที่รับแจ้งเตือนงบ Bedrock

ผู้ใช้ทั่วไปไม่ต้องมีบัญชี AWS

---

## 13. Deploy อัตโนมัติ

อย่าใช้เวิร์กโฟลว์ ECS ใน `app/infra/aws/ci/` เครื่องนี้ไม่มี Fargate และไม่มี ECR ในสแตกหลัก  
วิธีที่เข้ากับ EC2 `t3.medium` คือให้ GitHub กดสั่ง แล้ว AWS Systems Manager ส่งคำสั่งเข้าเครื่องเดิม ให้ดึง commit แล้ว `docker compose up --build`  
คลังบน S3 ไม่ถูกอัปโหลดหรือฝังใหม่ในขั้นนี้ ดังนั้นไม่เกิดค่า Bedrock จากการ deploy

```text
คนกด Run workflow ใน GitHub
        │  ไม่มี access key — ใช้ OIDC
        ▼
GitHub Actions  →  SSM SendCommand  →  EC2 t3.medium
                                        git checkout <SHA>
                                        docker compose up -d --build
                                        ตรวจ /api/v1/health
                                        ถ้าไม่ผ่าน ให้ย้อน commit เดิม
```

สิ่งที่สคริปต์ไม่ทำ: ไม่แก้ `.env` ไม่หมุนโทเคน ไม่ `ingest` คลัง ไม่เปิดพอร์ต SSH

### 13.1 ทำครั้งเดียวบนเครื่อง

`t3.medium` มีแรม 4 GB การ build หน้า Next.js มักไม่พอ ใส่ swap 4 GB ก่อนเปิด auto ไม่เช่นนั้นเครื่องจะฆ่าโปรเซสกลางคัน

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

รีโปต้องเป็น git checkout ที่ดึงจากต้นทางได้ ไม่ใช่โฟลเดอร์ที่แตกจาก zip  
ถ้ารีโปเป็นส่วนตัว ให้ใส่ deploy key แบบอ่านอย่างเดียวบนเครื่อง อย่าใส่รหัสส่วนตัวลงสคริปต์

สร้างไฟล์ตั้งค่าที่ไม่อยู่ใน Git:

```bash
sudo mkdir -p /etc/tor-pn
sudo tee /etc/tor-pn/deploy.env >/dev/null <<'EOF'
PN_APP_ROOT=/home/ec2-user/tor-app
PN_APP_USER=ec2-user
EOF
sudo chmod 644 /etc/tor-pn/deploy.env
```

บน Ubuntu เปลี่ยนผู้ใช้เป็น `ubuntu` และเส้นทางเป็น `/home/ubuntu/tor-app` ให้ตรงกับที่ clone ไว้

วางคำสั่งที่ SSM จะเรียก คำสั่งนี้รันเป็น root แล้วสลับไปผู้ใช้เจ้าของรีโป:

```bash
sudo tee /usr/local/bin/tor-pn-deploy >/dev/null <<'EOF'
#!/bin/bash
set -euo pipefail
set -a
# shellcheck disable=SC1091
source /etc/tor-pn/deploy.env
set +a
exec sudo -u "$PN_APP_USER" -H bash "$PN_APP_ROOT/app/infra/pn-ec2/scripts/deploy.sh" "$@"
EOF
sudo chmod 755 /usr/local/bin/tor-pn-deploy
```

ทดบนเครื่องก่อนผูก GitHub ใช้ SHA จริงจาก `git rev-parse HEAD`:

```bash
sudo /usr/local/bin/tor-pn-deploy
```

สคริปต์อยู่ที่ [`app/infra/pn-ec2/scripts/deploy.sh`](app/infra/pn-ec2/scripts/deploy.sh)  
ถ้า health ไม่ผ่าน มันจะ checkout commit เดิมแล้ว build กลับให้เอง  
เว็บจะดับช่วง build ประมาณหลายนาทีบนเครื่องนี้ อย่ากด deploy ขณะมีคนร่างค้าง

### 13.2 ทำครั้งเดียวบน AWS และ GitHub

1. เครื่องต้องออนไลน์ใน Systems Manager แล้ว (มี `AmazonSSMManagedInstanceCore` ตามข้อ 5.5)
2. สร้าง IAM role สำหรับ GitHub ไม่ใช่ role ของเครื่อง
   - เปิด OIDC provider `token.actions.githubusercontent.com` ถ้าบัญชียังไม่มี ผู้ชม (audience) คือ `sts.amazonaws.com`
   - Trust ให้เฉพาะรีโปและสาขา `main` เช่น subject `repo:หน่วยงาน/ชื่อรีโป:ref:refs/heads/main`
   - แนบนโยบายจาก [`app/infra/pn-ec2/iam/github-ssm-deploy.json`](app/infra/pn-ec2/iam/github-ssm-deploy.json) หลังแทน `ACCOUNT_ID` และ `INSTANCE_ID`  
     role นี้สั่งได้เฉพาะเครื่องนี้ และสั่งได้เฉพาะเอกสาร `AWS-RunShellScript`
3. ใน GitHub → Settings → Secrets → Actions ใส่
   - `AWS_DEPLOY_ROLE_ARN` เป็น ARN ของ role ข้อ 2
   - `PN_EC2_INSTANCE_ID` เป็นรหัส instance ของ `t3.medium`
4. คัดลอก [`app/infra/pn-ec2/ci/github-ec2-deploy.yml.example`](app/infra/pn-ec2/ci/github-ec2-deploy.yml.example) ไปที่ `.github/workflows/ec2-deploy.yml`  
   โฟลเดอร์ `.github/` ไม่ถูก commit ในรีโปนี้ จึงต้องวางบนเครื่องที่เปิด Actions
5. Actions → Deploy TOR to EC2 → Run workflow

ยังไม่เปิดให้ push แล้ว deploy เอง จนกว่าจะยอมรับได้ว่าการรีสตาร์ททิ้งงานร่างที่ค้างบนหน้าจอ  
เมื่อพร้อม ค่อยเพิ่ม `push` ไปสาขา `main` ในไฟล์ workflow และจำกัด path เป็น `app/frontend/**`, `app/backend/**`, `app/infra/pn-ec2/**`, `app/infra/quick/**`

### 13.3 สิ่งที่ยังทำมือ

| งาน | เหตุผลที่ไม่ใส่ใน auto |
|-----|------------------------|
| แก้ `.env` ใบรับรอง โทเคน Quick | สคริปต์ห้ามแตะความลับ |
| อัปโหลดหรือ ingest คลัง | มีค่า Bedrock และไม่ใช่การอัปเดตแอป |
| แพตช์ระบบปฏิบัติการ | ต้องนัดดับเครื่อง |
| กู้ข้อมูล Postgres | ใช้ snapshot ดิสก์ ไม่ใช่ git |

ถ้า build ยังถูกฆ่าทั้งที่มี swap 4 GB ขั้นถัดไปคือให้ GitHub สร้างอิมเมจแล้วให้เครื่องดึงจาก ECR วิธีนั้นเพิ่มบริการอีกตัว และยังไม่ใช่สแตกของคู่มือนี้

---

## 14. งานหลังเปิดใช้

### เพิ่มเอกสาร

อัปโหลดด้วย `ingest=true` หรือวางไฟล์ที่ `rags/<กลุ่ม>/sources/` แล้วเรียก `/api/v1/pn/kb/ingest`  
จากนั้นค้นคำที่อยู่ในไฟล์ใหม่  
เปลี่ยนโมเดลฝังหรือมิติเวกเตอร์ คือสร้าง index ใหม่แล้วฝังทั้งคลังใหม่ ห้ามปนของเก่า

### อัปเดตแอป

ทางที่ควรใช้หลังเปิด auto แล้วคือกด Run workflow ตามข้อ 13  
บนเครื่องเองใช้สคริปต์เดียวกันได้ ไม่ต้องพิมพ์ `git pull` เอง:

```bash
sudo /usr/local/bin/tor-pn-deploy
```

สคริปต์ไม่แก้ `.env` และไม่ ingest คลัง  
อย่า deploy ขณะมีคนร่างค้างบนหน้าจอ งานที่ยังอยู่ในโปรเซสจะหายช่วงรีสตาร์ท

### หมุนโทเคนของ Quick

เปลี่ยน `QUICK_MCP_AUTH_VALUE` แล้วรัน `docker compose ... up -d` จากนั้นแก้ค่าใน Connector ให้ตรงกัน  
การเปลี่ยน `JWT_SECRET` ทำให้ทุกคนต้องล็อกอินใหม่ ทำนอกเวลาทำการ

### สำรอง

- Snapshot ดิสก์ EC2 เป็นประจำ เพราะผู้ใช้และโครงการอยู่ใน Postgres บนเครื่อง
- เปิด versioning ของบัคเก็ต S3
- เวกเตอร์อยู่ที่ S3 Vectors ไม่ได้อยู่ใน snapshot ของดิสก์ ถ้าสร้าง index ใหม่ต้องฝังใหม่จากไฟล์บน S3
- ดู Budget เป็นระยะ โดยเฉพาะ Bedrock

### แพตช์เครื่อง

`t3.medium` เป็นเครื่องที่ต้องดูแลระบบปฏิบัติการเอง อัปเดตแพ็กเกจความปลอดภัยเป็นระยะ และรีสตาร์ทในหน้าต่างที่นัดไว้  
ก่อนรีสตาร์ท บอกผู้ใช้ เพราะเว็บจะดับช่วงเครื่องปิด

---

## 15. เกณฑ์ผ่านก่อนเปิดใช้จริง

- [ ] เครื่องเป็น **t3.medium** ใน `ap-southeast-1` มี Elastic IP และ DNS ชี้มาแล้ว
- [ ] `.env` ไม่มี `changeme` และไม่มี access key
- [ ] instance profile เรียก `aws sts get-caller-identity` และ `aws s3 ls` ของบัคเก็ตได้
- [ ] บัคเก็ตไฟล์ปิดการเข้าถึงสาธารณะ แยกจาก vector bucket และ index เป็นมิติ 1024
- [ ] Bedrock แชทและ `cohere.embed-v4:0` เป็น Access granted
- [ ] Security Group ไม่เปิดพอร์ตฐานข้อมูล และ 443 จำกัดสำนักงานหรือ VPN
- [ ] HTTPS ใช้ได้ ใบรับรองไม่หมดใน 30 วัน คุกกี้เป็น Secure
- [ ] `https://<โดเมน>/api/v1/health` ผ่าน
- [ ] ล็อกอินได้ และหน้าสร้างโครงการมี 7 หมวดใหญ่
- [ ] อัปโหลด `ingest=true` แล้วค้นเจอข้อความภาษาไทยพร้อมชื่อไฟล์
- [ ] Quick เรียก `/mcp` ได้โดยไม่ขึ้น 401 และไม่เกิน 60 วินาที ถ้าเปิด Quick
- [ ] ส่งออกไฟล์แล้วเห็นอ็อบเจกต์บน S3
- [ ] ปิดหรือเปลี่ยนรหัสบัญชีเดโมแล้ว
- [ ] Budget เตือน EC2, S3 และ Bedrock แล้ว มีคนรับการแจ้งเตือน
- [ ] มี snapshot ดิสก์ และเปิด versioning ของบัคเก็ต

---

## 16. อาการที่พบบ่อย

| อาการ | สาเหตุที่พบบ่อย | ทำอะไร |
|--------|------------------|--------|
| build ไม่เจอ Dockerfile ของเว็บ | โคลนไม่ครบ หรือไป build โฟลเดอร์ `frontend/` ที่ราก | ตรวจว่ามี `app/frontend/Dockerfile` |
| Bedrock ปฏิเสธชื่อโมเดล | ยังไม่เปิดสิทธิ์ หรือ model id ไม่ตรง region | เปิด Model access แล้วเทียบ `BEDROCK_MODEL_ID` |
| อัปโหลดได้แต่ค้นไม่เจอ | มีไฟล์บน S3 แต่ยังไม่ฝัง | เรียก ingest หรืออัปโหลดด้วย `ingest=true` |
| ใส่เวกเตอร์ไม่สำเร็จ | มิติ index ไม่ใช่ 1024 หรือชื่อ index ไม่ตรง yaml | สร้าง index ให้ตรงแล้วฝังใหม่ |
| `s3 ls` ถูกปฏิเสธ | นโยบายยังเป็นชื่อตัวอย่าง หรือไม่ได้แนบ role | แก้ role แล้วตรวจ `aws sts` บนเครื่อง |
| Quick ขึ้น 401 | โทเคนไม่ตรง หรือไม่ได้ส่ง header `Authorization` | เทียบค่าใน `.env` กับ Connector แล้วรีสตาร์ท compose |
| Quick หมดเวลา | ถามกว้าง หรือ Bedrock ช้า | ลด `top_k` แล้วถามแคบลง |
| ได้ข้อความว่างหรือข้อความตัวอย่าง | กลุ่มเอกสารผิด หรือยังไม่ ingest | ตรวจ `rag_group` และผลค้นข้อ 10.4 |
| เว็บขึ้นแต่ขึ้น CORS | `CORS_ORIGINS` ไม่ตรง `https://` และโดเมนที่เปิดจริง | แก้แล้วรีสตาร์ท backend |
| ส่งออกไฟล์ไม่ได้ | role ไม่มีสิทธิ์เขียนบัคเก็ต หรือ `MINIO_USE_IAM` ไม่ได้เปิด | ตรวจนโยบาย S3 และค่า MinIO ใน `.env` |
| health ของ API ไม่ขึ้น | Postgres ยังไม่พร้อม หรือรหัสไม่ตรง volume เก่า | ดูล็อก `backend` และ `postgres` |
| Deploy จาก GitHub ไม่ถึงเครื่อง | instance ไม่ออนไลน์ใน SSM หรือ role สั่งผิด instance | ดู Fleet Manager แล้วเทียบ `PN_EC2_INSTANCE_ID` |
| Build ตายกลางคัน | แรม 4 GB ไม่พอ | ตรวจว่าเปิด swap 4 GB แล้ว ดู `dmesg` ว่ามี OOM |
| ล็อกอินได้บน HTTP แล้วหายบน HTTPS | ยังไม่ตั้ง `COOKIE_SECURE=true` หรือชื่อในใบรับรองไม่ตรงโดเมน | ออกใบให้ตรงโดเมนแล้วบังคับ HTTPS |

---

## 17. ไฟล์ในรีโปที่ใช้คู่กับคู่มือนี้

| ไฟล์ | ใช้เมื่อ |
|------|----------|
| `app/infra/pn-ec2/.env.example` | รายการตัวแปรครบ |
| `app/infra/pn-ec2/docker-compose.pn.yml` | บริการที่เครื่องรัน |
| `app/infra/pn-ec2/rag-groups.yaml` | ชื่อกลุ่มและชื่อ index |
| `app/infra/pn-ec2/iam/ec2-instance-profile.json` | นโยบายของเครื่อง |
| `app/infra/pn-ec2/nginx/pn.conf.example` | แบบพร็อกซี |
| `app/infra/quick/คู่มือติดตั้ง-AWS-cloud.md` | รายละเอียดสกิลของ Quick เพิ่มเติม |
| `app/infra/pn-ec2/scripts/deploy.sh` | อัปเดตแอปบนเครื่อง โดยไม่แตะ `.env` |
| `app/infra/pn-ec2/ci/github-ec2-deploy.yml.example` | ปุ่ม deploy จาก GitHub ผ่าน SSM |
| `app/infra/pn-ec2/iam/github-ssm-deploy.json` | สิทธิ์ของ role ที่ GitHub ใช้สั่งเครื่อง |
| `Discussions/36-AWS-PN-USER-SETUP-AND-RUNBOOK.md` | บันทึกงานมือฉบับเดิม |
