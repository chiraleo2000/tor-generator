# Documents — data, corpus, and research files

Legal PDFs, extracts, RAG seed, templates, and research pipelines. **Do not copy this tree into `app/frontend` or `app/backend`.**

| Path | Role |
|------|------|
| `knowledge-base/` | RAG seed (markdown + JSON extracts). Compose mounts this read-only. |
| `templates/` | Industry TOR markdown templates |
| `sources/` | Original Thai source packs, sample files, and root manuals (PDF/DOCX) — omitted from GitHub (too large); keep locally |
| `research/` | `analysis/`, `raw_text/`, `zip_output/` — extraction corpus |
| `extract-scripts/` | PDF/DOCX/TOR extract helpers (not the FastAPI seed CLIs) |
| `prompts/` | Offline writing prompts for Claude/ChatGPT |
| `docs/` | Extra platform skill instructions |

App seed CLIs stay in `app/backend/` (`python -m app.seed_db` / `python -m app.seed_kb`).
