# การติดตั้งและรันระบบ TOR

คู่มือนี้สำหรับสแตกที่รันจริง: Next.js + FastAPI ใน Docker และ LLM ที่ LM Studio บนเครื่องโฮสต์ (ค่าเริ่มต้น) หรือคลาวด์เมื่อผู้ดูแลเปิดใช้

แอปปัจจุบันเป็นกระบวนการร่าง **5 Phase (0–4)** ไม่ใช่วิซาร์ด 8 ขั้น และไม่ใช่ไฟล์ HTML ต้นแบบใน `06-UXUI-Mockup.html` — ไฟล์นั้นเป็นแบบออกแบบเท่านั้น

ดูคำอธิบายแอปที่ `15-APPLICATION_DESCRIPTION.md` และคู่มือผู้ใช้ที่ `13-USER_GUIDELINE.md`

## สิ่งที่ต้องมี

- Docker Desktop (Windows/macOS) หรือ Docker Engine + Compose
- สำหรับโหมดในเครื่อง: เซิร์ฟเวอร์ OpenAI-compatible ที่ `http://127.0.0.1:1234` (LM Studio) พร้อม
  - Chat: **google/gemma-4-e4b**
  - Embeddings: **text-embedding-embeddinggemma-300m** (768 มิติ)
- หรือ Ollama ที่พอร์ต **11434** / llama.cpp ที่พอร์ต **8080** (เลือกได้จากหน้าการตั้งค่า AI)
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
LM_STUDIO_BASE_URL=http://host.docker.internal:1234/v1
LM_STUDIO_MODEL=google/gemma-4-e4b
LM_STUDIO_EMBEDDING_MODEL=text-embedding-embeddinggemma-300m
LM_STUDIO_TIMEOUT=180
OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
LLAMA_CPP_BASE_URL=http://host.docker.internal:8080/v1
```

คีย์คลาวด์ (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`) ว่างได้ถ้าใช้เฉพาะโมเดลท้องถิ่น — Compose ส่งค่าผ่านไปถ้ามี แต่ไม่บังคับว่างแล้ว คีย์ที่บันทึกจากหน้าผู้ดูแลอยู่ใน Postgres และมีผลทันทีหลังกดบันทึก (ไม่ต้องรีสตาร์ท backend)

## 2. เปิด LM Studio (โหมดในเครื่อง)

1. Start server ที่พอร์ต **1234**
2. Load **google/gemma-4-e4b** สำหรับแชท
3. Load **text-embedding-embeddinggemma-300m** สำหรับ embeddings
4. ทดสอบในเบราว์เซอร์หรือด้วย `GET http://127.0.0.1:1234/v1/models`

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
| redis | 6379 |
| minio | 9000 / 9001 |

รอจนสถานะ healthy แล้วเปิด http://localhost:3000

หลังย้ายมิติ embeddings เป็น 768 backend จะรัน Alembic เมื่อสตาร์ท แล้วต้องฝังเวกเตอร์ใหม่:

```bash
docker compose -p tor-app --env-file .env exec backend python -m app.seed_kb
```

## 4. ใส่ข้อมูลเริ่มต้น

```bash
docker compose -p tor-app --env-file .env exec backend python -m app.seed_db
```

บัญชีทดลอง: `officer@example.go.th` / `admin@example.go.th` / `reviewer@example.go.th` รหัส `Passw0rd!`

ใส่ฐานความรู้ (ถ้าเมานต์ `documents/knowledge-base` สำเร็จ) — รวม `*_tor_extract.json`, ชุด `*_combined.json` และ `04-decision-rules`:

```bash
docker compose -p tor-app --env-file .env exec backend python -m app.seed_kb
```

บน Windows ชื่อโฟลเดอร์ไทยอาจทำให้ bind-mount ล้ม (Errno 5) — คัดลอกไฟล์ชื่อสั้น (`*_combined.json`, `04-decision-rules/*.json`) เข้าคอนเทนเนอร์ที่ `/tmp/kb-linux-seed` แล้ว:

```bash
docker compose -p tor-app --env-file .env exec -e KNOWLEDGE_BASE_DIR=/tmp/kb-linux-seed backend python -m app.seed_kb
```

ชื่อไทยยาวเกิน NAME_MAX ให้ใช้ sidecar `.kbname` คู่กับชื่อสั้น `e01_tor_extract.json` แอปยังร่าง TOR ได้โดยไม่ต้องมี RAG ครบ

## 5. สลับ Local / Cloud จากหน้าผู้ดูแล

เข้าสู่ระบบด้วยบัญชี admin แล้วเปิด **การตั้งค่า AI**:

- รันในเครื่อง: LM Studio / Ollama / llama.cpp เท่านั้น, URL, ชื่อโมเดลแชทและ embeddings, timeout
- คลาวด์: Claude / OpenAI / Gemini เท่านั้น + API key (ใส่ในหน้านี้ได้ ไม่ต้องใส่ใน `.env`)
- ผสม: เลือกแชท/embeddings/คลังเวกเตอร์ทีละส่วน (คลาวด์ต้องมีคีย์)
- คลังเวกเตอร์: `pgvector` หรือ `qdrant` (ใช้ได้ทั้งโหมดในเครื่อง)
- **ทดสอบการเชื่อมต่อ** ไม่ต้องรีสตาร์ท
- **บันทึก** มีผลทันทีในกระบวนการ — ไม่ต้อง `restart backend`

ถ้าเปลี่ยนผู้ให้บริการ embeddings หรือชื่อโมเดลฝังตัว ต้อง `python -m app.seed_kb` อีกครั้ง (หน้าผู้ดูแลจะเตือน `reingest_required`)

## 6. ตรวจสุขภาพ

```bash
curl.exe http://localhost:4000/health
curl.exe http://localhost:3000
```

Frontend พร็อกซี `/api/v1/*` ไปที่ backend ภายใน Docker (`BACKEND_INTERNAL_URL=http://backend:4000/api/v1`)

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

ตรวจล่าสุด (**18 ส.ค. 2026 ~10:58 น.**) กับสแตก Docker (`tor-app`) + LM Studio ที่พอร์ต 1234 — ภาพหน้าจออยู่ใน `discussions/test-evidence/` อธิบายทีละขั้นใน `13-USER_GUIDELINE.md` และจับคู่เคสเทสต์ใน `18-TEST_EVIDENCE.md`

ถ่ายภาพหน้าจอเพิ่มสำหรับคู่มือ: `npm run test:e2e:guide` (`e2e/guide-shots.spec.ts` ไม่รวมในชุด E2E หลัก)

![Playwright 13 passed](test-evidence/15-playwright-report.png)

| ชุด | ผล |
|-----|-----|
| pytest รวม live LM Studio | **1339 ผ่าน** / ครอบคลุม **92%** ของ `app/` (ตัด `seed_db` / `seed_kb` / `main`) |
| Vitest | **104 ผ่าน** / ครอบคลุม **92.47%** statements ของ lib+stores+หน้าตั้งค่า AI |
| Playwright headed (แอป) | **13 ผ่าน** / 0 ล้ม — ฟอร์มสร้างโครงการ, เดิน Phase 0–4, ร่างด้วย AI (Gemma), Admin AI ping LM Studio |
| Playwright รายงาน coverage | **3 ผ่าน** (`test:e2e:reports` ที่พอร์ต 8765/8766/8767) |
| การตั้งค่า AI | โหมดในเครื่อง = LM Studio/Ollama/llama.cpp; โหมดคลาวด์ = Claude/OpenAI/Gemini + คีย์ในหน้า UI; บันทึกมีผลทันที |
| HTTP | `http://localhost:3000/` และ `http://localhost:4000/health` = **healthy** |

![Backend coverage 92%](test-evidence/13-backend-coverage.png)

![Frontend coverage 92.47%](test-evidence/14-frontend-coverage.png)

รอบนี้แก้ pgvector จริง: คอลัมน์ `metadata` ชนกับ `Table.metadata` ทำให้ upsert ฝังเวกเตอร์ไม่ได้ และ `search()` ล้มตอนสร้าง SQL — ตอนนี้ insert ใช้ `__table__` / `excluded["metadata"]` และ `Vector.cosine_distance` `seed_kb` ข้าม bind-mount ที่อ่านไม่ได้ (Errno 5) และรองรับไฟล์ชื่อสั้น + sidecar `.kbname` เพราะชื่อไทยยาวเกิน NAME_MAX ของ Linux Gemma 4 ใช้ reasoning tokens — `LMStudioLocalProvider` ตั้ง `max_tokens` เริ่มต้น 4096

อย่าส่ง `POSTGRES_HOST=127.0.0.1` ในเชลล์เดียวกับ `docker compose` — Compose จะทับ `.env` แล้ว backend หา postgres ไม่เจอ `python -m app.seed_kb` ในคอนเทนเนอร์ยังอ่าน `/knowledge-base` ไม่ได้ถ้า bind-mount โฟลเดอร์ไทยพัง: คัดลอกไฟล์ชื่อสั้นไป `/tmp/kb-linux-seed` แล้ว `KNOWLEDGE_BASE_DIR=/tmp/kb-linux-seed python -m app.seed_kb`

รอบนี้เพิ่มตัวเลือก Local vs Cloud ในหน้าผู้ดูแล ค่าเริ่มต้นยังเป็น on-prem (Gemma + EmbeddingGemma-300M) และการบันทึกมีผลทันทีโดยไม่ต้องรีสตาร์ท backend

คำเตือนใน Problems ของ Cursor มักเป็นหนึ่งในสามอย่างนี้ — ส่วนใหญ่ **ไม่ใช่บั๊กในแอปที่รันอยู่**:

1. **พาธ `frontend/...` หรือ `backend/...` ที่ราก** — โฟลเดอร์เหล่านี้ **ไม่มีในดิสก์**. โค้ดจริงอยู่ที่ `app/frontend` และ `app/backend`. ปิดแท็บที่พาธไม่มีคำว่า `app/` แล้วกด **Developer: Reload Window**. TypeScript → **Use Workspace Version**.
2. **การตั้งค่า IDE** — `.vscode/settings.json` ข้ามเฉพาะ `frontend/**` และ `backend/**` ที่ราก (อย่าใช้ `**/frontend/**` เพราะจะไปข้าม `app/frontend` ด้วย). `tsconfig.json` ที่รากชี้ไฟล์เดียว (`.vscode/tsconfig-placeholder.ts`) เพื่อไม่ให้ TS18002 และไม่ให้ language service ไป infer โปรเจกต์จากพาธราก. `.cursorignore` และ `sonar-project.properties` ใช้ `sonar.sources=app`.
3. **`documents/extract-scripts/**`** — สคริปต์วิจัย ไม่ได้ถูก Docker รัน — ถูก exclude จาก SonarLint / search.

อย่าใส่ `"ignoreDeprecations": "6.0"` ใน `app/frontend/tsconfig.json`. อย่าเปลี่ยน `[0-9]` เป็น `\\d` ในกฎรูปแบบ (Python `\\d` ตรงกับเลขไทย).

ซอร์สที่รันจริงอยู่ที่ `app/frontend` และ `app/backend` เท่านั้น.

## 8. โครงสร้างโฟลเดอร์ที่เกี่ยวกับรันไทม์

| เส้นทาง | บทบาท |
|---------|--------|
| `docker-compose.yml` | สแตกที่รากรีโป |
| `app/frontend` | Next.js 14 |
| `app/backend` | FastAPI |
| `documents/knowledge-base` | เมล็ด RAG (อ่านอย่างเดียวในคอนเทนเนอร์) |
| `.env` | ความลับและโมเดล (ไม่ commit) |

อย่าวางซอร์สแอปหรือเมล็ด RAG ที่รากรีโป — ดู `.cursor/rules/repo-layout.mdc`

## หยุดและลบ

```bash
docker compose -p tor-app --env-file .env down      # เก็บ volume
docker compose -p tor-app --env-file .env down -v   # ลบข้อมูลด้วย
```
