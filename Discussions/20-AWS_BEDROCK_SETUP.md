# Setup บน Amazon (AWS) — Bedrock บน EC2 + Docker Compose

คู่มือนี้เป็น **ทางลัด**: รันแอปด้วย Compose บน EC2 (หรือเครื่องใน VPC) แล้วชี้ LLM/embeddings ไป **Amazon Bedrock**  
**ไม่ใช่** เส้นทาง production ล้วนบนบริการจัดการของ AWS (ECS/RDS/S3/ElastiCache)

สำหรับ **AWS-only ไม่มี hybrid** (เป้าหมายหน่วยงานที่ deploy บนคลาวด์อย่างเดียว) ใช้ชุด:

| เอกสาร | เนื้อหา |
|--------|---------|
| [24-AWS_CLOUD_OVERVIEW.md](24-AWS_CLOUD_OVERVIEW.md) | เป้าหมายและเฟส A–G |
| [25-AWS_SERVICE_CATALOG.md](25-AWS_SERVICE_CATALOG.md) | จับคู่ Docker → บริการ AWS |
| [26-AWS_INSTALL_AND_WIRING.md](26-AWS_INSTALL_AND_WIRING.md) | ติดตั้ง ตั้งค่า เชื่อมโยงทีละขั้น |
| [27-AWS_CODE_AND_CUTOVER.md](27-AWS_CODE_AND_CUTOVER.md) | โค้ดที่ปรับแล้วและงานที่เหลือ |
| โครงไฟล์ | `app/infra/aws/` (Terraform, IAM, ECS, `.env` คลาวด์) |

ตัวเลือกอื่น (LM Studio, Ollama, llama.cpp, SGLang, Claude/OpenAI/Gemini/Azure) **ยังสลับได้จาก Admin** บนเส้นทางนี้ — บนเส้น 24–27 ห้ามชี้ GPU ในสำนักงาน

ดูการติดตั้ง Compose ทั่วไปที่ [`14-INSTALLATION.md`](14-INSTALLATION.md)

---

## 1. สิ่งที่ได้บน AWS

| ชิ้น | แนะนำบน Amazon |
|------|----------------|
| App (frontend/backend + postgres/redis/minio/mongo/neo4j) | EC2 + Docker Compose (หรือ ECS ทีหลัง) |
| LLM | **Amazon Bedrock** Converse API |
| Embeddings | Bedrock Titan **หรือ** local ใน VPC (`EMBEDDING_PROVIDER=local`) |
| Custom RAG | URL ใน VPC / บริการภายนอก (ดู Admin → Custom RAG) |

ไม่ต้องรัน GPU inference เองเมื่อใช้ Bedrock

---

## 2. บัญชี AWS และ Bedrock

1. ใช้หรือสร้าง AWS account
2. เลือก region ที่รองรับโมเดลที่ต้องการ — ค่าเริ่มต้นแอป: **`ap-southeast-1`**
3. เปิด **Bedrock → Model access** สำหรับโมเดลแชท (เช่น Claude) และ Titan Embeddings (ถ้าใช้ `EMBEDDING_PROVIDER=bedrock`)
4. สร้าง IAM user หรือ **instance/task role** ด้วยสิทธิ์ขั้นต่ำ เช่น:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:Converse",
        "bedrock:ConverseStream"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["sts:GetCallerIdentity"],
      "Resource": "*"
    }
  ]
}
```

(จำกัด `Resource` เป็น ARN โมเดลใน region จริงเมื่อ harden production)

### Credentials

| สภาพแวดล้อม | วิธี |
|-------------|------|
| Dev บนเครื่อง | ใส่ `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` ใน `.env` หรือ Admin → การตั้งค่า AI |
| Prod บน EC2/ECS | ผูก **IAM role** กับ instance/task — **เว้นว่าง** key ใน env ให้ boto3 ใช้ default chain |

---

## 3. ค่า `.env` แนะนำ (production Amazon)

```env
COMPOSE_PROJECT_NAME=tor-app
DEPLOYMENT_MODE=cloud
LLM_PROVIDER=bedrock
EMBEDDING_PROVIDER=bedrock
BEDROCK_REGION=ap-southeast-1
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```

**Hybrid ใน VPC:** แชท Bedrock + ฝังเวกเตอร์ในเครื่อง

```env
LLM_PROVIDER=bedrock
EMBEDDING_PROVIDER=local
LOCAL_EMBEDDING_SERVER=lm_studio
```

ถ้าเปลี่ยน embedding provider/model ต้องรัน `python -m app.seed_raw_docs` ใหม่ (`reingest_required`)

---

## 4. รันแอปบน EC2 (Compose)

1. EC2 ใน VPC ที่ออกเน็ตได้ถึง Bedrock (หรือ VPC endpoint ของ Bedrock)
2. ติดตั้ง Docker Engine + Compose
3. Clone รีโป, `cp .env.example .env`, ใส่ค่าด้านบน + รหัส DB/JWT
4. จากรากรีโป:

```bash
docker compose -p tor-app --env-file .env up -d --build
```

5. เปิด security group ให้พอร์ต frontend (เช่น 3000) ตามนโยบายหน่วยงาน
6. `GET http://<host>:4000/health` ต้อง healthy

> ECS/Fargate ทั้งชุดและ Terraform อยู่นอกขอบเขตรอบนี้ — ใช้ EC2+Compose เป็นจุดเริ่ม

---

## 5. Checklist หลัง setup

- [ ] Model access ใน Bedrock เปิดแล้วใน region ที่ใช้
- [ ] IAM role หรือ access key ใช้งานได้ (`sts:GetCallerIdentity`)
- [ ] Admin → โมเดลแชท = **Amazon Bedrock (แนะนำ production)** → ทดสอบการเชื่อมต่อผ่าน
- [ ] แชทหรือร่างหนึ่งรอบสำเร็จ
- [ ] สลับกลับ LM Studio (หรือ vendor อื่น) ได้จาก Admin เพื่อยืนยันว่าตัวเลือกไม่หาย

---

## 6. Concurrency / คิว

บน Amazon (Bedrock) แอปยังมี Redis admission + rate limit เพื่อกันงบและ timeout เมื่อหลายผู้ใช้พร้อมกัน  
ค่า `LLM_MAX_CONCURRENT` แนะนำสูงกว่าโหมด on-prem (เช่น 8–16) — ดู `.env.example`

---

## 7. สลับกลับ on-prem

Admin → การตั้งค่า AI → เลือก LM Studio / Ollama / llama.cpp / SGLang  
หรือตั้งใน `.env`: `LLM_PROVIDER=lm_studio` แล้วบันทึกใหม่จาก Admin (overlay ใน Postgres มีผลทันที)
