# การติดตั้งและรันระบบ TOR

คู่มือนี้สำหรับสแตกที่รันจริง: Next.js + FastAPI ใน Docker  
**Production แนะนำ:** Amazon Bedrock บนบัญชี AWS — ดู [`20-AWS_BEDROCK_SETUP.md`](20-AWS_BEDROCK_SETUP.md)  
**Dev / on-prem:** LM Studio บนเครื่องโฮสต์ (ค่าเริ่มต้น) หรือ Ollama / llama.cpp / SGLang — สลับได้จาก Admin โดยไม่ถอดตัวเลือก

แอปปัจจุบันเป็นกระบวนการร่าง **5 Phase (0–4)** ไม่ใช่วิซาร์ด 8 ขั้น และไม่ใช่ไฟล์ HTML ต้นแบบใน `06-UXUI-Mockup.html` — ไฟล์นั้นเป็นแบบออกแบบเท่านั้น

ดูคำอธิบายแอปที่ `15-APPLICATION_DESCRIPTION.md` และคู่มือผู้ใช้ที่ `13-USER_GUIDELINE.md`

หน้าจำลองบน GitHub Pages (คลิกได้ แต่ไม่เรียก API/LLM): https://chiraleo2000.github.io/tor-generator/  
ไฟล์คือ `index.html` ที่ราก — ไม่ใช่แอป Docker

## สิ่งที่ต้องมี

- Docker Desktop (Windows/macOS) หรือ Docker Engine + Compose
- **Production บน Amazon:** บัญชี AWS + Bedrock model access (ไม่บังคับ GPU บนเครื่องแอป)
- สำหรับโหมดในเครื่อง: เซิร์ฟเวอร์ OpenAI-compatible ที่ `http://127.0.0.1:1234` (LM Studio) พร้อม
  - Chat: **google/gemma-4-e4b**
  - Embeddings: **text-embedding-embeddinggemma-300m** (768 มิติ)
- หรือ Ollama ที่พอร์ต **11434** / llama.cpp ที่พอร์ต **8080** / SGLang (`docker compose --profile sglang`) เลือกได้จากหน้าการตั้งค่า AI
- Git และ (ถ้าจะรันเทสต์บนโฮสต์) Node.js 20 และ Python 3.11

โฟลเดอร์รีโปเป็นภาษาไทย ต้องตั้งชื่อโปรเจกต์ Compose เป็น `tor-app` มิฉะนั้นชื่อโปรเจกต์จะว่าง

## 1. ตั้งค่าสภาพแวดล้อม

จากรากรีโป:

```bash
copy .env.example .env   # Windows
# cp .env.example .env  # macOS/Linux
```

ตรวจใน `.env`:

```
COMPOSE_PROJECT_NAME=tor-app
DEPLOYMENT_MODE=on_prem
LLM_PROVIDER=lm_studio
EMBEDDING_PROVIDER=local
LOCAL_EMBEDDING_SERVER=lm_studio
LM_STUDIO_BASE_URL=http://host.docker.internal:1234/v1
LM_STUDIO_MODEL=google/gemma-4-e4b
LM_STUDIO_EMBEDDING_MODEL=text-embedding-embeddinggemma-300m
LM_STUDIO_TIMEOUT=180
OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
LLAMA_CPP_BASE_URL=http://host.docker.internal:8080/v1
MONGO_URI=mongodb://mongo:27017
MONGO_DB=tor_docs
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme_neo4j
```

คีย์คลาวด์ (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, และคีย์ Bedrock / Azure Foundry / OpenAI-compatible) ว่างได้ถ้าใช้เฉพาะโมเดลท้องถิ่น — Compose ส่งค่าผ่านไปถ้ามี แต่ไม่บังคับว่างแล้ว คีย์ที่บันทึกจากหน้าผู้ดูแลอยู่ใน Postgres และมีผลทันทีหลังกดบันทึก (ไม่ต้องรีสตาร์ท backend)

Alembic `005_agent_sessions` สร้างตาราง `agent_sessions`, `kb_chat_sessions` และคอลัมน์ `projects.workflow_mode` เมื่อ backend สตาร์ท (หรือ `alembic upgrade head` จาก `app/backend`)  
Alembic `006_kb_corpus_group` เพิ่ม `knowledge_base_documents.corpus_group` (`mandatory_handbook` / `mandatory_raw` / `user`)

## 2. เปิด LM Studio (โหมดในเครื่อง)

1. Start server ที่พอร์ต **1234**
2. Load **google/gemma-4-e4b** สำหรับแชท
3. Load **text-embedding-embeddinggemma-300m** สำหรับ embeddings
4. ทดสอบในเบราว์เซอร์หรือด้วย `GET http://127.0.0.1:1234/v1/models`

## 2b. SGLang บน GPU ท้องถิ่น (ร่าง/ตรวจแบบ structured JSON)

ถ้ามี NVIDIA GPU + NVIDIA Container Toolkit ให้ใช้ SGLang เป็น engine หลักของ **วิเคราะห์ intake / ReviewAgent / graph extract** (`guided_json` ตาม schema) และเป็นปลายทางแชทเมื่อ `/health` ขึ้น

**GPU หนึ่งตัว — อย่าโหลด Gemma ใน LM Studio คู่กับ `sglang-llm` พร้อมกัน**

```bash
# โมเดลแชท + guided JSON ที่ :30000 — ไม่สตาร์ท embeddings
docker compose -p tor-app --env-file .env --profile sglang up -d

# ฝังเวกเตอร์ที่ :30001 เฉพาะตอนยังไม่มีคลัง หรือต้องการ seed ใหม่ (กิน VRAM เพิ่ม)
docker compose -p tor-app --env-file .env --profile sglang-embed up -d
```

ตรวจสุขภาพ:

```bash
curl.exe http://localhost:4000/health
curl.exe http://localhost:30000/health
```

เมื่อ `http://localhost:30000/health` ขึ้น แอปจะชี้แชท/ร่าง/งาน JSON ไป SGLang อัตโนมัติ (แม้ `LLM_PROVIDER=lm_studio`)  
ถ้า SGLang ดับ แชทและร่างร้อยแก้วกลับไป LM Studio ที่ `:1234` — งานที่ต้องเป็น JSON ใช้ `parse_json_lenient` เป็น fallback  
อย่าอ้างว่า structured generation ถูกทดสอบแล้ว ถ้า `:30000/health` ไม่ขึ้น

แชทยังเก็บห้อง/ข้อความใน Postgres + pgvector ตามเดิม — ไม่ย้ายไป Mongo/Redis และไม่บังคับ Neo4j

Alembic `008_review_jobs` สร้างตาราง `review_jobs` สำหรับตรวจ TOR แบบสแตนด์อโลน (งานไม่หายเมื่อรีสตาร์ท)

## 3. ขึ้นสแตก

จากรากรีโป:

```bash
docker compose -p tor-app --env-file .env up -d --build
```

บริการ:

| บริการ | พอร์ต |
|--------|--------|
| frontend (Next.js) | 3000 |
| backend (FastAPI) | 4000 |
| postgres + pgvector | 5432 |
| mongo (GridFS ต้นฉบับ) | 27017 |
| neo4j (GraphRAG) | 7474 / 7687 |
| redis | 6379 |
| minio (ส่งออก TOR) | 9000 / 9001 |

รอจนสถานะ healthy แล้วเปิด http://localhost:3000  
`GET http://localhost:4000/health` ต้องมี `postgres` `redis` `minio` `mongo` `neo4j` เป็น `up`

หลังแก้โค้ด frontend/backend ให้ build ใหม่พร้อมบริการใหม่:

```bash
docker compose -p tor-app --env-file .env up -d --build frontend backend mongo neo4j
```

หลังย้ายมิติ embeddings เป็น 768 backend จะรัน Alembic เมื่อสตาร์ท แล้วต้องฝังเวกเตอร์ใหม่จาก PDF ข้อมูลดิบ (ไม่ ingest JSON extracts เก่าเป็นคลังใช้งาน):

จาก **โฮสต์** (เพราะ bind-mount path ไทยมัก Errno 5):

```bash
cd app/backend
set POSTGRES_HOST=127.0.0.1
set LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
set MONGO_URI=mongodb://127.0.0.1:27017
set NEO4J_URI=bolt://127.0.0.1:7687
python -m app.seed_raw_docs
```

เปิด LM Studio ที่พอร์ต 1234 และโหลดทั้งแชทกับ embeddings ก่อนรัน `seed_raw_docs` และก่อนชุดเทสต์ที่ติด LLM

`python -m app.seed_kb` ยังมีสำหรับชุด extracts ใน `documents/knowledge-base` แต่**ไม่ใช่คลังใช้งานหลังรีเซ็ตรอบนี้**

## 4. ใส่ข้อมูลเริ่มต้น

```bash
docker compose -p tor-app --env-file .env exec backend python -m app.seed_db
```

บัญชีทดลอง: `officer@example.go.th` / `admin@example.go.th` / `reviewer@example.go.th` รหัส `Passw0rd!`

คลังกฎหมายใช้งานรอบนี้มาจาก PDF สองกลุ่มผ่าน `seed_raw_docs`:

- `documents/sources/คู่มือแนวปฏิบัติ_การจัดซื้อจัดจ้างภาครัฐ.pdf`
- ไฟล์ใน `documents/sources/การจัดซื้อจัดจ้าง/ข้อมูลดิบ`

ไม่ ingest JSON extracts ใน `documents/knowledge-base` เป็นคลังหลัก เจ้าหน้าที่อัปโหลดไฟล์ส่วนตัวที่หน้าฐานความรู้ (`POST /knowledge-base/mine`) — ระบบ chunk/embed ให้เฉพาะบัญชีนั้น

`python -m app.seed_kb` ยังมีถ้าต้องการชุด extracts เก่าสำหรับงานวิจัย — บน Windows ชื่อโฟลเดอร์ไทยอาจทำให้ bind-mount ล้ม (Errno 5)

## 5. สลับ Local / Cloud จากหน้าผู้ดูแล

เข้าสู่ระบบด้วยบัญชี admin แล้วเปิด **การตั้งค่า AI**:

- **Production แนะนำ:** Amazon Bedrock (คู่มือเต็ม [`20-AWS_BEDROCK_SETUP.md`](20-AWS_BEDROCK_SETUP.md)) — เว้นว่าง AWS key ได้ถ้าใช้ IAM role บน EC2/ECS
- แชทและ embeddings เลือกอิสระในทุกโหมด ไม่สลับคู่อัตโนมัติ เช่น Claude API + EmbeddingGemma ในเครื่อง
- รันในเครื่อง: LM Studio / Ollama / llama.cpp / **SGLang** — เซิร์ฟเวอร์ embeddings แยกจากแชทได้ (`LOCAL_EMBEDDING_SERVER`)
- คลาวด์: Bedrock / Claude / OpenAI / Gemini / Azure Foundry / OpenAI-compatible + API key (ใส่ในหน้านี้ได้ ไม่ต้องใส่ใน `.env`)
- **Custom RAG:** เปิดแหล่ง HTTP เสริม (`POST {base}/v1/retrieve`) รวมกับคลังในเครื่องได้
- ผสม: ค่าที่เลือกในช่องแชท/embeddings คือแหล่งที่ใช้งานจริง (คลาวด์ต้องมีคีย์ของฝั่งนั้น ยกเว้น Bedrock ที่ใช้ IAM role)
- คลังเวกเตอร์: `pgvector` หรือ `qdrant` (ใช้ได้ทั้งโหมดในเครื่อง)
- **ทดสอบการเชื่อมต่อ** ยิงทั้งแชทและ embeddings ไม่ต้องรีสตาร์ท
- **บันทึก** มีผลทันทีในกระบวนการ — ไม่ต้อง `restart backend`

ถ้าเปลี่ยนผู้ให้บริการ embeddings หรือชื่อโมเดลฝังตัว ต้อง `python -m app.seed_raw_docs` อีกครั้ง (หน้าผู้ดูแลจะเตือน `reingest_required`)

### ตัวอย่างการตั้งค่าผสม (ผู้ดูแล → การตั้งค่า AI)

| เป้าหมาย | แชท | ฝังเวกเตอร์ | หมายเหตุ |
|----------|-----|-------------|----------|
| **Amazon production** | Amazon Bedrock | Bedrock Titan หรือในเครื่อง | ดู 20-AWS_BEDROCK_SETUP · IAM role หรือ access key |
| Claude + EmbeddingGemma ในเครื่อง | Claude (Anthropic) | ในเครื่อง | ใส่ Anthropic key · เปิด LM Studio โหลด EmbeddingGemma |
| Claude + OpenAI embeddings | Claude (Anthropic) | ฝังเวกเตอร์ OpenAI | ใส่ Anthropic + OpenAI key · **ต้อง** seed ใหม่หลังบันทึก |
| Gemma ในเครื่อง (dev) | LM Studio | ในเครื่อง | โหลดทั้งแชทและ EmbeddingGemma ที่พอร์ต 1234 — อย่าคู่กับ sglang-llm บน GPU เดียว |
| SGLang ร่าง/ตรวจ | SGLang (`:30000`) | pgvector ที่ seed แล้ว | `docker compose --profile sglang up` · GPU NVIDIA · อย่าเปิด `sglang-embed` คู่บน GPU เดียว |

โหมด (`on_prem` / `cloud` / `hybrid`) เป็นป้ายเท่านั้น — ค่าที่เลือกในช่องแชทและฝังเวกเตอร์คือแหล่งที่ใช้จริง · **ทดสอบการเชื่อมต่อ** ยิงทั้งสองฝั่ง · **บันทึก** มีผลทันที

เมื่อหลายผู้ใช้เรียก AI พร้อมกัน ระบบมี Redis admission queue + แสดงสถานะรอคิวใน UI (แชท / ร่าง / ตรวจ)

## 6. ตรวจสุขภาพ

```bash
curl.exe http://localhost:4000/health
curl.exe http://localhost:3000
curl.exe http://localhost:30000/health
```

Frontend พร็อกซี `/api/v1/*` ไปที่ backend ภายใน Docker (`BACKEND_INTERNAL_URL=http://backend:4000/api/v1`). `next.config.js` ตั้ง `experimental.proxyTimeout` เป็น 300000 มิลลิวินาที เพราะร่างด้วย AI / แชท SSE มักเกินค่าเริ่มต้น 30 วินาทีของ rewrite proxy

## 7. ทดสอบ

หน่วยทดสอบ backend: อิมเมจ production ไม่คัดลอกโฟลเดอร์ `tests/` (ดู `.dockerignore`) — คัดลอกเข้าคอนเทนเนอร์แล้วติดตั้ง pytest:

```bash
docker cp app/backend/tests tor-app-backend-1:/app/tests
docker compose -p tor-app --env-file .env exec -u root backend pip install pytest pytest-asyncio hypothesis
docker compose -p tor-app --env-file .env exec -u root backend python -m pytest tests/test_wizard_payload.py tests/test_slash_redirects.py tests/test_lm_studio_provider.py tests/test_config_timeout.py tests/test_canonical_tor_sections.py tests/test_health.py tests/test_provider_factory.py tests/test_legal_rules.py tests/test_rule_engine.py -q --tb=short
```

บนโฮสต์ (แนะนำ): จาก `app/backend`

```bash
python -m pytest tests -q --tb=short --cov=app --cov-report=term --cov-report=html
```

ชุด `test_live_lm_studio.py` ยิง LM Studio ที่พอร์ต 1234 จริง — ถ้าเซิร์ฟเวอร์ไม่เปิด เทสต์ชุดนี้จะล้มพร้อมข้อความชัด ไม่ข้ามเงียบ

หน่วยทดสอบ frontend (บนโฮสต์):

```bash
cd app/frontend
npm test -- --run
```

E2E แบบเห็นเบราว์เซอร์ (สแตก Docker ต้องขึ้นแล้วที่ http://localhost:3000):

```bash
cd app/frontend
npm run test:e2e:headed
```

โหมด UI ของ Playwright: `npm run test:e2e:ui`

ถ่ายภาพรายงาน coverage (ต้องมี htmlcov ที่พอร์ต 8765/8766/8767): `npm run test:e2e:reports`  
ถ่ายภาพหน้าจอเพิ่มสำหรับคู่มือผู้ใช้: `npm run test:e2e:guide`  
ไฟล์ `e2e/reports.spec.ts` และ `e2e/guide-shots.spec.ts` **ไม่ถูกรวม**ใน `test:e2e` ปกติ จึงไม่มีเคสข้ามในชุดหลัก

หลังแก้ UI ให้ rebuild อิมเมจ frontend ก่อนรัน E2E — Playwright ยิงไปที่คอนเทนเนอร์ ไม่ใช่ `next dev`

ตรวจล่าสุด (**25 ส.ค. 2026** · v0.2.4) กับสแตก Docker (`tor-app` + Mongo + Neo4j) — headed เดิน live Phase 0–4 + แชท + ตรวจ TOR; mock specs ถูกข้ามเมื่อ `HEADED=1` — ภาพหน้าจออยู่ใน `discussions/test-evidence/` อธิบายทีละขั้นใน `13-USER_GUIDELINE.md` และจับคู่เคสเทสต์ใน `18-TEST_EVIDENCE.md`

ถ่ายภาพหน้าจอเพิ่มสำหรับคู่มือ: `npm run test:e2e:guide` (`e2e/guide-shots.spec.ts` ไม่รวมในชุด E2E หลัก)

![Playwright 17 passed](test-evidence/15-playwright-report.png)

| ชุด | ผล |
|-----|-----|
| pytest ไม่รวม `live_llm` | **1557 ผ่าน** / **3 ข้าม** / ครอบคลุม **86%** ของ `app/` (ตัด `seed_*` / `main`) |
| Vitest coverage | **192 ผ่าน** / 45 ไฟล์ · statements **81.26%** · lines **83.41%** |
| Playwright headed (แอป) | **16 ผ่าน** / **3 ข้าม** / 0 ล้ม (25 ส.ค. 2026 · ~20.5 นาที · live Phase 0–4) + guide **3** |
| Guide screenshots | **3 ผ่าน** (`test:e2e:guide` headed · รีเฟรช PNG ใน `test-evidence/`) |
| HTTP | `http://localhost:3000/` และ `http://localhost:4000/health` = **healthy** |

![Backend coverage 84%](test-evidence/13-backend-coverage.png)

![Frontend coverage 86.51%](test-evidence/14-frontend-coverage.png)

รอบนี้แก้ pgvector จริง: คอลัมน์ `metadata` ชนกับ `Table.metadata` ทำให้ upsert ฝังเวกเตอร์ไม่ได้ และ `search()` ล้มตอนสร้าง SQL — ตอนนี้ insert ใช้ `__table__` / `excluded["metadata"]` และ `Vector.cosine_distance` `seed_kb` ข้าม bind-mount ที่อ่านไม่ได้ (Errno 5) และรองรับไฟล์ชื่อสั้น + sidecar `.kbname` เพราะชื่อไทยยาวเกิน NAME_MAX ของ Linux Gemma 4 ใช้ reasoning tokens — `LMStudioLocalProvider` ตั้ง `max_tokens` เริ่มต้น 4096

อย่าส่ง `POSTGRES_HOST=127.0.0.1` ในเชลล์เดียวกับ `docker compose` — Compose จะทับ `.env` แล้ว backend หา postgres ไม่เจอ `python -m app.seed_kb` ในคอนเทนเนอร์ยังอ่าน `/knowledge-base` ไม่ได้ถ้า bind-mount โฟลเดอร์ไทยพัง: คัดลอกไฟล์ชื่อสั้นไป `/tmp/kb-linux-seed` แล้ว `KNOWLEDGE_BASE_DIR=/tmp/kb-linux-seed python -m app.seed_kb`

รอบนี้เพิ่มตัวเลือก Local vs Cloud ในหน้าผู้ดูแล ค่าเริ่มต้นยังเป็น on-prem (Gemma + EmbeddingGemma-300M) และการบันทึกมีผลทันทีโดยไม่ต้องรีสตาร์ท backend

คำเตือนใน Problems ของ Cursor มักเป็นหนึ่งในสามอย่างนี้ — ส่วนใหญ่ **ไม่ใช่บั๊กในแอปที่รันอยู่**:

1. **พาธ `frontend/...` หรือ `backend/...` ที่ราก** — โฟลเดอร์เหล่านี้ **ไม่มีในดิสก์**. โค้ดจริงอยู่ที่ `app/frontend` และ `app/backend`. ปิดแท็บที่พาธไม่มีคำว่า `app/` แล้วกด **Developer: Reload Window**. TypeScript → **Use Workspace Version**.
2. **การตั้งค่า IDE** — `.vscode/settings.json` ข้ามเฉพาะ `frontend/**` และ `backend/**` ที่ราก (อย่าใช้ `**/frontend/**` เพราะจะไปข้าม `app/frontend` ด้วย). `tsconfig.json` ที่รากชี้ไฟล์เดียว (`.vscode/tsconfig-placeholder.ts`) เพื่อไม่ให้ TS18002 และไม่ให้ language service ไป infer โปรเจกต์จากพาธราก. `sonar-project.properties` ใช้ `sonar.sources=app/frontend/src,app/backend/app` (ไม่สแกน `e2e/`). สเปก Playwright อยู่นอก `app/frontend/tsconfig.json` — เปิด `app/frontend/e2e/tsconfig.json` (`types: ["node"]`) และ `import { Buffer } from "node:buffer"` เพื่อไม่ให้ TS2580 เมื่อพิมพ์ `Buffer.from` ในอัปโหลด E2E.
3. **`documents/extract-scripts/**`** — สคริปต์วิจัย ไม่ได้ถูก Docker รัน — ถูก exclude จาก SonarLint / search.

อย่าใส่ `"ignoreDeprecations": "6.0"` ใน `app/frontend/tsconfig.json`. อย่าเปลี่ยน `[0-9]` เป็น `\\d` ในกฎรูปแบบ (Python `\\d` ตรงกับเลขไทย).

ซอร์สที่รันจริงอยู่ที่ `app/frontend` และ `app/backend` เท่านั้น.

## 8. โครงสร้างโฟลเดอร์ที่เกี่ยวกับรันไทม์

| เส้นทาง | บทบาท |
|---------|--------|
| `docker-compose.yml` | สแตกที่รากรีโป (frontend, backend, postgres, mongo, neo4j, redis, minio) |
| `app/frontend` | Next.js 14 |
| `app/backend` | FastAPI |
| `documents/sources/` | PDF กฎหมาย/คู่มือต้นฉบับ — คลังใช้งานผ่าน `seed_raw_docs` |
| `documents/knowledge-base` | extracts งานวิจัย (ไม่ใช่คลัง RAG หลักหลังรีเซ็ตรอบนี้) |
| `.env` | ความลับและโมเดล (ไม่ commit) |

อย่าวางซอร์สแอปหรือเมล็ด RAG ที่รากรีโป — ดู `.cursor/rules/repo-layout.mdc`

## หยุดและลบ

```bash
docker compose -p tor-app --env-file .env down      # เก็บ volume
docker compose -p tor-app --env-file .env down -v   # ลบข้อมูลด้วย
```
