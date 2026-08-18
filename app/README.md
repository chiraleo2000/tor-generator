# App — TOR drafting / review web stack

This folder is the **only** runtime application. Do not put research PDFs, legal extracts, or design notes here.

| Path | Role |
|------|------|
| `frontend/` | Next.js 14 UI (8-step wizard, admin, help, standalone review) |
| `backend/` | FastAPI + LangGraph + rule engine + RAG |
| `docker/` | Extra Docker assets (placeholder) |

Orchestration lives one level up: `../docker-compose.yml`, `../.env.example`.

The RAG seed is **not** inside this folder. Compose mounts `../documents/knowledge-base` into the backend as `/knowledge-base`.

## Local commands

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

Seed (from `backend/`): `python -m app.seed_db` then `python -m app.seed_kb`.
