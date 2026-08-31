# TOR Generator

ระบบร่างและตรวจสอบ TOR ภาครัฐ (Terms of Reference) ตาม พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560

แอปที่รันจริงคือ **v0.2.6**: Next.js 14 + FastAPI, พื้นที่ทำงาน **5 Phase (0–4)** ที่ `/projects/{id}/draft`, คลังความรู้ RAG จาก PDF ต้นฉบับ (ต่อยอด MCP + โครง AWS ตาม [Discussions/30](Discussions/30-DEV-ASSIGNMENT-MCP-AND-AWS.md))  
**Production แนะนำ:** Amazon Bedrock (ดู [Discussions/20-AWS_BEDROCK_SETUP.md](Discussions/20-AWS_BEDROCK_SETUP.md))  
**Dev:** LM Studio / Ollama / llama.cpp / SGLang หรือคลาวด์อื่น — สลับจากหน้าผู้ดูแลได้ทั้งหมด

**GitHub Pages คือ UI จำลองเท่านั้น** — เปิดจาก [`index.html`](index.html) ที่ root ของรีโป ให้หน้าตาและเมนูตรงกับแอปปัจจุบัน แต่ไม่เรียก API/LLM จริง และ**ไม่ได้**ใช้ `discussions/06-UXUI-Mockup.html`

ไซต์ที่เผยแพร่: **https://chiraleo2000.github.io/tor-generator/** (branch `gh-pages` มีแค่ mockup)

## โครงสร้างรีโป

วางไฟล์ใหม่ในโฟลเดอร์ที่ตรงกัน — อย่าวาง PDF, บันทึกออกแบบ, หรือซอร์สแอปที่รากรีโป (ข้อยกเว้น: `index.html` + `.nojekyll` สำหรับ GitHub Pages)

| Folder | ใส่ที่นี่ |
|--------|-----------|
| **[app/](app/)** | เว็บแอป: Next.js UI, FastAPI, extras ของ Docker image |
| **[discussions/](discussions/)** | สถาปัตยกรรม, API, UX, หลักฐานเทสต์ (ไม่โหลดตอนรัน) |
| **[documents/](documents/)** | กฎหมาย, PDF ต้นฉบับ, extracts งานวิจัย, แม่แบบ TOR |

ที่เกี่ยวข้อง (ไม่ใช่เว็บแอป):

| Path | บทบาท |
|------|--------|
| [skills/](skills/) | Skill packs ออฟไลน์ (Claude / ChatGPT / Gemini / Hermes) |
| [.kiro/](.kiro/) | สเปก Kiro และสกิลใน IDE — ดู [SKILLS.md](SKILLS.md) |
| `docker-compose.yml` | รัน **app/** พร้อม Postgres, Redis, MinIO, Mongo, Neo4j |

คีย์หมวด TOR ตามมาตรฐานคือ `s1`–`s13` — นิยามร่วม: `app/backend/app/domain/tor_sections.py` และ `app/frontend/src/lib/tor-sections.ts`

## รันบนเครื่อง (Docker)

โฟลเดอร์รีโปเป็นภาษาไทย ต้องตั้งชื่อโปรเจกต์ Compose เป็น `tor-app`

```bash
copy .env.example .env
docker compose -p tor-app --env-file .env up -d --build
```

| บริการ | URL |
|--------|-----|
| UI | http://localhost:3000 |
| API | http://localhost:4000/api/v1 |
| Health | http://localhost:4000/health (`postgres` `redis` `minio` `mongo` `neo4j`) |
| MinIO console | http://localhost:9001 |
| Neo4j browser | http://localhost:7474 |

รอจนทุกคอนเทนเนอร์ `healthy` แล้วใส่ข้อมูลเริ่มต้น:

```bash
docker compose -p tor-app --env-file .env exec backend python -m app.seed_db
```

บัญชีทดลอง (รหัส `Passw0rd!`): `officer@example.go.th`, `admin@example.go.th`, `reviewer@example.go.th`

### คลังความรู้ RAG (บังคับ)

คลังใช้งานมาจาก PDF สองกลุ่ม — **ไม่** ingest JSON ใน `documents/knowledge-base` เป็นคลังหลัก รันจาก **โฮสต์** (bind-mount ชื่อไทยในคอนเทนเนอร์มัก Errno 5):

```bash
cd app/backend
set POSTGRES_HOST=127.0.0.1
set LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
set MONGO_URI=mongodb://127.0.0.1:27017
set NEO4J_URI=bolt://127.0.0.1:7687
python -m app.seed_raw_docs
```

| กลุ่ม | แหล่ง | ใครเห็น |
|-------|--------|---------|
| `mandatory_handbook` | `documents/sources/คู่มือแนวปฏิบัติ_การจัดซื้อจัดจ้างภาครัฐ.pdf` | ทุกบัญชี |
| `mandatory_raw` | PDF ใน `documents/sources/การจัดซื้อจัดจ้าง/ข้อมูลดิบ` | ทุกบัญชี |
| `user` | อัปโหลดที่หน้าฐานความรู้ (`POST /api/v1/knowledge-base/mine`) | **เฉพาะเจ้าของ** — เจ้าหน้าที่อื่นไม่เห็น |

อย่าส่ง `POSTGRES_HOST=127.0.0.1` ในเชลล์เดียวกับ `docker compose` — Compose จะทับ `.env` แล้ว backend หา postgres ในเครือข่าย Docker ไม่เจอ

`python -m app.seed_kb` ยังมีสำหรับ extracts งานวิจัยเท่านั้น

## โหมด LLM

ค่าเริ่มต้น `DEPLOYMENT_MODE=on_prem` และ `LLM_PROVIDER=lm_studio`

| โหมด | ความหมาย | แชท / embeddings |
|------|----------|-------------------|
| `on_prem` | ค่าเริ่มต้นในเครื่อง | เลือกอิสระ เช่น LM Studio แชท + EmbeddingGemma หรือ Claude + EmbeddingGemma |
| `cloud` | เน้นคีย์ API | เลือกอิสระ เช่น Claude แชท + OpenAI embeddings หรือ Claude + embeddings ในเครื่อง |
| `hybrid` | ผสมชัดเจน | เหมือนกัน — `LLM_PROVIDER` กับ `EMBEDDING_PROVIDER` ไม่ถูกสลับคู่ |

ตัวอย่าง: `DEPLOYMENT_MODE=hybrid`, `LLM_PROVIDER=claude`, `EMBEDDING_PROVIDER=local`, `ANTHROPIC_API_KEY=...` — แชทใช้ Claude, ฝังเวกเตอร์ใช้ EmbeddingGemma บน LM Studio (`LOCAL_EMBEDDING_SERVER=lm_studio`)

ผู้ดูแลสลับผู้ให้บริการได้ที่ **การตั้งค่า AI** — บันทึกมีผลทันที ไม่ต้องรีสตาร์ท backend ถ้าเปลี่ยนโมเดล embeddings ต้อง `seed_raw_docs` ใหม่

### LM Studio (ค่าเริ่มต้น)

1. โหลดแชท **google/gemma-4-e4b** และ embeddings **text-embedding-embeddinggemma-300m**
2. เปิดเซิร์ฟเวอร์ OpenAI-compatible ที่ `http://127.0.0.1:1234/v1`
3. จาก Docker backend ใช้ `http://host.docker.internal:1234/v1`

## รันโดยไม่ใช้ Compose

```bash
cd app/backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 4000
```

```bash
cd app/frontend
npm install
npm run dev
```

เบราว์เซอร์เรียก `/api/v1` ผ่าน rewrite ของ Next.js (อย่าตั้ง `NEXT_PUBLIC_API_URL` เป็นโฮสต์ Docker ชื่อ `backend`)

## ทดสอบ (coverage เต็มบนโฮสต์)

Production image ไม่คัดลอกโฟลเดอร์ `tests/` — รันบนโฮสต์

```bash
# Backend (ตัด live LLM)
cd app/backend
python -m pytest tests -q --tb=short --cov=app --cov-report=term-missing --cov-report=html -m "not live_llm"

# Backend รวมยิง LM Studio จริง (ต้องโหลดแชท+embeddings ที่พอร์ต 1234)
python -m pytest -m live_llm -v -s
python -m pytest tests -q --tb=short --cov=app --cov-report=term-missing --cov-report=html
```

หมวดคลังส่วนตัวใช้ `category=other` (ป้าย **ข้อมูลอื่น ๆ**) ดาวน์โหลดที่ `GET /api/v1/knowledge-base/mine/{id}/file`

รายงาน HTML: `app/backend/htmlcov/index.html` (ตัด `seed_db` / `seed_kb` / `seed_raw_docs` / `main` ตาม `pyproject.toml`)

```bash
# Frontend unit + coverage
cd app/frontend
npm test
npm run test:coverage
```

รายงาน HTML: `app/frontend/coverage/index.html`

```bash
# E2E (สแตก Docker ต้องขึ้นที่ http://localhost:3000; รัน 1 worker เพราะบัญชีทดลองร่วมกัน)
cd app/frontend
npx playwright install chromium
npm run test:e2e
npm run test:e2e:headed
```

ชุดล่าสุดบนโฮสต์ (**24 ส.ค. 2026**):

`npm run test:e2e:headed` เปิด Chromium ให้เห็นจริง (slowMo 400ms) ทั้ง **21 เคส** บน Docker `:3000` + LM Studio — รวมล็อกอิน แดชบอร์ด แอดมิน คู่มือทุกแท็บ ฐานความรู้ ตรวจ TOR ถาม-ตอบ แนบไฟล์คลัง วิซาร์ด Phase 0–4 และร่าง Gemma

| ชุด | ผล |
|-----|-----|
| pytest `-m "not live_llm"` | **1533 ผ่าน** · cov **85%** |
| pytest `-m live_llm` | **14 ผ่าน** |
| Vitest `npm run test:coverage` | **177 ผ่าน** / 42 ไฟล์ · lines **82.36%** |
| Playwright `test:e2e:headed` | **21 ผ่าน** / 0 ล้ม (~4.7 นาที · เบราว์เซอร์โชว์บนจอ) |

รายละเอียดและภาพ: [discussions/18-TEST_EVIDENCE.md](discussions/18-TEST_EVIDENCE.md)

## คู่มือเพิ่มเติม

- ผู้ใช้: [discussions/13-USER_GUIDELINE.md](discussions/13-USER_GUIDELINE.md)
- ติดตั้ง: [discussions/14-INSTALLATION.md](discussions/14-INSTALLATION.md)
- คำอธิบายแอป: [discussions/15-APPLICATION_DESCRIPTION.md](discussions/15-APPLICATION_DESCRIPTION.md)
- Backend: [discussions/16-BACKEND_ARCHITECTURE.md](discussions/16-BACKEND_ARCHITECTURE.md)
- Frontend: [discussions/17-FRONTEND_ARCHITECTURE.md](discussions/17-FRONTEND_ARCHITECTURE.md)
- หลักฐานเทสต์: [discussions/18-TEST_EVIDENCE.md](discussions/18-TEST_EVIDENCE.md)

## หยุดสแตก

```bash
docker compose -p tor-app --env-file .env down      # เก็บ volume
docker compose -p tor-app --env-file .env down -v   # ลบข้อมูลด้วย
```
