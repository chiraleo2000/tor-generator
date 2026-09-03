# Amazon Quick connector (not QuickSight)

Local sidecar so [Amazon Quick](https://aws.amazon.com/quick/) can call this TOR app’s knowledge retrieve over **remote MCP** or **OpenAPI 3.0**.

This is not the AWS cloud install in `Discussions/31-MCP-RAG-AWS-QUICKSTART.md` (ECS + Bedrock + Secrets). Quick is the workplace AI assistant; it talks to *this* HTTP server.

## Constraints (from AWS docs)

- Remote MCP only (no stdio). HTTP JSON-RPC on `/` or `/mcp`.
- `tools/list` `inputSchema.required` must be a **Draft 7 array**, not a boolean on each property.
- Tool calls time out at **60 seconds**.
- At most **100** tools; the list is static after Quick registers the connector.
- OpenAPI: JSON 3.0+, no `type: array` in request/response schemas, every operation needs `operationId` + descriptions.

## Run locally

```bash
docker compose --profile amazon-quick up amazon-quick
# or: python app/infra/quick/mcp_server.py
```

- Health: `GET http://127.0.0.1:8767/health`
- REST retrieve: `POST http://127.0.0.1:8767/retrieve` `{"query":"..."}`
- MCP: `POST http://127.0.0.1:8767/mcp`

The TOR backend’s own MCP RAG client still uses `retrieve_stub.py` on **8765**. Point Quick at **8767** so the two do not share a port.

## Register in Amazon Quick

1. Enterprise subscription. Private servers need a Quick VPC connection; OAuth (if any) must stay on the public internet.
2. **Connectors → Create for your team → Model Context Protocol (MCP)**  
   Endpoint: public HTTPS URL of this sidecar (or VPC DNS). Auth: none for the local stub.
3. Or **OpenAPI Specification** and import `openapi-tor.json`.
4. After you change tools, delete and recreate the connector (tool list is frozen at register time).

Production: put TLS in front, keep retrieve under 60s, and optionally replace the stub body with a call to TOR `hybrid_retrieve` on the private network.
