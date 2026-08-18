"""Agent 3: Qualifications Drafter — §3 คุณสมบัติผู้เสนอราคา (Vendor Qualifications).

Specialized agent for drafting the Qualifications section of TOR documents.
Focuses on legal requirements, paid-up capital calculation, experience criteria,
personnel qualifications, and fairness (avoiding brand-lock).

This section contains legal references and is subject to mandatory human review.

Requirements: 5.6, 6.2, 12.1, 12.7, 16.5
"""

from __future__ import annotations

from typing import Any

from app.orchestrator.agents.base import THAI_FORMAL_REGISTER_PREAMBLE, BaseDraftingAgent


class QualificationsDraftingAgent(BaseDraftingAgent):
    """Drafts §3 คุณสมบัติผู้เสนอราคา — vendor qualification requirements."""

    section_key = "s3"
    section_name_th = "คุณสมบัติผู้เสนอราคา"
    section_name_en = "Qualifications"

    def get_system_prompt(self) -> str:
        """Return the system prompt for Qualifications section drafting."""
        return (
            THAI_FORMAL_REGISTER_PREAMBLE
            + "คุณกำลังร่างส่วน «คุณสมบัติผู้เสนอราคา» (§3) ของเอกสาร TOR\n\n"
            "⚠️ ส่วนนี้มีข้อกำหนดทางกฎหมาย — ต้องอ้างอิง พ.ร.บ. 2560 อย่างถูกต้อง\n\n"
            "=== แนวทางการเขียนส่วนคุณสมบัติ ===\n"
            "ส่วนนี้ต้องประกอบด้วย:\n"
            "1. คุณสมบัติทั่วไปตามกฎหมาย — ตามมาตรา 50 แห่ง พ.ร.บ. 2560\n"
            "   - เป็นนิติบุคคลจดทะเบียนในประเทศไทย\n"
            "   - ไม่เป็นผู้ถูกระบุชื่อไว้ในบัญชีรายชื่อผู้ทิ้งงาน\n"
            "   - ไม่เป็นผู้มีผลประโยชน์ร่วมกันกับผู้เสนอราคารายอื่น\n"
            "   - ไม่เป็นผู้ได้รับเอกสิทธิ์หรือความคุ้มกันที่จะปฏิเสธไม่ยอมขึ้นศาลไทย\n"
            "2. ทุนจดทะเบียน — คำนวณจาก งบประมาณ ÷ 4 (ปัดลง)\n"
            "   สูตร: ทุนจดทะเบียนชำระแล้ว ≥ floor(งบประมาณ / 4) บาท\n"
            "3. ประสบการณ์ — ผลงานที่ผ่านมาในงานลักษณะเดียวกัน\n"
            "4. บุคลากรหลัก — คุณวุฒิและจำนวนบุคลากรที่ต้องจัดให้\n"
            "5. ใบอนุญาต/การขึ้นทะเบียน — ตามประเภทงาน\n\n"
            "=== กฎหมายที่เกี่ยวข้อง ===\n"
            "- พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560 มาตรา 50 (คุณสมบัติผู้ยื่นข้อเสนอ)\n"
            "- กฎกระทรวงกำหนดหลักเกณฑ์เกี่ยวกับผู้ที่มีสิทธิขึ้นทะเบียนผู้ประกอบการ\n"
            "- ระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างฯ พ.ศ. 2560 ข้อ 16\n\n"
            "=== ข้อกำหนดด้านรูปแบบ ===\n"
            "- เขียนเป็นรายการลำดับเลข\n"
            "- ข้อแรกต้องเป็นคุณสมบัติทั่วไปตามกฎหมาย\n"
            "- ข้อสองต้องเป็นทุนจดทะเบียน (ระบุจำนวนเงินที่คำนวณแล้ว)\n"
            "- ข้อถัดไปเป็นคุณสมบัติเฉพาะตามประเภทงาน\n"
            "- ห้ามกำหนดคุณสมบัติที่เป็นการกีดกัน (ห้ามระบุยี่ห้อเฉพาะ)\n"
            "- ต้องเปิดโอกาสให้มีการแข่งขันอย่างเป็นธรรม\n\n"
            "=== สูตรคำนวณทุนจดทะเบียน ===\n"
            "ทุนจดทะเบียน = floor(งบประมาณโครงการ ÷ 4)\n"
            "ตัวอย่าง: งบประมาณ 10,000,000 บาท → ทุนจดทะเบียน ≥ 2,500,000 บาท\n"
        )

    def build_user_message(
        self,
        user_input: dict[str, Any],
        rag_chunks: list,
        template: dict[str, Any] | None = None,
        validation_findings: list | None = None,
        human_feedback: str | None = None,
    ) -> str:
        """Build user message with budget-derived capital calculation hint.

        Enhances the base implementation by extracting budget from user_input
        and pre-computing the required paid-up capital for the LLM.
        """
        # Pre-compute paid-up capital if budget is available
        budget = user_input.get("budget") or user_input.get("งบประมาณ")
        if budget and isinstance(budget, (int, float)):
            capital = int(budget) // 4
            user_input = {
                **user_input,
                "_computed_capital": capital,
                "_capital_note": (
                    f"ทุนจดทะเบียนชำระแล้วที่คำนวณได้ = {capital:,} บาท "
                    f"(จาก {int(budget):,} ÷ 4)"
                ),
            }

        return super().build_user_message(
            user_input=user_input,
            rag_chunks=rag_chunks,
            template=template,
            validation_findings=validation_findings,
            human_feedback=human_feedback,
        )
