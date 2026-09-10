"""Agent 1: Background Drafter — §1 ความเป็นมา (Background/Rationale).

Specialized agent for drafting the Background section of TOR documents.
Focuses on government context framing, organizational mandate, problem
statement, and justification for the procurement.

Requirements: 5.6, 12.1, 16.5
"""

from __future__ import annotations

from app.orchestrator.agents.base import formal_register, BaseDraftingAgent


class BackgroundDraftingAgent(BaseDraftingAgent):
    """Drafts §1 ความเป็นมา — the background/rationale section of a TOR."""

    section_key = "s1"
    section_name_th = "ความเป็นมา"
    section_name_en = "Background"

    def get_system_prompt(self, category: str | None = None) -> str:
        """Return the system prompt for Background section drafting."""
        return (
            formal_register(category, self.section_key)
            + "คุณกำลังร่างส่วน «ความเป็นมา» (๑) ของเอกสารกำหนดขอบเขตงาน\n\n"
            "=== แนวทางการเขียนส่วนความเป็นมา ===\n"
            "ส่วนนี้ต้องประกอบด้วยสาระต่อไปนี้ในย่อหน้าต่อเนื่อง ไม่แยกหัวข้อย่อย:\n"
            "๑. บริบทขององค์กร — ชื่อหน่วยงาน ภารกิจ อำนาจหน้าที่ตามกฎหมาย\n"
            "๒. สภาพปัญหา/ความจำเป็น — อธิบายปัญหาหรือความต้องการที่นำไปสู่การจัดซื้อจัดจ้าง\n"
            "๓. ผลกระทบหากไม่ดำเนินการ — ความเสียหายหรือผลเสียที่จะเกิดขึ้น\n"
            "๔. ความสอดคล้องกับแผน — เชื่อมโยงกับแผนยุทธศาสตร์ แผนปฏิบัติราชการ หรือนโยบายที่เกี่ยวข้อง\n"
            "๕. เหตุผลความจำเป็นในการจัดซื้อจัดจ้าง — สรุปว่าเหตุใดจึงต้องดำเนินการ\n\n"
            "=== ข้อกำหนดด้านรูปแบบ ===\n"
            "- เขียนเป็นย่อหน้าต่อเนื่อง (เล่าเรื่อง) ห้ามใช้หัวข้อย่อย "
            "ห้ามพิมพ์ป้ายเช่น ประวัติ/สถานการณ์ปัจจุบันของระบบเดิม หรือ ปัญหาที่พบ (ระบุตัวเลข/สถิติ)\n"
            "- อธิบายภารกิจ ปัญหา ผลกระทบ และความจำเป็นให้ครบสาระ "
            "ตามข้อมูลที่มี ไม่บังคับยาวหลายย่อหน้า\n"
            "- เริ่มต้นด้วยชื่อหน่วยงานและภารกิจ\n"
            "- ลงท้ายด้วยสูตร «จึงมีความจำเป็นต้อง…»\n"
            "- หลีกเลี่ยงรายละเอียดทางเทคนิคมากเกินไป (จะอยู่ในส่วนขอบเขตงาน)\n"
            "- ไม่ระบุจำนวนเงินงบประมาณในส่วนนี้ (จะอยู่ในส่วนงบประมาณ)\n\n"
            "=== ตัวอย่างโครงสร้าง ===\n"
            "[ชื่อหน่วยงาน] มีภารกิจ/อำนาจหน้าที่ตาม [กฎหมาย/ระเบียบ] "
            "ในการ [ภารกิจหลัก]...\n"
            "ปัจจุบัน [สภาพปัญหา/ความจำเป็น]...\n"
            "หากไม่ดำเนินการ [ผลกระทบ]...\n"
            "ดังนั้น เพื่อ [วัตถุประสงค์โดยรวม] จึงมีความจำเป็นต้อง "
            "[จัดซื้อ/จัดจ้าง/เช่า]...\n"
        )
