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
            "ส่วนนี้เป็นส่วนสำคัญที่สุดของ TOR และอาจมีได้ถึง 14 หัวข้อย่อย:\n\n"
            "4.1 รายละเอียดของงาน/พัสดุ — ขอบเขตงานโดยรวม\n"
            "4.2 คุณลักษณะเฉพาะ/ข้อกำหนดทางเทคนิค — สเปกที่ต้องการ\n"
            "4.3 จำนวน/ปริมาณ — ระบุจำนวนที่ชัดเจน\n"
            "4.4 มาตรฐานที่ต้องเป็นไปตาม — ISO, มอก., หรือมาตรฐานอื่น\n"
            "4.5 สถานที่ส่งมอบ/ติดตั้ง/ดำเนินการ\n"
            "4.6 ขั้นตอนการดำเนินงาน — workflow หรือ methodology\n"
            "4.7 ผลงานส่งมอบ (Deliverables) — รายการ output ที่ต้องส่ง\n"
            "4.8 เงื่อนไขการรับประกัน\n"
            "4.9 การฝึกอบรม/ถ่ายทอดเทคโนโลยี\n"
            "4.10 เงื่อนไขเพิ่มเติม\n"
            "4.11 สิทธิในทรัพย์สินทางปัญญา\n"
            "4.12 การรักษาความลับ\n"
            "4.13 เงื่อนไขการยกเลิกสัญญา\n"
            "4.14 อื่นๆ\n\n"
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
