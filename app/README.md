# App — TOR drafting / review web stack

โฟลเดอร์นี้คือ **แอปที่รันจริงเท่านั้น** อย่าวาง PDF งานวิจัย, extracts กฎหมาย, หรือบันทึกออกแบบที่นี่

แอปปัจจุบันเป็นกระบวนการร่าง **5 Phase (0–4)** ที่ `/projects/{id}/draft` ไม่ใช่วิซาร์ด 8 ขั้น

| Path | Role |
|------|------|
| `frontend/` | Next.js 14 UI (แดชบอร์ด, ร่าง 5 Phase, แชท, ฐานความรู้, ตรวจสอบ, ผู้ดูแล) |
| `backend/` | FastAPI + LangGraph + rule engine + RAG (pgvector + GraphRAG) |
| `docker/` | Extra Docker assets (placeholder) |

Orchestration อยู่ระดับบน: `../docker-compose.yml`, `../.env.example`

คลัง RAG หลัก **ไม่ได้อยู่ในโฟลเดอร์นี้** — เมล็ดจาก PDF ใน `../documents/sources/` ผ่าน `python -m app.seed_raw_docs` (โฮสต์) เข้า Mongo GridFS + pgvector + Neo4j Compose ยัง mount `../documents/knowledge-base` เป็น `/knowledge-base` สำหรับ `seed_kb` (งานวิจัย ไม่ใช่คลังใช้งาน)

แชท (`LLM_PROVIDER`) และ embeddings (`EMBEDDING_PROVIDER`) เลือกอิสระในทุกโหมด — ตัวอย่าง Claude API + EmbeddingGemma ในเครื่อง เจ้าหน้าที่อัปโหลดเอกสารส่วนตัวที่ `POST /knowledge-base/mine`

## Local commands

จากรากรีโปที่แนะนำ: `docker compose -p tor-app --env-file .env up -d --build`

รันแยกบริการ:

```bash
# API
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 4000

# UI
cd frontend
npm install
npm run dev
```

Seed จาก `backend/` บนโฮสต์:

```bash
python -m app.seed_db
python -m app.seed_raw_docs
```

ทดสอบพร้อม coverage: ดูคำสั่งใน [README.md](../README.md) ที่รากรีโป
