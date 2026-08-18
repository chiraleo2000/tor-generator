"""Agent 6: Evaluation Drafter — §11 เกณฑ์การพิจารณาคัดเลือก (Evaluation Criteria).

Specialized agent for drafting the Evaluation Criteria section of TOR documents.
Focuses on scoring methodology, price/performance weighting, and compliance
with procurement law requirements for fair and transparent evaluation.

Requirements: 5.6, 12.1, 16.5
"""

from __future__ import annotations

from app.orchestrator.agents.base import THAI_FORMAL_REGISTER_PREAMBLE, BaseDraftingAgent


class EvaluationDraftingAgent(BaseDraftingAgent):
    """Drafts §11 เกณฑ์การพิจารณาคัดเลือก — the evaluation criteria section."""

    section_key = "s11"
    section_name_th = "เกณฑ์การพิจารณาคัดเลือก"
    section_name_en = "Evaluation"

    def get_system_prompt(self) -> str:
        """Return the system prompt for Evaluation Criteria section drafting."""
        return (
            THAI_FORMAL_REGISTER_PREAMBLE
            + "คุณกำลังร่างส่วน «เกณฑ์การพิจารณาคัดเลือก» (§11) ของเอกสาร TOR\n\n"
            "=== แนวทางการเขียนส่วนเกณฑ์การพิจารณา ===\n"
            "ส่วนนี้ต้องประกอบด้วย:\n"
            "1. วิธีการพิจารณา — ระบุวิธีการคัดเลือก\n"
            "   - พิจารณาราคาต่ำสุด (Price Only)\n"
            "   - พิจารณาราคาประกอบเกณฑ์คุณภาพ (Price-Performance)\n"
            "   - พิจารณาผลประโยชน์สูงสุด (Best Value)\n"
            "2. เกณฑ์คะแนน — รายละเอียดหัวข้อและน้ำหนักคะแนน\n"
            "3. เกณฑ์ผ่าน — คะแนนขั้นต่ำที่ต้องได้\n"
            "4. วิธีการให้คะแนน — อธิบายวิธีให้คะแนนแต่ละหัวข้อ\n\n"
            "=== กฎหมายที่เกี่ยวข้อง ===\n"
            "- พ.ร.บ. 2560 มาตรา 65 (หลักเกณฑ์การพิจารณาคัดเลือกข้อเสนอ)\n"
            "- ระเบียบกระทรวงการคลังฯ ข้อ 83–84 (เกณฑ์ราคา/เกณฑ์คุณภาพ)\n"
            "- น้ำหนักคะแนนด้านราคา: ไม่น้อยกว่า 30% (สำหรับ Price-Performance)\n"
            "- น้ำหนักคะแนนด้านเทคนิค: ระบุชัดเจน รวมกันเป็น 100%\n\n"
            "=== ข้อกำหนดด้านรูปแบบ ===\n"
            "- ระบุวิธีการพิจารณาอย่างชัดเจน\n"
            "- ใช้ตารางแสดงเกณฑ์คะแนน น้ำหนัก และวิธีให้คะแนน\n"
            "- น้ำหนักคะแนนรวมทุกหัวข้อ = 100%\n"
            "- ระบุเกณฑ์ผ่าน (pass/fail threshold)\n"
            "- เกณฑ์ต้องโปร่งใส วัดผลได้ ไม่เอื้อประโยชน์ต่อผู้ขายรายใดรายหนึ่ง\n"
            "- ต้องสอดคล้องกับขอบเขตงาน (§4) — ไม่กำหนดเกณฑ์ที่เกินขอบเขต\n\n"
            "=== ตัวอย่างโครงสร้าง ===\n"
            "การพิจารณาคัดเลือกใช้เกณฑ์ [ราคาต่ำสุด/ราคาประกอบเกณฑ์คุณภาพ]\n\n"
            "ตารางเกณฑ์คะแนน:\n"
            "| หัวข้อ | น้ำหนัก (%) | วิธีให้คะแนน |\n"
            "| ด้านเทคนิค | XX% | ... |\n"
            "| ด้านราคา | XX% | ... |\n"
            "| รวม | 100% | |\n\n"
            "เกณฑ์ผ่าน: ผู้เสนอราคาต้องได้คะแนนด้านเทคนิคไม่น้อยกว่า [X]%\n"
        )
