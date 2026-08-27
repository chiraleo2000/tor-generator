# Discussions — design notes

Architecture, API, UX, and product write-ups. **Not imported** by Next.js or FastAPI.

Help text in the running app is under `/help` (`app/frontend`). The current operator/install/architecture/test/operating guides are `13`–`19` below (Docker + LM Studio Gemma). Files `01`–`12` are earlier design notes.

Clickable UX/UI demo: **https://chiraleo2000.github.io/tor-generator/** (`index.html` at repo root, branch `gh-pages`). `06-UXUI-Mockup.html` is the older PoC mock.

เอกสารชุดปัจจุบันของสแตกที่รันด้วย Docker + LM Studio Gemma + Mongo + Neo4j คือ **13–23**. เส้นทางหลักบน UI คือพื้นที่ทำงาน **5 Phase** + เมนูถาม-ตอบ `/chat` / ฐานความรู้ / ตรวจสอบ:

คำอธิบายเวิร์กโฟลว์สามบริการหลัก (ภาษาไทย ตรวจจากโค้ดจริง **26 ส.ค. 2026 รอบบ่าย**) อยู่ที่ **21–23** ใช้ชุดนี้เมื่อขัดกับบันทึกเก่าใน `15`/`19` (เช่น วิเคราะห์ขั้นที่ ๐ ไม่ดึงกฎหมายอัตโนมัติแล้ว และเกต HITL บนปุ่มไปทบทวนไม่มีแล้ว)

| File | Topic |
|------|--------|
| `13-USER_GUIDELINE.md` | คู่มือผู้ใช้ทีละขั้นพร้อมภาพ |
| `14-INSTALLATION.md` | ติดตั้งและรัน |
| `15-APPLICATION_DESCRIPTION.md` | คำอธิบายแอป |
| `16-BACKEND_ARCHITECTURE.md` | สถาปัตยกรรม backend |
| `17-FRONTEND_ARCHITECTURE.md` | สถาปัตยกรรม frontend |
| `18-TEST_EVIDENCE.md` | หลักฐานเทสต์ — Vitest 205 / pytest 1596 / E2E headed wizard 0→4 + **ECT live 26 ส.ค. 2026** (27/27 · ร่างครบ · ตรวจ 74/95/76) + Sonar QG OK |
| `19-APPLICATION_OPERATING_REPORT.md` | รายงานการทำงานครบ frontend/backend/workflows/tools + ภาพ unit tests (24 ส.ค. 2026 อัปเดตเส้นทาง 5 Phase) |
| `19-APPLICATION_OPERATING_REPORT.docx` | ฉบับ Word (TH Sarabun New, ตาราง, ภาพจอ, ไดอะแกรม) |
| `19-APPLICATION_OPERATING_REPORT.pdf` | ฉบับ PDF ส่งออกจาก Word |
| `19-APPLICATION_OPERATING_REPORT.pptx` | สไลด์นำเสนอ (สร้างจาก `_build_report_exports.py`) |
| `20-AWS_BEDROCK_SETUP.md` | **Setup บน Amazon / Bedrock (path production หลัก)** |
| `21-WORKFLOW_DRAFT_TOR.md` | เวิร์กโฟลว์ **ร่าง TOR** (ห้าขั้น จากโค้ด 26 ส.ค. 2026 — ไม่มีเกต HITL บนจอ) |
| `22-WORKFLOW_REVIEW_TOR.md` | เวิร์กโฟลว์ **ตรวจสอบ TOR** (หน้าล้วน `/review` + ขั้นที่ ๔ + แชท `/review/comment`) |
| `23-WORKFLOW_KB_QA.md` | เวิร์กโฟลว์ **ถาม-ตอบ** ลึก (RAG 32/48, คำตอบแบบเจ้าหน้าที่พัสดุ) และฐานความรู้ |

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
