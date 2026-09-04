# เอกสาร — คลังกฎหมาย แม่แบบ และงานวิจัย

โฟลเดอร์นี้เก็บ **ข้อมูลและเอกสารอ้างอิงภาษาไทย** ไม่ใช่ซอร์สแอป อย่าคัดลอกต้นไม้นี้ไปไว้ใน `app/frontend` หรือ `app/backend`

แอปที่รันจริงอ้างอิง: TOR Generator **v0.3.1** — คู่มือติดตั้ง [Discussions/14](../Discussions/14-INSTALLATION.md) · คำอธิบายแอป [15](../Discussions/15-APPLICATION_DESCRIPTION.md) · หลักฐานเทสต์ล่าสุด [18](../Discussions/18-TEST_EVIDENCE.md) · AWS Cloud ล้วน [29](../Discussions/29-TBD-AWS-CLOUD-ONLY.md) · มอบหมายทีม [30](../Discussions/30-DEV-ASSIGNMENT-MCP-AND-AWS.md)

## คลังที่แอปใช้จริง กับ คลังงานวิจัย

แอปที่รันจริงฝังเวกเตอร์จาก **PDF ต้นฉบับ** ด้วย `python -m app.seed_raw_docs` จากโฟลเดอร์ `app/backend` บนเครื่องโฮสต์

| กลุ่มคลัง | แหล่ง | ใครเห็น |
|-----------|--------|---------|
| คู่มือแนวปฏิบัติ (บังคับ) | `sources/คู่มือแนวปฏิบัติ_การจัดซื้อจัดจ้างภาครัฐ.pdf` | ทุกบัญชี |
| ข้อมูลดิบกฎหมาย/ระเบียบ (บังคับ) | PDF ใน `sources/การจัดซื้อจัดจ้าง/ข้อมูลดิบ` | ทุกบัญชี |
| เอกสารของฉัน | อัปโหลดในแอป (`POST /api/v1/knowledge-base/mine`) | เฉพาะเจ้าของ |

โฟลเดอร์ `knowledge-base/` เป็น **สารสกัดงานวิจัย** (Markdown / JSON) — Compose ยัง mount เป็น `/knowledge-base` สำหรับ `python -m app.seed_kb` แต่**ไม่ใช่คลัง RAG หลักของแอป**

อย่าส่ง `POSTGRES_HOST=127.0.0.1` ในเชลล์เดียวกับ `docker compose` — ค่านี้ทับ `.env` แล้ว backend ใน Docker หา postgres ไม่เจอ

## โครงสร้างโฟลเดอร์

| เส้นทาง | หน้าที่ |
|---------|---------|
| `knowledge-base/` | สารสกัดงานวิจัย (Markdown + JSON) ไม่ใช่คลังฝังเวกเตอร์หลัก |
| `templates/` | แม่แบบ TOR ตามประเภทงาน (Markdown ภาษาไทย) |
| `sources/` | PDF/DOCX ต้นฉบับภาษาไทย — มักไม่ขึ้น GitHub เพราะไฟล์ใหญ่ เก็บไว้ในเครื่อง |
| `research/` | `analysis/`, `raw_text/`, `zip_output/` — ผลสกัดข้อความจากเอกสาร |
| `extract-scripts/` | สคริปต์สกัด PDF/DOCX (ไม่ใช่คำสั่ง seed ของ FastAPI) |
| `prompts/` | คำสั่งเขียน TOR สำหรับ Claude / ChatGPT และคู่มือภาษาราชการ |
| `docs/` | คู่มือใช้สกิลบนแพลตฟอร์ม LLM |

คำสั่งใส่ข้อมูลแอปอยู่ใน `app/backend/` (`python -m app.seed_db` และ `python -m app.seed_raw_docs`)

ตรวจรอบ 20 ส.ค. 2026 บนแอปที่รันจริง: คลัง RAG **80 ไฟล์ / 507 chunks** คำถามวิธีเฉพาะเจาะจงได้คำตอบพร้อม citations — ไม่ ingest โฟลเดอร์นี้เป็นคลังหลัก
