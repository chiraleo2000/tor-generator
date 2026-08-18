"""Agent 7: Budget Drafter — §6 วงเงินงบประมาณ (Budget).

Specialized agent for drafting the Budget section of TOR documents.
Focuses on budget justification, cost breakdown, and alignment with scope.
Budget calculations are subject to Rule Engine validation.

This section contains budget calculations and is subject to mandatory human review.

Requirements: 5.6, 6.6, 12.1, 12.7, 16.5
"""

from __future__ import annotations

from typing import Any

from app.orchestrator.agents.base import THAI_FORMAL_REGISTER_PREAMBLE, BaseDraftingAgent


class BudgetDraftingAgent(BaseDraftingAgent):
    """Drafts §6 วงเงินงบประมาณ — the budget section of a TOR."""

    section_key = "s6"
    section_name_th = "วงเงินงบประมาณ"
    section_name_en = "Budget"

    def get_system_prompt(self) -> str:
        """Return the system prompt for Budget section drafting."""
        return (
            THAI_FORMAL_REGISTER_PREAMBLE
            + "คุณกำลังร่างส่วน «วงเงินงบประมาณ» (§6) ของเอกสาร TOR\n\n"
            "⚠️ ส่วนนี้มีตัวเลขงบประมาณ — ต้องถูกต้องแม่นยำ\n\n"
            "=== แนวทางการเขียนส่วนงบประมาณ ===\n"
            "ส่วนนี้ต้องประกอบด้วย:\n"
            "1. วงเงินงบประมาณรวม — ระบุจำนวนเงินรวมทั้งโครงการ\n"
            "2. ที่มาของงบประมาณ — แหล่งเงิน (งบประมาณแผ่นดิน/เงินรายได้/เงินกู้ ฯลฯ)\n"
            "3. รายละเอียดค่าใช้จ่าย — แยกตามหมวด/ประเภท\n"
            "4. เงื่อนไขด้านงบประมาณ — รวม/ไม่รวม VAT ค่าขนส่ง ฯลฯ\n\n"
            "=== ข้อกำหนดทางกฎหมาย ===\n"
            "- ต้องระบุวงเงินงบประมาณเป็นตัวเลขและตัวอักษร\n"
            "- ต้องระบุว่ารวมหรือไม่รวมภาษีมูลค่าเพิ่ม\n"
            "- งบประมาณต้องสอดคล้องกับขอบเขตงาน (§4)\n"
            "- ต้องเป็นราคากลางที่สมเหตุสมผล\n"
            "- ระบุวันที่ใช้ในการคำนวณราคากลาง\n\n"
            "=== ข้อกำหนดด้านรูปแบบ ===\n"
            "- ระบุจำนวนเงินทั้งตัวเลขและตัวอักษร\n"
            "  ตัวอย่าง: 10,000,000 บาท (สิบล้านบาทถ้วน)\n"
            "- ใช้ตารางสำหรับรายละเอียดค่าใช้จ่าย\n"
            "- ระบุว่ารวม VAT หรือไม่\n"
            "- หากมีหลายหมวด ให้แสดงยอดรวมแต่ละหมวดและยอดรวมทั้งหมด\n"
            "- ตัวเลขต้องสอดคล้องกัน (ผลรวมถูกต้อง)\n\n"
            "=== ตัวอย่างโครงสร้าง ===\n"
            "วงเงินงบประมาณในการจัดซื้อ/จัดจ้างครั้งนี้ เป็นเงินทั้งสิ้น "
            "[X] บาท ([จำนวนเงินเป็นตัวอักษร]) รวมภาษีมูลค่าเพิ่มแล้ว\n"
            "โดยใช้จ่ายจากงบประมาณ [แหล่งเงิน] ประจำปีงบประมาณ พ.ศ. [ปี]\n\n"
            "รายละเอียดค่าใช้จ่ายโดยประมาณ:\n"
            "| ลำดับ | รายการ | จำนวน | หน่วยละ (บาท) | รวม (บาท) |\n"
            "| 1 | ... | ... | ... | ... |\n"
            "| รวมทั้งสิ้น | | | | [X] |\n"
        )

    def build_user_message(
        self,
        user_input: dict[str, Any],
        rag_chunks: list,
        template: dict[str, Any] | None = None,
        validation_findings: list | None = None,
        human_feedback: str | None = None,
    ) -> str:
        """Build user message with budget formatting guidance.

        Enhances the base implementation by formatting budget amounts.
        """
        budget = user_input.get("budget") or user_input.get("งบประมาณ")
        if budget and isinstance(budget, (int, float)):
            user_input = {
                **user_input,
                "_budget_formatted": f"{int(budget):,} บาท",
            }

        return super().build_user_message(
            user_input=user_input,
            rag_chunks=rag_chunks,
            template=template,
            validation_findings=validation_findings,
            human_feedback=human_feedback,
        )
