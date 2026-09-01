# Discussions — design notes

Architecture, API, UX, and product write-ups. **Not imported** by Next.js or FastAPI.

Help text in the running app is under `/help` (`app/frontend`). Operator/install guides for Docker + LM Studio are `13`–`23`; AWS Cloud ล้วน is `24`–`27` plus `28` (เกต) and `29` (TBD). Files `01`–`12` are earlier design notes.

Clickable UX/UI demo: **https://chiraleo2000.github.io/tor-generator/** (`index.html` at repo root, branch `gh-pages`). `06-UXUI-Mockup.html` is the older PoC mock.

เอกสารชุดปัจจุบันของสแตกที่รันด้วย Docker + LM Studio Gemma + Mongo + Neo4j คือ **13–23**. เส้นทางหลักบน UI คือพื้นที่ทำงาน **5 Phase** + เมนูถาม-ตอบ `/chat` / ฐานความรู้ / ตรวจสอบ:

คำอธิบายเวิร์กโฟลว์สามบริการหลัก (ภาษาไทย ตรวจจากโค้ดจริง **26 ส.ค. 2026 รอบบ่าย**) อยู่ที่ **21–23** ใช้ชุดนี้เมื่อขัดกับบันทึกเก่าใน `15`/`19` (เช่น วิเคราะห์ขั้นที่ ๐ ไม่ดึงกฎหมายอัตโนมัติแล้ว และเกต HITL บนปุ่มไปทบทวนไม่มีแล้ว)

**Production บน AWS ล้วน (ไม่มี hybrid LLM):** ชุด **24–27** + **29 (TBD)** + โครง `app/infra/aws/` — อย่าใช้เอกสาร 20 เป็นคู่มือ ECS/RDS  
RAG **อนุญาตสองแหล่งข้อมูล** (คลังกลาง + ของฉัน/ระบบอื่น) โดยโมเดลยังเป็น Bedrock — ดู [29](29-TBD-AWS-CLOUD-ONLY.md)  
หลักฐานตรวจ Local LLM ล่าสุด (31 ส.ค. 2026): [28](28-VERIFICATION-AND-MIGRATION.md) · แอปปัจจุบัน **v0.2.9**

| File | Topic |
|------|--------|
| `13-USER_GUIDELINE.md` | คู่มือผู้ใช้ทีละขั้นพร้อมภาพ |
| `14-INSTALLATION.md` | ติดตั้งและรัน |
| `15-APPLICATION_DESCRIPTION.md` | คำอธิบายแอป |
| `16-BACKEND_ARCHITECTURE.md` | สถาปัตยกรรม backend |
| `17-FRONTEND_ARCHITECTURE.md` | สถาปัตยกรรม frontend |
| `18-TEST_EVIDENCE.md` | หลักฐานเทสต์รอบ ส.ค. 2026 (baseline) — รอบตรวจรวมล่าสุดอยู่ที่ **28** |
| `19-APPLICATION_OPERATING_REPORT.md` | รายงานการทำงานครบ frontend/backend/workflows/tools + ภาพ unit tests (24 ส.ค. 2026 อัปเดตเส้นทาง 5 Phase) |
| `19-APPLICATION_OPERATING_REPORT.docx` | ฉบับ Word (TH Sarabun New, ตาราง, ภาพจอ, ไดอะแกรม) |
| `19-APPLICATION_OPERATING_REPORT.pdf` | ฉบับ PDF ส่งออกจาก Word |
| `19-APPLICATION_OPERATING_REPORT.pptx` | สไลด์นำเสนอ (สร้างจาก `_build_report_exports.py`) |
| `20-AWS_BEDROCK_SETUP.md` | ทางลัด **EC2 + Compose + Bedrock** (ไม่ใช่ ECS/RDS ล้วน) |
| `21-WORKFLOW_DRAFT_TOR.md` | เวิร์กโฟลว์ **ร่าง TOR** (ห้าขั้น จากโค้ด 26 ส.ค. 2026 — ไม่มีเกต HITL บนจอ) |
| `22-WORKFLOW_REVIEW_TOR.md` | เวิร์กโฟลว์ **ตรวจสอบ TOR** (หน้าล้วน `/review` + ขั้นที่ ๔ + แชท `/review/comment`) |
| `23-WORKFLOW_KB_QA.md` | เวิร์กโฟลว์ **ถาม-ตอบ** ลึก (RAG 32/48, คำตอบแบบเจ้าหน้าที่พัสดุ) และฐานความรู้ |
| `24-AWS_CLOUD_OVERVIEW.md` | **AWS-only:** เป้าหมาย สถาปัตยกรรม เฟส A–G |
| `25-AWS_SERVICE_CATALOG.md` | จับคู่ทุกชิ้น Docker กับบริการ AWS |
| `26-AWS_INSTALL_AND_WIRING.md` | ติดตั้ง ตั้งค่า เชื่อมโยงทีละขั้น (VPC→ECS→WAF) |
| `27-AWS_CODE_AND_CUTOVER.md` | โค้ดที่ปรับแล้ว (S3/IAM, Redis TLS) และงานตัดระบบ |
| `28-VERIFICATION-AND-MIGRATION.md` | Combined_Report: ตรวจ Local LLM + เกต + แผนย้าย AWS + เสถียรภาพ (31 ส.ค. 2026) |
| `29-TBD-AWS-CLOUD-ONLY.md` | **TBD** AWS Cloud ล้วน (ห้าม hybrid) + RAG สองแหล่ง + งานค้าง + รีวิวความพร้อมโครง |
| `30-DEV-ASSIGNMENT-MCP-AND-AWS.md` | มอบหมายทีม DEV: สปรินต์ MCP RAG + YAML deploy AWS |

ชุด `01`–`12` เป็นบันทึกออกแบบก่อนหน้า (รวม PoC HTML) — อย่าใช้ `10`/`11` เป็นคู่มือติดตั้งของแอป Docker ปัจจุบัน

| File | Topic |
|------|--------|
| `01_TOR_STRUCTURE_DETAILED_EXPANSION_TH.md` | Legal TOR section expansion |
| `02_TOR_DRAFTING_STEPS_DETAILED_EXPANSION_TH.md` | Drafting step expansion |
| `03_TOR_TECHNICAL_ARCHITECTURE_OVERVIEW_FULL_TH.md` | Technical architecture |
| `04_SYSTEM_COMPONENTS_IMPLEMENTATION_GUIDE_FULL_TH.md` | Component implementation |
| `05-Flow-Diagrams.html` | Flow diagrams |
| `06-UXUI-Mockup.html` | UX mockups (PoC เก่า — เดโมคลิกได้คือ GitHub Pages `index.html`) |
| `07-COMPREHENSIVE-App-Architecture-Diagrams.md` | Architecture diagrams |
| `08-COMPLETE_API_REFERENCE_DOCUMENTATION.md` | API reference |
| `09-BACKEND-FRONTEND-DEVELOPMENT-Structure.md` | Frontend/backend structure |
| `10-DEPLOYMENT_AND_INSTALLATION_GUIDE.md` | Deployment |
| `11-USER_MANUAL_AND_HELP_GUIDE.md` | User manual |
| `12-HYBRID_ONPREM_CLOUD_LLM_ARCHITECTURE.md` | Hybrid LLM architecture |

Historical path: `Discussion/` (see the stub at the repo root).
