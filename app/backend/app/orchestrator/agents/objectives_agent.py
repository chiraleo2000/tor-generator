"""Agent 2: Objectives Drafter — §2 วัตถุประสงค์ (Objectives).

Specialized agent for drafting the Objectives section of TOR documents.
Focuses on writing SMART objectives that align with the background section
and are measurable, achievable, and time-bound.

Requirements: 5.6, 12.1, 16.5
"""

from __future__ import annotations

from app.orchestrator.agents.base import formal_register, BaseDraftingAgent


class ObjectivesDraftingAgent(BaseDraftingAgent):
    """Drafts §2 วัตถุประสงค์ — the objectives section of a TOR."""

    section_key = "s2"
    section_name_th = "วัตถุประสงค์"
    section_name_en = "Objectives"

    def get_system_prompt(self, category: str | None = None) -> str:
        """Return the system prompt for Objectives section drafting."""
        return (
            formal_register(category, self.section_key)
            + "คุณกำลังร่างส่วน «วัตถุประสงค์» ของเอกสารกำหนดขอบเขตงาน\n\n"
            "=== ผลลัพธ์ที่ต้องส่ง ===\n"
            "ตอบเป็น JSON ล้วนเท่านั้น ห้ามข้อความก่อนหรือหลัง:\n"
            "{\n"
            '  "mainObj": "...",\n'
            '  "users": "...",\n'
            '  "kpi": "..."\n'
            "}\n\n"
            "=== ความหมายแต่ละคีย์ (ต้องครบทั้งสาม) ===\n"
            "mainObj — วัตถุประสงค์รายข้อ ๓–๘ ข้อ\n"
            "  • ทุกข้อขึ้นต้นด้วย «เพื่อ»\n"
            "  • วัดผลได้ ผูกกับงานจริงในขอบเขตของงาน\n"
            "  • ห้ามข้อความกว้างอย่าง «เพื่อพัฒนาองค์กร»\n"
            "  • คัดลอก/เรียบเรียงจากเอกสารขั้นที่ ๐ ให้ครบ ไม่สรุปจนหายสาระ\n"
            "users — กลุ่มผู้ใช้งานเป้าหมาย\n"
            "  • ระบุหน่วยงาน/เจ้าหน้าที่/กลุ่มที่ใช้ระบบจริงจากเอกสาร\n"
            "  • ห้ามปล่อยว่างถ้าเอกสารมีกลุ่มเป้าหมาย\n"
            "kpi — ตัวชี้วัดความสำเร็จ\n"
            "  • เป็นข้อย่อยพร้อมตัวเลขที่วัดได้ (ร้อยละ วัน จำนวน)\n"
            "  • ดึงจากหัวข้อตัวชี้วัด/เป้าหมายในเอกสารต้นทางให้ครบ\n"
            "  • ห้ามปล่อยว่างถ้าเอกสารมีตัวชี้วัด\n\n"
            "=== กฎเข้ม ===\n"
            "ห้ามเล่าความเป็นมายาวหรือรายละเอียดงานในหมวดนี้\n"
            "ห้ามพิมพ์ป้ายช่องข้อมูลหรือรหัสภาษาอังกฤษเป็นหัวข้อในค่าสตริง\n"
            "ถ้ามีร่างปัจจุบัน ให้คงสาระที่ผู้ใช้แก้แล้ว และเติมเฉพาะส่วนที่ยังว่างหรือยังไม่ครบ\n"
        )
