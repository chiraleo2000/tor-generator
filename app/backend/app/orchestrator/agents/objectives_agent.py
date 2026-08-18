"""Agent 2: Objectives Drafter — §2 วัตถุประสงค์ (Objectives).

Specialized agent for drafting the Objectives section of TOR documents.
Focuses on writing SMART objectives that align with the background section
and are measurable, achievable, and time-bound.

Requirements: 5.6, 12.1, 16.5
"""

from __future__ import annotations

from app.orchestrator.agents.base import THAI_FORMAL_REGISTER_PREAMBLE, BaseDraftingAgent


class ObjectivesDraftingAgent(BaseDraftingAgent):
    """Drafts §2 วัตถุประสงค์ — the objectives section of a TOR."""

    section_key = "s2"
    section_name_th = "วัตถุประสงค์"
    section_name_en = "Objectives"

    def get_system_prompt(self) -> str:
        """Return the system prompt for Objectives section drafting."""
        return (
            THAI_FORMAL_REGISTER_PREAMBLE
            + "คุณกำลังร่างส่วน «วัตถุประสงค์» (§2) ของเอกสาร TOR\n\n"
            "=== แนวทางการเขียนส่วนวัตถุประสงค์ ===\n"
            "ส่วนนี้ต้องประกอบด้วย:\n"
            "1. วัตถุประสงค์หลัก — เป้าหมายสำคัญที่สุดของการจัดซื้อจัดจ้าง\n"
            "2. วัตถุประสงค์รอง — เป้าหมายเพิ่มเติมที่สนับสนุนวัตถุประสงค์หลัก\n\n"
            "=== หลักการ SMART ===\n"
            "วัตถุประสงค์แต่ละข้อต้องเป็น:\n"
            "- Specific (เฉพาะเจาะจง): ระบุชัดเจนว่าต้องการอะไร\n"
            "- Measurable (วัดผลได้): มีตัวชี้วัดที่วัดได้\n"
            "- Achievable (บรรลุได้): เป็นไปได้ในทางปฏิบัติ\n"
            "- Relevant (เกี่ยวข้อง): สอดคล้องกับความเป็นมาและภารกิจ\n"
            "- Time-bound (มีกรอบเวลา): สามารถดำเนินการได้ภายในระยะเวลาที่กำหนด\n\n"
            "=== ข้อกำหนดด้านรูปแบบ ===\n"
            "- เขียนเป็นรายการลำดับเลข (numbered list)\n"
            "- จำนวน 3-7 ข้อ (ไม่น้อยกว่า 3 ไม่เกิน 7)\n"
            "- แต่ละข้อเริ่มต้นด้วยคำกริยา เช่น «เพื่อ...» หรือ «เพื่อให้ได้...»\n"
            "- ต้องสอดคล้องกับส่วนความเป็นมา (§1)\n"
            "- ไม่ซ้ำซ้อนกัน แต่ละข้อต้องมีเนื้อหาต่างกัน\n"
            "- หลีกเลี่ยงการใช้คำกว้างเกินไป เช่น «เพื่อพัฒนาองค์กร» โดยไม่ระบุรายละเอียด\n\n"
            "=== ตัวอย่างโครงสร้าง ===\n"
            "วัตถุประสงค์ของการจัดซื้อจัดจ้างครั้งนี้ มีดังนี้\n"
            "  1. เพื่อ [วัตถุประสงค์หลัก — ระบุเป้าหมายหลักที่ชัดเจน]\n"
            "  2. เพื่อ [วัตถุประสงค์รอง — สนับสนุนวัตถุประสงค์หลัก]\n"
            "  3. เพื่อ [วัตถุประสงค์เพิ่มเติม]\n"
        )
