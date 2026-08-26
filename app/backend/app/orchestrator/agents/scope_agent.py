"""Agent 4: Scope Drafter — §4 ขอบเขตของงาน.

Specialized agent for drafting the Scope of Work section of TOR documents.
This is typically the longest and most detailed section, supporting up to
14 subsections covering technical requirements, deliverables, and specifications.
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
            + "คุณกำลังร่างส่วน «ขอบเขตของงาน» ของเอกสาร TOR\n\n"
            "=== แนวทางการเขียนส่วนขอบเขตของงาน ===\n"
            "ส่วนนี้เป็นส่วนสำคัญที่สุดของ TOR และมี 14 หัวข้อย่อยตามแม่แบบระบบ:\n\n"
            "4.1 สรุปขอบเขตงาน\n"
            "4.2 ระบบงานปัจจุบัน\n"
            "4.3 งานหลักและกิจกรรม\n"
            "4.4 ข้อกำหนดด้านฮาร์ดแวร์\n"
            "4.5 ข้อกำหนดด้านซอฟต์แวร์และลิขสิทธิ์\n"
            "4.6 จุดเชื่อมโยงระบบ\n"
            "4.7 มาตรฐานและแบบอ้างอิง\n"
            "4.8 ผลงานส่งมอบ\n"
            "4.9 ระยะเวลาการสนับสนุนและบำรุงรักษา\n"
            "4.10 บุคลากรและทีมงาน\n"
            "4.11 รูปแบบการบำรุงรักษา\n"
            "4.12 การดำเนินงานและการบริหารจัดการ\n"
            "4.13 แผนสำรองและกู้คืนระบบ\n"
            "4.14 ข้อกำหนดด้านความมั่นคงปลอดภัย\n\n"
            "=== ข้อกำหนดด้านรูปแบบ ===\n"
            "- เขียนแยกเป็นหัวข้อย่อย 4.1 ถึง 4.14 ตามลำดับ (ข้ามหัวข้อที่ไม่มีข้อมูล)\n"
            "- เขียนรายละเอียดทางเทคนิคให้ชัดเจน วัดผลได้\n"
            "- ใช้ตารางมาร์กดาวน์สำหรับรายการพัสดุ/อุปกรณ์ที่มีหลายรายการ หัวคอลัมน์เป็นภาษาไทย\n"
            "- ระบุหน่วยนับ จำนวน และคุณลักษณะที่ชัดเจน\n"
            "- ห้ามระบุยี่ห้อ/รุ่นเฉพาะ ยกเว้นจะมีคำว่า «หรือเทียบเท่า»\n"
            "- ห้ามใช้คำกว้างที่ไม่สามารถตรวจสอบได้ เช่น «คุณภาพดี» «ทันสมัย»\n"
            "- ต้องสอดคล้องกับวัตถุประสงค์ และงบประมาณ\n"
            "- เขียนเป็นภาษาไทยเท่านั้น\n\n"
            "=== หลักการเขียนที่ดี ===\n"
            "- เขียนเป็นข้อกำหนดที่ตรวจรับได้\n"
            "- แยกระหว่าง «ต้อง» กับ «ควร»\n"
            "- ระบุเกณฑ์การตรวจรับสำหรับแต่ละผลงานส่งมอบ\n"
            "- ใช้ภาษาที่เป็นกลาง ไม่เอื้อประโยชน์ต่อผู้ขายรายใดรายหนึ่ง\n"
            "- คำนึงถึงความสมเหตุสมผลกับงบประมาณ\n"
        )
