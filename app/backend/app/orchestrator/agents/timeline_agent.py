"""Agent 5: Timeline Drafter — §5 ระยะเวลาดำเนินการ (Timeline).

Specialized agent for drafting the Timeline section of TOR documents.
Focuses on duration estimation, milestone planning, and feasibility
relative to budget and scope complexity.

Requirements: 5.6, 6.4, 12.1, 16.5
"""

from __future__ import annotations

from typing import Any

from app.orchestrator.agents.base import THAI_FORMAL_REGISTER_PREAMBLE, BaseDraftingAgent


class TimelineDraftingAgent(BaseDraftingAgent):
    """Drafts §5 ระยะเวลาดำเนินการ — the timeline/duration section of a TOR."""

    section_key = "s5"
    section_name_th = "ระยะเวลาดำเนินการ"
    section_name_en = "Timeline"

    def get_system_prompt(self) -> str:
        """Return the system prompt for Timeline section drafting."""
        return (
            THAI_FORMAL_REGISTER_PREAMBLE
            + "คุณกำลังร่างส่วน «ระยะเวลาดำเนินการ» (§5) ของเอกสาร TOR\n\n"
            "=== แนวทางการเขียนส่วนระยะเวลา ===\n"
            "ส่วนนี้ต้องประกอบด้วย:\n"
            "1. ระยะเวลาดำเนินการรวม — จำนวนวัน/เดือน นับถัดจากวันลงนามในสัญญา\n"
            "2. แผนงาน/ตารางเวลา — แบ่งเป็นระยะหรือ milestone\n"
            "3. กำหนดส่งมอบ — วันที่ส่งมอบผลงานแต่ละงวด\n\n"
            "=== กฎหมายและข้อกำหนดด้านระยะเวลา ===\n"
            "- งบประมาณ > 100 ล้านบาท: ระยะเวลาควรไม่น้อยกว่า 180 วัน\n"
            "- งบประมาณ < 10 ล้านบาท: ระยะเวลาควรไม่เกิน 365 วัน\n"
            "- ต้องสอดคล้องกับขอบเขตงาน (§4) และผลงานส่งมอบ\n"
            "- ต้องเป็นไปได้ในทางปฏิบัติ (feasible)\n\n"
            "=== ข้อกำหนดด้านรูปแบบ ===\n"
            "- ระบุระยะเวลารวมเป็นวัน (หรือเดือน) อย่างชัดเจน\n"
            "- ระบุจุดเริ่มต้น: «นับถัดจากวันลงนามในสัญญา» หรือ «นับถัดจากวันที่ได้รับหนังสือแจ้งให้เริ่มงาน»\n"
            "- แบ่งเป็นระยะ/งวด หากเป็นงานขนาดใหญ่\n"
            "- ใช้ตารางแสดงแผนงานหากมีหลายขั้นตอน\n"
            "- สอดคล้องกับงวดงาน/การจ่ายเงิน (§8)\n\n"
            "=== ตัวอย่างโครงสร้าง ===\n"
            "ผู้รับจ้างต้องดำเนินการให้แล้วเสร็จภายใน [X] วัน "
            "นับถัดจากวันลงนามในสัญญา โดยมีแผนการดำเนินงานดังนี้\n"
            "  ระยะที่ 1: [งาน] ภายใน [X] วัน\n"
            "  ระยะที่ 2: [งาน] ภายใน [X] วัน\n"
            "  ...\n"
        )

    def build_user_message(
        self,
        user_input: dict[str, Any],
        rag_chunks: list,
        template: dict[str, Any] | None = None,
        validation_findings: list | None = None,
        human_feedback: str | None = None,
    ) -> str:
        """Build user message with timeline feasibility hints.

        Enhances the base implementation by checking budget-duration feasibility
        rules and adding guidance notes.
        """
        budget = user_input.get("budget") or user_input.get("งบประมาณ")

        feasibility_notes: list[str] = []
        if budget and isinstance(budget, (int, float)):
            if budget > 100_000_000:
                feasibility_notes.append(
                    f"หมายเหตุ: งบประมาณ {int(budget):,} บาท (>100 ล้าน) "
                    f"— ระยะเวลาควรไม่น้อยกว่า 180 วัน"
                )
            elif budget < 10_000_000:
                feasibility_notes.append(
                    f"หมายเหตุ: งบประมาณ {int(budget):,} บาท (<10 ล้าน) "
                    f"— ระยะเวลาควรไม่เกิน 365 วัน"
                )

        if feasibility_notes:
            user_input = {
                **user_input,
                "_feasibility_notes": "\n".join(feasibility_notes),
            }

        return super().build_user_message(
            user_input=user_input,
            rag_chunks=rag_chunks,
            template=template,
            validation_findings=validation_findings,
            human_feedback=human_feedback,
        )
