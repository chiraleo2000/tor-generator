"""Agent 8: Payment Drafter — §8 งวดงานและการจ่ายเงิน (Payment Schedule).

Specialized agent for drafting the Payment Schedule section of TOR documents.
Focuses on installment planning, deliverable linkage, and compliance with
payment percentage rules (5%–50% per installment, sum to 100%).

This section contains budget calculations and is subject to mandatory human review.

Requirements: 5.6, 6.3, 12.1, 12.7, 16.5
"""

from __future__ import annotations

from typing import Any

from app.orchestrator.agents.base import THAI_FORMAL_REGISTER_PREAMBLE, BaseDraftingAgent


class PaymentDraftingAgent(BaseDraftingAgent):
    """Drafts §8 งวดงานและการจ่ายเงิน — the payment schedule section."""

    section_key = "s8"
    section_name_th = "งวดงานและการจ่ายเงิน"
    section_name_en = "Payment"

    def get_system_prompt(self) -> str:
        """Return the system prompt for Payment Schedule section drafting."""
        return (
            THAI_FORMAL_REGISTER_PREAMBLE
            + "คุณกำลังร่างส่วน «งวดงานและการจ่ายเงิน» (§8) ของเอกสาร TOR\n\n"
            "⚠️ ส่วนนี้มีตัวเลขการเงิน — ต้องถูกต้องแม่นยำ\n\n"
            "=== แนวทางการเขียนส่วนงวดงาน ===\n"
            "ส่วนนี้ต้องประกอบด้วย:\n"
            "1. จำนวนงวด — แบ่งการจ่ายเงินเป็นกี่งวด\n"
            "2. รายละเอียดแต่ละงวด — ระบุผลงานส่งมอบและเปอร์เซ็นต์\n"
            "3. เงื่อนไขการจ่ายเงิน — ขั้นตอนการตรวจรับและจ่ายเงิน\n\n"
            "=== กฎเกณฑ์ทางกฎหมาย (สำคัญมาก) ===\n"
            "- เปอร์เซ็นต์รวมทุกงวด = 100% (ต้องเท่ากันพอดี)\n"
            "- แต่ละงวดต้องอยู่ระหว่าง 5%–50% (ไม่ต่ำกว่า 5% ไม่เกิน 50%)\n"
            "- แต่ละงวดต้องเชื่อมโยงกับผลงานส่งมอบ (Deliverables) ที่ชัดเจน\n"
            "- ผลงานส่งมอบต้องตรวจสอบได้ (verifiable deliverable)\n"
            "- ต้องสอดคล้องกับระยะเวลาดำเนินการ (§5) และขอบเขตงาน (§4)\n\n"
            "=== ข้อกำหนดด้านรูปแบบ ===\n"
            "- ใช้ตารางแสดงงวดงาน\n"
            "- ระบุลำดับงวด เปอร์เซ็นต์ จำนวนเงิน และผลงานส่งมอบ\n"
            "- ระบุระยะเวลาของแต่ละงวด\n"
            "- ระบุเงื่อนไขการตรวจรับ\n"
            "- แสดงยอดรวมที่ด้านล่างของตาราง (ต้อง = 100%)\n\n"
            "=== ตัวอย่างโครงสร้าง ===\n"
            "การจ่ายเงินค่าจ้างแบ่งออกเป็น [X] งวด ดังนี้\n\n"
            "| งวดที่ | ผลงานส่งมอบ | ระยะเวลา | เปอร์เซ็นต์ | จำนวนเงิน (บาท) |\n"
            "| 1 | [deliverable] | ภายใน X วัน | XX% | X,XXX,XXX |\n"
            "| 2 | [deliverable] | ภายใน X วัน | XX% | X,XXX,XXX |\n"
            "| ... | ... | ... | ... | ... |\n"
            "| รวม | | | 100% | [วงเงินรวม] |\n\n"
            "เงื่อนไขการจ่ายเงิน:\n"
            "- ผู้รับจ้างส่งมอบงานตามที่กำหนดในแต่ละงวด\n"
            "- คณะกรรมการตรวจรับพัสดุตรวจรับงานเรียบร้อยแล้ว\n"
            "- หน่วยงานจะชำระเงินภายใน [X] วันทำการนับจากวันตรวจรับ\n"
        )

    def build_user_message(
        self,
        user_input: dict[str, Any],
        rag_chunks: list,
        template: dict[str, Any] | None = None,
        validation_findings: list | None = None,
        human_feedback: str | None = None,
    ) -> str:
        """Build user message with payment constraint reminders.

        Enhances the base implementation with explicit percentage constraint
        reminders to help the LLM produce valid installments.
        """
        budget = user_input.get("budget") or user_input.get("งบประมาณ")
        installments = user_input.get("installments") or user_input.get("จำนวนงวด")

        notes: list[str] = []
        if budget and isinstance(budget, (int, float)):
            notes.append(f"วงเงินรวม: {int(budget):,} บาท")
        if installments and isinstance(installments, int):
            # Suggest even split as a starting point
            even_pct = round(100 / installments, 1)
            notes.append(
                f"จำนวนงวด: {installments} งวด "
                f"(แบ่งเท่าๆ กันประมาณ {even_pct}% ต่องวด)"
            )

        notes.append(
            "⚠️ ข้อกำหนด: เปอร์เซ็นต์รวม = 100%, แต่ละงวด 5%–50%"
        )

        if notes:
            user_input = {**user_input, "_payment_notes": "\n".join(notes)}

        return super().build_user_message(
            user_input=user_input,
            rag_chunks=rag_chunks,
            template=template,
            validation_findings=validation_findings,
            human_feedback=human_feedback,
        )
