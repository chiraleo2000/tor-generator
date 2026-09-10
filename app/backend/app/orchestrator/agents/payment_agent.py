"""Agent 8: Payment Drafter — §8 งวดงานและการจ่ายเงิน (Payment Schedule).

Specialized agent for drafting the Payment Schedule section of TOR documents.
Focuses on installment planning, deliverable linkage, and compliance with
payment percentage rules (5%–50% per installment, sum to 100%).

This section contains budget calculations and is subject to mandatory human review.

Requirements: 5.6, 6.3, 12.1, 12.7, 16.5
"""

from __future__ import annotations

from typing import Any

from app.orchestrator.agents.base import formal_register, BaseDraftingAgent


class PaymentDraftingAgent(BaseDraftingAgent):
    """Drafts §8 งวดงานและการจ่ายเงิน — the payment schedule section."""

    section_key = "s8"
    section_name_th = "งวดงานและการจ่ายเงิน"
    section_name_en = "Payment"

    def get_system_prompt(self, category: str | None = None) -> str:
        """Return the system prompt for Payment Schedule section drafting."""
        from app.services.thai_draft import PAYMENT_TABLE_TEMPLATE

        return (
            formal_register(category, self.section_key)
            + "คุณกำลังร่างส่วน «งวดงานและการจ่ายเงิน» (๘) ของเอกสารกำหนดขอบเขตงาน\n\n"
            "ส่วนนี้มีตัวเลขการเงิน — ต้องถูกต้องแม่นยำ\n\n"
            "=== แนวทางการเขียนส่วนงวดงาน ===\n"
            "ส่วนนี้ต้องประกอบด้วย:\n"
            "๑. จำนวนงวด — แบ่งการจ่ายเงินเป็นกี่งวด\n"
            "๒. รายละเอียดแต่ละงวด — ระบุผลงานส่งมอบและร้อยละ\n"
            "๓. เงื่อนไขการจ่ายเงิน — ขั้นตอนการตรวจรับและจ่ายเงิน\n\n"
            "=== กฎเกณฑ์ทางกฎหมาย ===\n"
            "- ร้อยละรวมทุกงวด = ๑๐๐ (ต้องเท่ากันพอดี)\n"
            "- แต่ละงวดต้องอยู่ระหว่างร้อยละ ๕–๕๐\n"
            "- แต่ละงวดต้องเชื่อมโยงกับผลงานส่งมอบที่ตรวจสอบได้\n"
            "- ต้องสอดคล้องกับระยะเวลาดำเนินการ และขอบเขตของงาน\n\n"
            "=== ข้อกำหนดด้านรูปแบบ ===\n"
            "- ต้องมีตารางมาร์กดาวน์คอลัมน์ไทยตามแม่แบบนี้:\n"
            f"{PAYMENT_TABLE_TEMPLATE}\n"
            "- ใช้รูปประโยค «งวดที่ … ชำระเงินในอัตราร้อยละ … ของจำนวนเงินในสัญญา "
            "เมื่อผู้รับจ้างส่งมอบงานงวดที่ … และคณะกรรมการตรวจรับพัสดุได้ตรวจรับเรียบร้อยแล้ว»\n"
            "- ห้ามใช้คำภาษาอังกฤษในหัวตารางหรือตัวอย่าง\n\n"
            "=== ตัวอย่างข้อความนำ ===\n"
            "การจ่ายเงินค่าจ้างแบ่งออกเป็น [X] งวด ดังนี้\n"
            "ห้ามซ้ำรายละเอียดงานจาก s4 — มีเฉพาะตารางงวดจ่ายและเงื่อนไขการจ่าย\n"
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
