# Terraform — AWS-only TOR app (`ap-southeast-1`)

อ่าน [Discussions/26-AWS_INSTALL_AND_WIRING.md](../../../../Discussions/26-AWS_INSTALL_AND_WIRING.md) ก่อน apply  
อย่า `apply` ในบัญชีจริงโดยไม่ `plan` และไม่ตั้ง AWS Budget (โดยเฉพาะ Bedrock)

## สองรอบ apply (กันคิดเงินโดยไม่ตั้งใจ)

| รอบ | `enable_managed_data` | `enable_ecs` | ได้ |
|-----|------------------------|--------------|-----|
| 1 | `false` | `false` | VPC, NAT, S3, ECR, KMS, IAM, Secrets **เปล่า**, log group, security group |
| 2 | `true` | `false` | + RDS PostgreSQL 16 Multi-AZ, ElastiCache Redis (TLS+AUTH), เติม Secrets |
| 3 | `true` | `true` | + ECS Fargate, ALB HTTPS, Cloud Map `backend.tor.local` — ต้องมี `certificate_arn` |

ค่าเริ่มต้นใน `terraform.tfvars.example` คือรอบ 1

```bash
cp terraform.tfvars.example terraform.tfvars
# ตั้ง bucket_prefix ให้โกลบอล (เช่น <accountid>-tor)
terraform init
terraform plan
terraform apply
```

หลังรอบ 2: เปิด ECS Exec / bastion แล้ว `CREATE EXTENSION vector;` + Alembic ตามเอกสาร 26 ข้อ D  
หลังรอบ 3: ดันอิมเมจไป ECR แท็ก `prod` ก่อน service จะดึงได้

## ตัวแปรสำคัญ

- `bucket_prefix` — ชื่อบัคเก็ต S3 ต้องไม่ซ้ำทั่วโลก
- `backend_desired_count` — คง `1` จนกว่าคิวร่างจะออกจากหน่วยความจำโปรเซส (เอกสาร 27)
- `app_domain` — ใส่โดเมนจริงใน `CORS_ORIGINS`
- `certificate_arn` — ใบ ACM **ใน region เดียวกับ ALB** (ไม่ใช่ใบ CloudFront ที่ต้องออกที่ `us-east-1`)

State: อย่า commit `terraform.tfvars` / `*.tfstate` (มี `.gitignore` ในโฟลเดอร์นี้)  
แนะนำ backend S3 + DynamoDB lock เมื่อหน่วยงานพร้อม — ยังไม่ใส่ใน scaffold นี้
