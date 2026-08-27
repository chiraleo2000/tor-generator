# AWS infrastructure templates (production path)

เอกสารหลัก: [Discussions/24–27](../../../Discussions/24-AWS_CLOUD_OVERVIEW.md)

โฟลเดอร์นี้เป็น **โครงพร้อมใส่บัญชี** ไม่ใช่สแตกที่ apply แล้วเสร็จเอง

| ไฟล์ | ใช้ |
|------|-----|
| `env.cloud.example` | ค่า ECS / Secrets (คัดลอก ไม่ commit รหัส) |
| `iam/*.json` | นโยบาย execution / task / GitHub OIDC |
| `ecs/*.json` | ตัวอย่าง task definition (ชื่อ role ตรง Terraform `tor-prod-ecs-*`) |
| `terraform/` | รอบ 1: VPC/ECR/S3/IAM — รอบ 2–3: RDS/Redis/ECS เมื่อเปิดแฟล็กใน tfvars |
| `scripts/pull-kb-from-s3.sh` | ดึงคลังจาก S3 แล้ว seed (`KB_SOURCES_ROOT`) |
| `ci/github-ecs-deploy.yml.example` | คัดลอกไป `.github/workflows/` เมื่อพร้อม OIDC |

อย่ารัน `terraform apply` ในบัญชีจริงโดยไม่ `plan` และไม่ตั้งงบเตือน Bedrock
