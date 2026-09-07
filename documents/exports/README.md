# Dataset exports

Large zip archives of the mandatory RAG corpus and Amazon Quick / MCP connector files are built on demand (not committed — see root `.gitignore`).

## Build

From the repository root (PowerShell):

```powershell
powershell -File documents/exports/build-rag-mcp-zip.ps1
# or: python documents/exports/build_rag_mcp_zip.py --version 0.4.0
```

Output: `documents/exports/tor-rag-mcp-dataset-v0.4.0.zip`

## Contents

| Path inside zip | Source |
|-----------------|--------|
| `rag-pdfs/` | `documents/sources/การจัดซื้อจัดจ้าง/ข้อมูลดิบ/*.pdf` (live pgvector corpus) |
| `rag-json-chunks/` | Matching `documents/knowledge-base/*_tor_extract.json` |
| `mcp-amazon-quick/` | `app/infra/quick/*` (MCP server, OpenAPI, README) |
| `mcp-pgvector/` | `app/backend/app/mcp_retrieve_server.py` |
| `docs/` | `Discussions/32-AMAZON-QUICK.md` |
| `MANIFEST.txt` | File list and version stamp |
