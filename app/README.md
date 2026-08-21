# แอป — ระบบร่างและตรวจสอบ TOR

โฟลเดอร์นี้คือ **แอปที่รันจริงเท่านั้น** อย่าวาง PDF งานวิจัย, extracts กฎหมาย, หรือบันทึกออกแบบที่นี่

แอปปัจจุบันเป็นกระบวนการร่าง **5 Phase (0–4)** ที่ `/projects/{id}/draft` ไม่ใช่วิซาร์ด 8 ขั้น — Phase 0 `Phase0Upload` (กดเริ่มวิเคราะห์) → Phase 1 `Phase1Coverage` → Phase 2 `Phase2Qa` → Phase 3 `Phase3Draft` → Phase 4 `Phase4Review` + `Phase4Export` ผ่าน `ConfirmPhaseDialog`

| เส้นทาง | หน้าที่ |
|---------|---------|
| `frontend/` | Next.js 14 UI (แดชบอร์ด, ร่าง 5 Phase, แชท, ฐานความรู้, ตรวจสอบ, ผู้ดูแล) |
| `backend/` | FastAPI + LangGraph + rule engine + RAG (pgvector + GraphRAG) |
| `docker/` | Extra Docker assets (placeholder) |

Orchestration อยู่ระดับบน: `../docker-compose.yml`, `../.env.example`

คลัง RAG หลัก **ไม่ได้อยู่ในโฟลเดอร์นี้** — เมล็ดจาก PDF ใน `../documents/sources/` ผ่าน `python -m app.seed_raw_docs` (โฮสต์) เข้า Mongo GridFS + pgvector + Neo4j Compose ยัง mount `../documents/knowledge-base` เป็น `/knowledge-base` สำหรับ `seed_kb` (งานวิจัย ไม่ใช่คลังใช้งาน)

แชท (`LLM_PROVIDER`) และ embeddings (`EMBEDDING_PROVIDER`) เลือกอิสระในทุกโหมด — ตัวอย่าง Claude API + EmbeddingGemma ในเครื่อง เจ้าหน้าที่อัปโหลดเอกสารส่วนตัวที่ `POST /knowledge-base/mine`

## คำสั่งบนเครื่อง

จากรากรีโปที่แนะนำ: `docker compose -p tor-app --env-file .env up -d --build`

รันแยกบริการ:

```bash
# ส่วนหลังบ้าน
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 4000

# ส่วนหน้าบ้าน
cd frontend
npm install
npm run dev
```

Seed จาก `backend/` บนโฮสต์:

```bash
python -m app.seed_db
python -m app.seed_raw_docs
```

ตรวจสด 21 ส.ค. 2026: เครื่องมือร่าง TOR / ตรวจสอบ TOR / ถาม-ตอบ / ฐานความรู้ของฉัน ใช้งานได้จริงบนสแตก Docker + LM Studio — รายละเอียดใน [../Discussions/18-TEST_EVIDENCE.md](../Discussions/18-TEST_EVIDENCE.md)

ทดสอบพร้อม coverage: ดูคำสั่งใน [README.md](../README.md) ที่รากรีโป
