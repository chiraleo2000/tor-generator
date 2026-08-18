"""Agent 1: Background Drafter — §1 ความเป็นมา (Background/Rationale).

Specialized agent for drafting the Background section of TOR documents.
Focuses on government context framing, organizational mandate, problem
statement, and justification for the procurement.

Requirements: 5.6, 12.1, 16.5
"""

from __future__ import annotations

from app.orchestrator.agents.base import THAI_FORMAL_REGISTER_PREAMBLE, BaseDraftingAgent


class BackgroundDraftingAgent(BaseDraftingAgent):
    """Drafts §1 ความเป็นมา — the background/rationale section of a TOR."""

    section_key = "s1"
    section_name_th = "ความเป็นมา"
    section_name_en = "Background"

    def get_system_prompt(self) -> str:
        """Return the system prompt for Background section drafting."""
        return (
            THAI_FORMAL_REGISTER_PREAMBLE
            + "คุณกำลังร่างส่วน «ความเป็นมา» (§1) ของเอกสาร TOR\n\n"
            "=== แนวทางการเขียนส่วนความเป็นมา ===\n"
            "ส่วนนี้ต้องประกอบด้วย:\n"
            "1. บริบทขององค์กร — ชื่อหน่วยงาน ภารกิจ อำนาจหน้าที่ตามกฎหมาย\n"
            "2. สภาพปัญหา/ความจำเป็น — อธิบายปัญหาหรือความต้องการที่นำไปสู่การจัดซื้อจัดจ้าง\n"
            "3. ผลกระทบหากไม่ดำเนินการ — ความเสียหายหรือผลเสียที่จะเกิดขึ้น\n"
            "4. ความสอดคล้องกับแผน — เชื่อมโยงกับแผนยุทธศาสตร์ แผนปฏิบัติราชการ หรือนโยบายที่เกี่ยวข้อง\n"
            "5. เหตุผลความจำเป็นในการจัดซื้อจัดจ้าง — สรุปว่าเหตุใดจึงต้องดำเนินการ\n\n"
            "=== ข้อกำหนดด้านรูปแบบ ===\n"
            "- เขียนเป็นย่อหน้าต่อเนื่อง (narrative) ไม่ใช้หัวข้อย่อย\n"
            "- ความยาวประมาณ 2-4 ย่อหน้า (300-800 คำ)\n"
            "- เริ่มต้นด้วยชื่อหน่วยงานและภารกิจ\n"
            "- ลงท้ายด้วยเหตุผลความจำเป็นในการจัดซื้อจัดจ้าง\n"
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
