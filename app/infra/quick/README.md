# Amazon Quick connector (not QuickSight)

Local sidecar so [Amazon Quick](https://aws.amazon.com/quick/) can call this TOR app’s knowledge retrieve over **remote MCP** or **OpenAPI 3.0**.

With Compose, `QUICK_RAG_MCP_URL=http://mcp-rag:8765/mcp` so `retrieve` uses the **same pgvector corpus** as TOR chat (not a fake stub). Unset that env only for offline unit tests.

This is not the AWS cloud install in `Discussions/31-MCP-RAG-AWS-QUICKSTART.md` (ECS + Bedrock + Secrets). Quick is the workplace AI assistant; it talks to *this* HTTP server on **8767**.

## Constraints (from AWS docs)

- Remote MCP only (no stdio). HTTP JSON-RPC on `/` or `/mcp`.
- `tools/list` `inputSchema.required` must be a **Draft 7 array**, not a boolean on each property.
- Tool calls time out at **60 seconds**.
- At most **100** tools; the list is static after Quick registers the connector.
- OpenAPI: JSON 3.0+, no `type: array` in request/response schemas, every operation needs `operationId` + descriptions.

## Run locally

```bash
docker compose up -d mcp-rag   # real pgvector retrieve
docker compose --profile amazon-quick up -d amazon-quick
# or host: set QUICK_RAG_MCP_URL=http://127.0.0.1:8765/mcp && python app/infra/quick/mcp_server.py
```

- Health: `GET http://127.0.0.1:8767/health` (includes `rag.reachable`)
- REST retrieve: `POST http://127.0.0.1:8767/retrieve` `{"query":"..."}`
- MCP: `POST http://127.0.0.1:8767/mcp`

Point Amazon Quick Desktop at **8767**. Service **mcp-rag** owns **8765** (pgvector). Optional fake stub is profile `mcp-stub` on **8766**.

## Register in Amazon Quick

1. Enterprise subscription. Private servers need a Quick VPC connection; OAuth (if any) must stay on the public internet.
2. **Connectors → Create for your team → Model Context Protocol (MCP)**  
   Endpoint: public HTTPS URL of this sidecar (or VPC DNS). Auth: none for the local stub.
3. Or **OpenAPI Specification** and import `openapi-tor.json`.
4. After you change tools, delete and recreate the connector (tool list is frozen at register time).
5. Import **Agents & Skills** from [`agents-skills/`](agents-skills/README.md) (`SKILL.md` + agent JSON) so Quick can draft/review TOR with the same phase logic as the web app.

Production: put TLS in front, keep retrieve under 60s, and optionally replace the stub body with a call to TOR `hybrid_retrieve` on the private network.
