# 31 — MCP RAG + Custom RAG บน Amazon (cloud quickstart)

เอกสารนี้พาค่า MCP / Custom RAG จากเครื่องขึ้น **AWS cloud install** ตาม [24](24-AWS_CLOUD_OVERVIEW.md) และ [`app/infra/aws/env.cloud.example`](../app/infra/aws/env.cloud.example)  
ไม่ใช่ QuickSight และไม่ใช่ `DEPLOYMENT_MODE=hybrid`

สเปก: [`.kiro/specs/mcp-rag-config-and-deploy/`](../.kiro/specs/mcp-rag-config-and-deploy/requirements.md)

## รูปสแตก

| ชิ้น | ค่า |
|------|-----|
| โหมด / LLM | `DEPLOYMENT_MODE=cloud`, `LLM_PROVIDER=bedrock`, `EMBEDDING_PROVIDER=bedrock` |
| วัตถุ | S3 (`MINIO_USE_IAM=true`, `MINIO_SECURE=true`, `MINIO_REGION`) |
| Redis | ElastiCache + `REDIS_TLS=true` |
| Bedrock | ECS **task IAM role** (เว้น `AWS_ACCESS_KEY_ID` ว่าง) หรือ `AWS_BEARER_TOKEN_BEDROCK` ใน Secrets |
| MCP | `MCP_RAG_SERVERS_JSON` จาก Secrets Manager เท่านั้น — **ห้าม** `MCP_RAG_CONFIG_PATH` |
| Auth MCP | `MCP_RAG_AUTH_VALUE` จาก Secrets เมื่อพาร์ทเนอร์ยืนยันแล้ว (ว่าง = ไม่ส่ง header) |
| Custom RAG | `CUSTOM_RAG_*` จาก Secrets; URL ต้องอยู่ใน VPC |
| Fail-open | เซิร์ฟเวอร์ MCP ล่มแล้วยังตอบจาก pgvector / Custom RAG |
| Secret หาย | Terraform สร้าง secret `tor/<env>/mcp` ด้วย `{"servers":[]}` — ทาสก์ขึ้นได้แม้ยังไม่มี URL จริง |

## Terraform / ECS

| รายการ | ที่อยู่ |
|--------|---------|
| Secret MCP | `aws_secretsmanager_secret.mcp` → `${project}/${environment}/mcp` |
| คีย์ JSON | `MCP_RAG_SERVERS_JSON`, `MCP_RAG_AUTH_VALUE` (เวอร์ชันเริ่มต้นเป็นเซิร์ฟเวอร์ว่าง) |
| Task env | `MCP_RAG_ENABLED=false` จนกว่าจะมี endpoint ใน VPC |
| Egress | SG `ecs-be` ออก NAT ทั้งหมด; จำกัดเป็น URL:port ของพาร์ทเนอร์เมื่อรู้แล้ว |
| ห้าม | mount `rag-sources.yaml` หรือตั้ง `MCP_RAG_CONFIG_PATH` บน Fargate |

เปิด MCP บน UAT: อัปเดต secret (Terraform `ignore_changes` บน `secret_string`) แล้วตั้ง `MCP_RAG_ENABLED=true` ใน task — **อย่า commit URL จริง**

## ลำดับขึ้น UAT

1. Health ของ backend/frontend บน HTTPS
2. Seed คลัง Titan (`seed_kb` / `seed_raw_docs`) ให้ RAG A มีเอกสาร
3. ใส่ URL จริงใน secret `tor/<env>/mcp` จาก [`servers.example.json`](../app/infra/mcp/servers.example.json)
4. เปิด egress จาก ECS ไปพอร์ต MCP ของพาร์ทเนอร์ (NAT + SG)
5. ตั้ง `MCP_RAG_ENABLED=true` แล้ว inject `MCP_RAG_SERVERS_JSON`
6. (ถ้าใช้ PageIndex) ตั้ง `CUSTOM_RAG_ENABLED=true` และ `CUSTOM_RAG_BASE_URL` ใน VPC
7. รันเกต UI: แชทต้องมีชิป `mcp:` และ/หรือ `custom_rag:` และยังตอบได้เมื่อปิด MCP

## ทางลัด EC2 + Compose (ไม่แทน ECS)

[20](20-AWS_BEDROCK_SETUP.md) ใช้ทดสอบ Bedrock + VPC ก่อน Fargate:

- เครื่อง EC2 ใน private subnet, IAM instance profile มี `bedrock:InvokeModel*`
- `docker compose -p tor-app --env-file .env up -d` ตามรูปร่างเดียวกับเครื่องพัฒนา
- MCP: ใช้ `MCP_RAG_SERVERS_JSON` ชี้ URL ใน VPC (หรือ stub) — อย่าเปิด YAML path บน production
- Custom RAG: URL เป็นชื่อโฮสต์ใน VPC ไม่ใช่ `pageindex` ของ Compose บนโน้ตบุ๊ก

ทางลัดนี้ไม่แทน RDS / ElastiCache / ECS ในเอกสาร 24–27

## Seed คลังบนเครื่อง (Windows)

Bind-mount ชื่อโฟลเดอร์ไทยมักอ่าน `/knowledge-base` ไม่ได้ (OSError 5) — คัดลอกไฟล์ไป `/tmp/kb` ในคอนเทนเนอร์แล้ว `KNOWLEDGE_BASE_DIR=/tmp/kb python -m app.seed_kb`

ถ้า Titan embeddings คืน `ValidationException: model identifier is invalid` ให้ตรวจ `BEDROCK_EMBEDDING_MODEL_ID` กับสิทธิ์ของ API key/ภูมิภาค — การค้นหา hybrid ยัง fail-open ไป MCP / Custom RAG ได้

## Fail-open เมื่อ secret ว่าง

ถ้า `MCP_RAG_SERVERS_JSON` เป็น `{"servers":[]}` หรือ `MCP_RAG_ENABLED=false` แอปยังขึ้น คลังท้องถิ่นตอบได้ และไม่พิมพ์ค่า secret ในล็อก
