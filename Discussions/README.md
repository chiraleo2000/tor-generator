# Discussions — design notes

Architecture, API, UX, and product write-ups. **Not imported** by Next.js or FastAPI.

Help text in the running app is under `/help` (`app/frontend`). The current operator/install/architecture/test/operating guides are `13`–`19` below (Docker + LM Studio Gemma). Files `01`–`12` are earlier design notes.

Clickable UX/UI demo: **https://chiraleo2000.github.io/tor-generator/** (`index.html` at repo root, branch `gh-pages`). `06-UXUI-Mockup.html` is the older PoC mock.

เอกสารชุดปัจจุบันของสแตกที่รันด้วย Docker + LM Studio Gemma + Mongo + Neo4j คือ **13–19**. แอป **v0.2.3** เพิ่มเส้นทาง backend `/api/v1/agent` และ `/api/v1/kb-chat` คู่กับพื้นที่ทำงาน 5 Phase:

| File | Topic |
|------|--------|
| `13-USER_GUIDELINE.md` | คู่มือผู้ใช้ทีละขั้นพร้อมภาพ |
| `14-INSTALLATION.md` | ติดตั้งและรัน |
| `15-APPLICATION_DESCRIPTION.md` | คำอธิบายแอป |
| `16-BACKEND_ARCHITECTURE.md` | สถาปัตยกรรม backend |
| `17-FRONTEND_ARCHITECTURE.md` | สถาปัตยกรรม frontend |
| `18-TEST_EVIDENCE.md` | หลักฐานเทสต์ — smoke 3 เครื่องมือ + unit tests 20 ส.ค. 2026 |
| `19-APPLICATION_OPERATING_REPORT.md` | รายงานการทำงานครบ frontend/backend/workflows + ภาพ unit tests (20 ส.ค. 2026; Vitest 128 / pytest 1448) |
| `19-APPLICATION_OPERATING_REPORT.docx` | ฉบับ Word (TH Sarabun New, ตาราง, ภาพจอ, ไดอะแกรม) |
| `19-APPLICATION_OPERATING_REPORT.pdf` | ฉบับ PDF ส่งออกจาก Word |
| `19-APPLICATION_OPERATING_REPORT.pptx` | สไลด์นำเสนอ 23 หน้า |

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
