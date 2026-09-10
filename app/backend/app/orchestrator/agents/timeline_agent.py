"""Agent 5: Timeline Drafter — §5 ระยะเวลาดำเนินการ (Timeline).

Specialized agent for drafting the Timeline section of TOR documents.
Focuses on duration estimation, milestone planning, and feasibility
relative to budget and scope complexity.

Requirements: 5.6, 6.4, 12.1, 16.5
"""

from __future__ import annotations

from typing import Any

from app.orchestrator.agents.base import formal_register, BaseDraftingAgent


class TimelineDraftingAgent(BaseDraftingAgent):
    """Drafts §5 ระยะเวลาดำเนินการ — the timeline/duration section of a TOR."""

    section_key = "s5"
    section_name_th = "ระยะเวลาดำเนินการ"
    section_name_en = "Timeline"

    def get_system_prompt(self, category: str | None = None) -> str:
        """Return the system prompt for Timeline section drafting."""
        from app.services.thai_draft import TIMELINE_TABLE_TEMPLATE

        return (
            formal_register(category, self.section_key)
            + "คุณกำลังร่างส่วน «ระยะเวลาดำเนินการ» (๕) ของเอกสารกำหนดขอบเขตงาน\n\n"
            "=== แนวทางการเขียนส่วนระยะเวลา ===\n"
            "ส่วนนี้ต้องประกอบด้วย:\n"
            "๑. ระยะเวลาดำเนินการรวม — จำนวนวัน นับถัดจากวันลงนามในสัญญา\n"
            "๒. แผนงานเป็นตารางงวดส่งมอบ\n"
            "๓. กำหนดส่งมอบผลงานแต่ละงวด\n\n"
            "=== ข้อกำหนดด้านรูปแบบ ===\n"
            "- ระบุระยะเวลารวมเป็นวันอย่างชัดเจน ตามด้วย «นับถัดจากวันลงนามในสัญญา»\n"
            "- ต้องมีตารางมาร์กดาวน์คอลัมน์ไทย:\n"
            f"{TIMELINE_TABLE_TEMPLATE}\n"
            "- จำนวนวันของแต่ละงวดเรียงเพิ่มขึ้น งวดสุดท้ายเท่ากับระยะเวลารวม\n"
            "- สอดคล้องกับงวดงานและการจ่ายเงิน\n"
            "- ห้ามซ้ำรายละเอียดงานจาก s4 หรือตารางจ่ายเงินจาก s8\n"
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
