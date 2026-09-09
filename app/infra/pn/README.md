# PN package moved

ใช้แพ็กเกจ deploy หลักที่ **[../pn-ec2/](../pn-ec2/)**  

- คัดลอก [`../pn-ec2/.env.example`](../pn-ec2/.env.example) → `.env` แล้วแก้ค่า  
- Compose / IAM / nginx / สคริปต์ อยู่ที่นั่น  
- คู่มือขึ้น AWS: [Discussions/35-AWS-PN-DEV-AND-DEPLOY.md](../../../Discussions/35-AWS-PN-DEV-AND-DEPLOY.md)

ไฟล์ `rag-groups.yaml` ชุดเก่าถ้ายังถูกอ้างอิง ให้ชี้ไป `pn-ec2/rag-groups.yaml` หรือใช้ของใน `pn-ec2` โดยตรง
