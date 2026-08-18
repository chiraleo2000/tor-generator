"""Agent 4: Scope Drafter — §4 ขอบเขตของงาน (Scope of Work).

Specialized agent for drafting the Scope of Work section of TOR documents.
This is typically the longest and most detailed section, supporting up to
14 subsections covering technical requirements, deliverables, and specifications.

Requirements: 5.6, 5.7, 12.1, 16.5
"""

from __future__ import annotations

from app.orchestrator.agents.base import THAI_FORMAL_REGISTER_PREAMBLE, BaseDraftingAgent


class ScopeDraftingAgent(BaseDraftingAgent):
    """Drafts §4 ขอบเขตของงาน — the scope of work section of a TOR."""

    section_key = "s4"
    section_name_th = "ขอบเขตของงาน"
    section_name_en = "Scope"

    def get_system_prompt(self) -> str:
        """Return the system prompt for Scope of Work section drafting."""
        return (
            THAI_FORMAL_REGISTER_PREAMBLE
            + "คุณกำลังร่างส่วน «ขอบเขตของงาน» (§4) ของเอกสาร TOR\n\n"
            "=== แนวทางการเขียนส่วนขอบเขตของงาน ===\n"
            "ส่วนนี้เป็นส่วนสำคัญที่สุดของ TOR และมี 14 หัวข้อย่อยตามแม่แบบระบบ:\n\n"
            "s4.1 สรุปขอบเขตงาน\n"
            "s4.2 ระบบงานปัจจุบัน (As-Is)\n"
            "s4.3 งานหลักและกิจกรรม\n"
            "s4.4 ข้อกำหนดด้านฮาร์ดแวร์\n"
            "s4.5 ข้อกำหนดด้านซอฟต์แวร์และลิขสิทธิ์\n"
            "s4.6 จุดเชื่อมโยงระบบ\n"
            "s4.7 มาตรฐานและแบบอ้างอิง\n"
            "s4.8 ผลงานส่งมอบ\n"
            "s4.9 ระยะเวลาการสนับสนุนและบำรุงรักษา\n"
            "s4.10 บุคลากรและทีมงาน\n"
            "s4.11 รูปแบบการบำรุงรักษา\n"
            "s4.12 การดำเนินงานและการบริหารจัดการ\n"
            "s4.13 แผนสำรองและกู้คืนระบบ\n"
            "s4.14 ข้อกำหนดด้านความมั่นคงปลอดภัย\n\n"
            "=== ข้อกำหนดด้านรูปแบบ ===\n"
            "- ใช้หัวข้อย่อยที่เหมาะสมกับประเภทงาน (ไม่จำเป็นต้องมีครบทุกหัวข้อ)\n"
            "- เขียนรายละเอียดทางเทคนิคให้ชัดเจน วัดผลได้\n"
            "- ใช้ตารางสำหรับรายการพัสดุ/อุปกรณ์ที่มีหลายรายการ\n"
            "- ระบุหน่วยนับ จำนวน และคุณลักษณะที่ชัดเจน\n"
            "- ห้ามระบุยี่ห้อ/รุ่นเฉพาะ ยกเว้นจะมีคำว่า «หรือเทียบเท่า»\n"
            "- ห้ามใช้คำกว้างที่ไม่สามารถตรวจสอบได้ เช่น «คุณภาพดี» «ทันสมัย»\n"
            "- ต้องสอดคล้องกับวัตถุประสงค์ (§2) และงบประมาณ (§7)\n\n"
            "=== หลักการเขียนที่ดี ===\n"
            "- เขียนเป็น specification ที่ตรวจรับได้ (verifiable)\n"
            "- แยกระหว่าง «ต้อง» (mandatory) กับ «ควร» (desirable)\n"
            "- ระบุเกณฑ์การตรวจรับสำหรับแต่ละ deliverable\n"
            "- ใช้ภาษาที่เป็นกลาง ไม่เอื้อประโยชน์ต่อผู้ขายรายใดรายหนึ่ง\n"
            "- คำนึงถึงความสมเหตุสมผลกับงบประมาณ\n"
        )
