# MCP RAG — แหล่ง retrieve เพิ่ม (ไม่ใช่โมเดลตอบ)

แบ็กเอนด์เรียกเครื่องมือ MCP `retrieve` ผ่าน JSON-RPC 2.0 บน HTTP  
ไม่ใช่ `DEPLOYMENT_MODE=hybrid` — โมเดลที่ตอบยังเป็น LM Studio / Bedrock ตามโหมดแอป

| ไฟล์ | บทบาท |
|------|--------|
| `rag-sources.yaml` | รายการเซิร์ฟเวอร์สำหรับ Compose (`local-pgvector-mcp` เปิดในเครื่อง) |
| `servers.example.json` | วางใน Secrets Manager เป็น `MCP_RAG_SERVERS_JSON` บน ECS |
| `app/backend/app/mcp_retrieve_server.py` | เซิร์ฟเวอร์ MCP ท้องถิ่น ค้น pgvector |
| `servers/retrieve_stub.py` | สตับ HTTP คืนข้อความจำลอง (อย่าเปิดสำหรับคำตอบกฎหมาย) |
| `servers/pageindex_adapter.py` | แปลง `POST /v1/retrieve` → PageIndex `/api/search` |
| `app/backend/app/rag/mcp_rag.py` | ไคลเอนต์ในแอป |

Compose ท้องถิ่น: `MCP_RAG_ENABLED=true` และเซอร์วิส `mcp-rag` (พอร์ต 8765)  
YAML ชี้ `http://mcp-rag:8765` — ค้นคลังเดียวกับ `documents/sources` → pgvector  
สตับจำลอง: `docker compose --profile mcp-stub up` ที่ `http://mcp-stub:8765` (โฮสต์แมป 8766) — **ห้าม enabled: true**  
PageIndex Custom RAG: `CUSTOM_RAG_BASE_URL=http://pageindex:8000/api/search`  
ECS: ใช้ JSON ใน Secrets เป็น `MCP_RAG_SERVERS_JSON` ไม่ใช้ `MCP_RAG_CONFIG_PATH`

มอบหมายทีม: [Discussions/30-DEV-ASSIGNMENT-MCP-AND-AWS.md](../../../Discussions/30-DEV-ASSIGNMENT-MCP-AND-AWS.md)  
ขึ้น Amazon (ECS/Bedrock): [Discussions/31-MCP-RAG-AWS-QUICKSTART.md](../../../Discussions/31-MCP-RAG-AWS-QUICKSTART.md)  
Amazon Quick (assistant connectors, not QuickSight): [Discussions/32-AMAZON-QUICK.md](../../../Discussions/32-AMAZON-QUICK.md) · sidecar `app/infra/quick/`
