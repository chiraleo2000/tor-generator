# AWS infrastructure templates (production path)

เอกสารหลัก: [Discussions/24–27](../../../Discussions/24-AWS_CLOUD_OVERVIEW.md) · TBD Cloud ล้วน + RAG สองแหล่ง: [29](../../../Discussions/29-TBD-AWS-CLOUD-ONLY.md)  
`DEPLOYMENT_MODE=cloud` เท่านั้น — ห้าม hybrid LLM ใน task นี้

โฟลเดอร์นี้เป็น **โครงพร้อมใส่บัญชี** ไม่ใช่สแตกที่ apply แล้วเสร็จเอง

| ไฟล์ | ใช้ |
|------|-----|
| `env.cloud.example` | ค่า ECS / Secrets (คัดลอก ไม่ commit รหัส) |
| `iam/*.json` | นโยบาย execution / task / GitHub OIDC |
| `ecs/*.json` | ตัวอย่าง task definition (ชื่อ role ตรง Terraform `tor-prod-ecs-*`) |
| `terraform/` | รอบ 1: VPC/ECR/S3/IAM — รอบ 2–3: RDS/Redis/ECS เมื่อเปิดแฟล็กใน tfvars |
| `scripts/pull-kb-from-s3.sh` | ดึงคลังจาก S3 แล้ว seed (`KB_SOURCES_ROOT`) |
| `ci/github-ecs-deploy.yml.example` | แบบ push-to-main (เปิดเมื่อ OIDC พร้อม) |
| `app/infra/aws/ci/ecs-deploy.yml` | skeleton `workflow_dispatch` (ก๊อปไป `.github/workflows/` บนเครื่อง — `.github/` ไม่ขึ้น Git) |
| `ecs/*.yml` + `config/cloud-app.yaml` | ค่า service/task/แอปแบบ YAML |
| `config/services.yaml` | แคตตาล็อกบริการ AWS ↔ ไฟล์โครง (skeleton / gated / TBD) |
| `compose/docker-compose.cloud.yml` | ทดลองป้าย env คลาวด์บนเครื่อง |
| `../mcp/` | โครง MCP RAG (`rag-sources.yaml` สำหรับ bind-mount, `servers.example.json` สำหรับ ECS JSON) |

อย่ารัน `terraform apply` ในบัญชีจริงโดยไม่ `plan` และไม่ตั้งงบเตือน Bedrock
