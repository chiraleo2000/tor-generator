# MCP RAG — โครงต่อยอดคลังภายนอก

แบ็กเอนด์เรียกเครื่องมือ MCP `retrieve` ผ่าน JSON-RPC 2.0 บน HTTP  
ไม่ใช่ `DEPLOYMENT_MODE=hybrid` — โมเดลที่ตอบยังเป็น Bedrock / Local ตามโหมดแอป

| ไฟล์ | บทบาท |
|------|--------|
| `rag-sources.yaml` | รายการเซิร์ฟเวอร์ (ค่าเริ่มต้น `enabled: false`) |
| `servers/retrieve_stub.py` | สตับ HTTP สำหรับพัฒนา (คืนชิ้นข้อความจำลอง) |
| `app/backend/app/rag/mcp_rag.py` | ไคลเอนต์ในแอป |

มอบหมายทีม: [Discussions/30-DEV-ASSIGNMENT-MCP-AND-AWS.md](../../../Discussions/30-DEV-ASSIGNMENT-MCP-AND-AWS.md)
