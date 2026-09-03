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
| Compose profile `amazon-quick` | Sidecar on port **8767** |
| `app/infra/mcp/servers/retrieve_stub.py` | Existing TOR RAG source C on **8765**, now also speaks `initialize` / `tools/list` |

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

1. `docker compose --profile amazon-quick up -d amazon-quick`
2. In Amazon Quick: Connectors → MCP → endpoint `https://<public-or-vpc-host>:8767/mcp` (or `/`). Auth: none for the stub.
3. Or import `app/infra/quick/openapi-tor.json`.
4. Share the integration with the procurement team. Ask Quick to “retrieve procurement rules for performance bonds” and confirm a snippet comes back.

Replace the stub with a private retrieve that calls TOR hybrid RAG only after TLS and network allow-lists are in place. Keep that call under 60 seconds.
