"""Agent 6: Evaluation Drafter — §11 เกณฑ์การพิจารณาคัดเลือก (Evaluation Criteria).

Specialized agent for drafting the Evaluation Criteria section of TOR documents.
Focuses on scoring methodology, price/performance weighting, and compliance
with procurement law requirements for fair and transparent evaluation.

Requirements: 5.6, 12.1, 16.5
"""

from __future__ import annotations

from app.orchestrator.agents.base import formal_register, BaseDraftingAgent


class EvaluationDraftingAgent(BaseDraftingAgent):
    """Drafts §11 เกณฑ์การพิจารณาคัดเลือก — the evaluation criteria section."""

    section_key = "s11"
    section_name_th = "เกณฑ์การพิจารณาคัดเลือก"
    section_name_en = "Evaluation"

    def get_system_prompt(self, category: str | None = None) -> str:
        """Return the system prompt for Evaluation Criteria section drafting."""
        from app.services.thai_draft import EVALUATION_TABLE_TEMPLATE

        return (
            formal_register(category, self.section_key)
            + "คุณกำลังร่างส่วน «เกณฑ์การพิจารณาคัดเลือก» ของเอกสารกำหนดขอบเขตงาน\n\n"
            "=== แนวทางการเขียนส่วนเกณฑ์การพิจารณา ===\n"
            "ส่วนนี้ต้องประกอบด้วย:\n"
            "๑. วิธีการพิจารณา — เกณฑ์ราคา หรือเกณฑ์ราคาประกอบเกณฑ์คุณภาพ "
            "หรือผลประโยชน์สูงสุด ห้ามใช้ชื่อวิธีเป็นภาษาอังกฤษ\n"
            "๒. ตารางน้ำหนักคะแนนรวมร้อยละ ๑๐๐\n"
            "๓. เกณฑ์ผ่านขั้นต่ำ\n"
            "๔. วิธีให้คะแนนแต่ละหัวข้อ\n\n"
            "=== ข้อกำหนดด้านรูปแบบ ===\n"
            "- ต้องมีตารางมาร์กดาวน์คอลัมน์ไทย:\n"
            f"{EVALUATION_TABLE_TEMPLATE}\n"
            "- เกณฑ์ต้องโปร่งใส วัดผลได้ ไม่เอื้อประโยชน์ต่อผู้ขายรายใดรายหนึ่ง\n"
            "- ห้ามซ้ำคุณสมบัติจาก s3 หรือรายละเอียดงานจาก s4\n"
        )
