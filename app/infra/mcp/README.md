# MCP RAG — โครงต่อยอดคลังภายนอก

แบ็กเอนด์เรียกเครื่องมือ MCP `retrieve` ผ่าน JSON-RPC 2.0 บน HTTP  
ไม่ใช่ `DEPLOYMENT_MODE=hybrid` — โมเดลที่ตอบยังเป็น Bedrock / Local ตามโหมดแอป

| ไฟล์ | บทบาท |
|------|--------|
| `rag-sources.yaml` | รายการเซิร์ฟเวอร์สำหรับ dev/bind-mount (ค่าเริ่มต้น `enabled: false`) |
| `servers.example.json` | วางใน Secrets Manager เป็น `MCP_RAG_SERVERS_JSON` บน ECS |
| `servers/retrieve_stub.py` | สตับ HTTP สำหรับพัฒนา (คืนชิ้นข้อความจำลอง) |
| `servers/pageindex_adapter.py` | แปลง `POST /v1/retrieve` → PageIndex `/api/search` |
| `app/backend/app/rag/mcp_rag.py` | ไคลเอนต์ในแอป |

Compose ท้องถิ่น: ส่ง `MCP_RAG_*` เข้า backend และ bind-mount `rag-sources.yaml`  
สตับ: `docker compose --profile mcp-stub up` หรือรัน stub บนโฮสต์แล้วใช้ `http://host.docker.internal:8765`  
ECS: ใช้ JSON ใน Secrets เป็น `MCP_RAG_SERVERS_JSON` ไม่ใช้ `MCP_RAG_CONFIG_PATH`

มอบหมายทีม: [Discussions/30-DEV-ASSIGNMENT-MCP-AND-AWS.md](../../../Discussions/30-DEV-ASSIGNMENT-MCP-AND-AWS.md)  
ขึ้น Amazon (ECS/Bedrock): [Discussions/31-MCP-RAG-AWS-QUICKSTART.md](../../../Discussions/31-MCP-RAG-AWS-QUICKSTART.md)  
Amazon Quick (assistant connectors, not QuickSight): [Discussions/32-AMAZON-QUICK.md](../../../Discussions/32-AMAZON-QUICK.md) · sidecar `app/infra/quick/`
