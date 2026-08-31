# MCP RAG — โครงต่อยอดคลังภายนอก

แบ็กเอนด์เรียกเครื่องมือ MCP `retrieve` ผ่าน JSON-RPC 2.0 บน HTTP  
ไม่ใช่ `DEPLOYMENT_MODE=hybrid` — โมเดลที่ตอบยังเป็น Bedrock / Local ตามโหมดแอป

| ไฟล์ | บทบาท |
|------|--------|
| `rag-sources.yaml` | รายการเซิร์ฟเวอร์สำหรับ dev/bind-mount (ค่าเริ่มต้น `enabled: false`) |
| `servers.example.json` | วางใน Secrets Manager เป็น `MCP_RAG_SERVERS_JSON` บน ECS |
| `servers/retrieve_stub.py` | สตับ HTTP สำหรับพัฒนา (คืนชิ้นข้อความจำลอง) |
| `app/backend/app/rag/mcp_rag.py` | ไคลเอนต์ในแอป |

อิมเมจ backend สร้างจาก `app/backend` จึง**ไม่มี**ไฟล์ในโฟลเดอร์นี้ — บน ECS ใช้ JSON ใน env/secrets ไม่ใช้ `MCP_RAG_CONFIG_PATH`

มอบหมายทีม: [Discussions/30-DEV-ASSIGNMENT-MCP-AND-AWS.md](../../../Discussions/30-DEV-ASSIGNMENT-MCP-AND-AWS.md)
