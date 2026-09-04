# แหล่งข้อมูลคลังความรู้ (RAG ในเครื่อง)

## สิ่งที่แอปใช้จริงตอนนี้

ถาม-ตอบ / ร่าง / ตรวจสอบ ดึงชิ้นข้อความจาก **pgvector ใน Postgres**  
โมเดลตอบคือ **LM Studio** (`LLM_PROVIDER=lm_studio`)  
**MCP RAG เปิดใน Compose ท้องถิ่น** — `MCP_RAG_ENABLED=true` และ `local-pgvector-mcp` ใน `app/infra/mcp/rag-sources.yaml` ชี้ `http://mcp-rag:8765`  
เซิร์ฟเวอร์นี้ค้นคลังเดียวกับเอกสารใต้ `documents/sources/` ไม่ใช่สตับจำลอง  
`agency-legal-mcp` / `retrieve-stub` ยัง `enabled: false`

คลังต้นฉบับคือ PDF ใต้ `documents/sources/` ไม่ใช่ไฟล์ JSON ในโฟลเดอร์ `documents/knowledge-base/`

| กลุ่ม | พาธ | บทบาท |
|------|------|--------|
| คู่มือแนวปฏิบัติ | `documents/sources/คู่มือแนวปฏิบัติ_การจัดซื้อจัดจ้างภาครัฐ.pdf` | บังคับ |
| ข้อมูลดิบกฎหมาย/ระเบียบ | `documents/sources/การจัดซื้อจัดจ้าง/ข้อมูลดิบ/` | พ.ร.บ. ระเบียบ กฎกระทรวง หนังสือเวียน |
| เอกสารจัดจ้างทำของ | `documents/sources/การจัดจ้างทำของ/` | PDF ในคลังท้องถิ่น (pgvector + MCP ท้องถิ่น) |
| ตัวอย่าง | `documents/sources/ตัวอย่าง/` | TOR / ตัวอย่างประกาศ |

อัปเดตคลัง (จากโฮสต์, ข้ามไฟล์ที่ hash ซ้ำแล้ว):

```
cd app/backend
set POSTGRES_HOST=127.0.0.1
set LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
python -m app.seed_raw_docs
```

`RAG_SOURCES=local` — ไม่ดึง Custom RAG / PageIndex stub  
MCP เป็นแหล่ง retrieve เพิ่มบนคลังเดียวกัน

## แหล่งภายนอกในอนาคต (เมื่อมี URL จริง)

เปิด `agency-legal-mcp` เมื่อมีเซิร์ฟเวอร์ retrieve ของหน่วยงาน แล้วตั้ง `enabled: true` หรือ `MCP_RAG_SERVERS_JSON`  
อย่าเปิด `retrieve-stub`

1. **กรมบัญชีกลาง (CGD)** — หนังสือเวียน กวจ. หลัง พ.ศ. 2560, ประกาศคณะกรรมการนโยบายฯ
2. **ระบบ e-GP** — ตัวอย่าง TOR ที่ประกาศจริง
3. **DGA** — มาตรฐาน TOR งานไอที/ดิจิทัลภาครัฐ
4. **สำนักงบประมาณ** — เกณฑ์ราคากลางไอซีที
5. **สตง.** — ข้อสังเกตจากการตรวจสอบ
