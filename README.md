# TOR Generator

ระบบร่างและตรวจสอบ TOR ภาครัฐ (Terms of Reference) ตาม พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560

**GitHub Pages คือ UI จำลองเท่านั้น** — เปิดจาก `index.html` ที่ root ของรีโป ให้หน้าตาและเมนูตรงกับแอปปัจจุบัน (แดชบอร์ดภาษาไทย, 5 Phase, 13 หมวด, ร่างด้วย AI, ตรวจสอบ, การตั้งค่า AI) แต่ไม่เรียก API/LLM จริง และ**ไม่ได้**ใช้ `discussions/06-UXUI-Mockup.html`

แอปที่ใช้งานจริงอยู่ที่ `app/` รันด้วย Docker ตามด้านล่าง

This repository is split into **three trees**. Put new files in the matching folder — do not drop PDFs, notes, or app code at the repo root (exception: `index.html` + `.nojekyll` for GitHub Pages).

| Folder | What belongs here |
|--------|-------------------|
| **[app/](app/)** | The web application: Next.js UI, FastAPI backend, Docker image extras |
| **[discussions/](discussions/)** | Design notes, architecture write-ups, API/UX docs (not loaded at runtime) |
| **[documents/](documents/)** | Laws, PDFs, RAG corpus, TOR templates, research extracts, source packs |

Related (not the web app):

| Path | Role |
|------|------|
| [skills/](skills/) | Offline Claude / ChatGPT / Gemini / Hermes skill packs |
| [.kiro/](.kiro/) | Kiro spec and in-IDE skills — see [SKILLS.md](SKILLS.md) |
| `docker-compose.yml` | Runs **app/** with a read-only mount of `documents/knowledge-base` |

Canonical TOR keys are `s1`–`s13`. Shared definition: `app/backend/app/domain/tor_sections.py` and `app/frontend/src/lib/tor-sections.ts`.

## Quick start (app)

```bash
cp .env.example .env
docker compose up --build
```

- UI: http://localhost:3000
- API: http://localhost:4000/api/v1
- Health: http://localhost:4000/health

Seed demo users, templates, and knowledge base:

```bash
docker compose exec backend python -m app.seed_db
docker compose exec backend python -m app.seed_kb
```

Demo logins (after seed): `admin@example.go.th`, `officer@example.go.th`, `reviewer@example.go.th` — password `Passw0rd!`.

Local backend (without Compose):

```bash
cd app/backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 4000
```

Local frontend:

```bash
cd app/frontend
npm install
# NEXT_PUBLIC_API_URL=/api/v1 uses the Next.js rewrite to localhost:4000
npm run dev
```

## Deployment modes (Req 2)

Set `DEPLOYMENT_MODE` in `.env`:

| Mode | LLM | Embedding | Vector store |
|------|-----|-----------|----------------|
| `on_prem` | LM Studio / Ollama / llama.cpp (`LLM_PROVIDER`) | EmbeddingGemma-300M local (`EMBEDDING_PROVIDER=local`) | pgvector |
| `cloud` | Claude / OpenAI / Gemini | OpenAI or Gemini embeddings (768-d) | pgvector or Qdrant |
| `hybrid` | `LLM_PROVIDER` + `EMBEDDING_PROVIDER` + `VECTOR_STORE_PROVIDER` | same | same |

Operator docs: [discussions/13-USER_GUIDELINE.md](discussions/13-USER_GUIDELINE.md), [14-INSTALLATION.md](discussions/14-INSTALLATION.md), [15-APPLICATION_DESCRIPTION.md](discussions/15-APPLICATION_DESCRIPTION.md), [16-BACKEND_ARCHITECTURE.md](discussions/16-BACKEND_ARCHITECTURE.md), [17-FRONTEND_ARCHITECTURE.md](discussions/17-FRONTEND_ARCHITECTURE.md).

### LM Studio (on-prem)

1. Load chat **google/gemma-4-e4b** and embeddings **text-embedding-embeddinggemma-300m** (768-d).
2. Start the OpenAI-compatible server (default `http://127.0.0.1:1234/v1`).
3. From Docker, the backend uses `http://host.docker.internal:1234/v1`.
4. If the LLM is unreachable the API returns a structured error. No project data is sent off-host in `on_prem`.
5. Admins can switch to Ollama, llama.cpp, or cloud Claude/OpenAI/Gemini from **การตั้งค่า AI** (restart backend after save).

## Browser API URL

The browser cannot resolve the Docker hostname `backend`. Compose builds the frontend with `NEXT_PUBLIC_API_URL=/api/v1` and Next.js rewrites `/api/v1/*` to `http://backend:4000/api/v1` inside the container (or `http://localhost:4000` in local `next dev`).

## Compose smoke (Req 1)

Health checks use 30s interval, 3 retries, 40s start period. After `docker compose up --build`:

1. `curl http://localhost:4000/health` and open http://localhost:3000
2. Seed users/templates/KB (`python -m app.seed_db` then `python -m app.seed_kb`)
3. Log in as `officer@example.go.th` / `Passw0rd!` and create a project (browser must reach `/api/v1` via the Next.js rewrite)
4. Optional drafting call if LM Studio is running; otherwise AI draft returns a structured error ≤10s

Playwright (needs a running UI): `cd app/frontend && npm i && npx playwright install chromium && E2E=1 npm run test:e2e`

Deferred: dual vector-store daily sync and Kubernetes/OCR HPA.
