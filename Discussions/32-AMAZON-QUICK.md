# 32 — Amazon Quick (workplace AI), not QuickSight

Product: [Amazon Quick](https://aws.amazon.com/quick/) — agentic assistant for research, automations, and connectors.

This is **not**:

- Amazon QuickSight (BI dashboards)
- The AWS *cloud install* of this TOR app (`DEPLOYMENT_MODE=cloud` + Bedrock + ECS) documented in [31](31-MCP-RAG-AWS-QUICKSTART.md)

Local GPU testing stays on **LM Studio** (`LLM_PROVIDER=lm_studio`, `EMBEDDING_PROVIDER=local`). Amazon Quick is a *second* client that can call the same knowledge retrieve over MCP or OpenAPI when the agency already uses Quick at work.

## What we ship in this repo

| Path | Role |
|------|------|
| `app/infra/quick/mcp_server.py` | Remote MCP (`initialize`, `tools/list` Draft 7, `tools/call`) + REST `/health` `/retrieve` |
| `app/infra/quick/openapi-tor.json` | OpenAPI 3.0 JSON for Quick’s OpenAPI connector (no array schemas) |
| `app/infra/quick/README.md` | Operator steps |
| `app/infra/quick/agents-skills/` | **Agents + Skills** สำหรับร่าง/ตรวจ TOR บน Quick (JSON + `SKILL.md`) — ดู [README](../app/infra/quick/agents-skills/README.md) |
| Compose profile `amazon-quick` | Sidecar on port **8767**; `QUICK_RAG_MCP_URL=http://mcp-rag:8765/mcp` → **real pgvector** |
| `app.mcp_retrieve_server` (`mcp-rag`) | Live retrieve from the same corpus TOR chat uses |
| `app/infra/mcp/servers/retrieve_stub.py` | Optional fake stub on **8766** (`mcp-stub` profile) |

### Agents & Skills (ร่าง / ตรวจ)

สะท้อน workflow แอป ([21](21-WORKFLOW_DRAFT_TOR.md), [22](22-WORKFLOW_REVIEW_TOR.md)):

| Artifact | ใช้เมื่อ |
|----------|---------|
| `agents/tor-draft-agent.json` | เดินครบ intake → compose |
| `agents/tor-review-agent.json` | ตรวจ TOR / Phase 4 |
| Skills `tor-draft-intake`, `tor-draft-compose`, `tor-review-compliance`, `tor-kb-retrieve` | Import `SKILL.md` ใน Quick Desktop → Agents & skills |

Quick เรียก MCP `retrieve` เท่านั้น — ไม่แทนที่การอนุมัติโครงการหรือ export DOCX/PDF ของเว็บแอป

สไตล์ร่าง (กันโครงร่างวิซาร์ดและคำอังกฤษ): อัปเดตใน `skill.json` / `SKILL.md` ของ `tor-draft-compose` และ `tor-review-compliance` เมื่อ 9 ก.ย. 2026 — เลขไทย, ห้าม `### history`, ห้าม Server/Cyber Attack/Digital Government, และระบุรูปแบบส่งออกของแอป (16pt / 1.0 / ขอบ 2.54/1.91 ซม.)

## Local vs Quick vs AWS cloud

| Mode | Chat / draft LLM | Embeddings | Who calls retrieve |
|------|------------------|------------|--------------------|
| On-prem dev | LM Studio Gemma | EmbeddingGemma 768-d | TOR backend hybrid RAG |
| Amazon Quick | Quick’s models | Quick’s stack | Quick → this MCP/OpenAPI sidecar |
| AWS cloud TOR | Bedrock | Bedrock or pgvector already seeded | TOR backend; optional same MCP JSON as [31](31-MCP-RAG-AWS-QUICKSTART.md) |

Do not set `LLM_PROVIDER=bedrock` for local Playwright. A hung Bedrock section used to wait **1800s**, so 13/13 never finished and evidence screenshots froze at 2/13.

## Quick MCP rules we coded for

From [MCP integration](https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html) and [OpenAPI integration](https://docs.aws.amazon.com/quick/latest/userguide/openapi-integration.html):

- Remote HTTP only (no stdio). Streaming HTTP preferred over SSE.
- `required` is an **array** of names (JSON Schema Draft 7).
- 60s tool timeout; max 100 tools; recreate the connector after tool changes.
- OpenAPI 3.0 JSON, ≤100 operations, **no array types** in schemas — `/retrieve` returns one object.
- Enterprise + optional VPC for private servers; OAuth endpoints must remain public.

## Register (ops)

1. Ensure `mcp-rag` is healthy (real pgvector) and LM Studio embeddings are loaded.
2. `docker compose --profile amazon-quick up -d amazon-quick`
3. Desktop Remote MCP: `http://127.0.0.1:8767/mcp` (team/cloud: `https://<public-or-vpc-host>:8767/mcp`). Auth: none unless `QUICK_MCP_AUTH_VALUE` is set.
4. Or import `app/infra/quick/openapi-tor.json`.
5. Ask Quick to retrieve “หลักประกันผลงาน” — expect a real `source_document` from the corpus (not `amazon-quick-mcp` stub text).

## Verification (7 ก.ย. 2026 บ่าย)

Live sidecar on `:8767` with Compose profile `amazon-quick`:

| Check | Result |
|-------|--------|
| `GET /health` | `status=ok` · `rag.mode=live` · `reachable=true` → `tor-mcp-pgvector` |
| `POST /retrieve` | HTTP 200 · real PDF source (~20k chars) — not stub |
| MCP `initialize` / `tools/list` / `tools/call retrieve` | `tor-amazon-quick` · tools retrieve,ping,get_health · live call OK |
| `pytest tests/test_amazon_quick.py` | **10 passed** |

Evidence log: `Discussions/test-evidence/_round-2026-09-07pm-amazon-quick.txt`

`retrieve` proxies to `mcp-rag` (`QUICK_RAG_MCP_URL`). Keep calls under 60 seconds. Cloud/team sharing still needs TLS (or Quick VPC) in front of 8767.
