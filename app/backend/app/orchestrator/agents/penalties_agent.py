"""Agent 9: Penalties Drafter — §10 อัตราค่าปรับ.

Specialized agent for drafting the Penalties section of TOR documents.
Focuses on penalty rate calculation (0.01%–0.20% per day).

This section contains penalty clauses and is subject to mandatory human review.

Requirements: 5.6, 6.8, 12.1, 12.7, 16.5
"""

from __future__ import annotations

from typing import Any

from app.orchestrator.agents.base import THAI_FORMAL_REGISTER_PREAMBLE, BaseDraftingAgent


class PenaltiesDraftingAgent(BaseDraftingAgent):
    """Drafts §10 อัตราค่าปรับ — penalties."""

    section_key = "s10"
    section_name_th = "อัตราค่าปรับ"
    section_name_en = "Penalties"

    def get_system_prompt(self) -> str:
        """Return the system prompt for Penalties/Warranty section drafting."""
        return (
            THAI_FORMAL_REGISTER_PREAMBLE
            + "คุณกำลังร่างส่วน «อัตราค่าปรับ» (§10) ของเอกสาร TOR\n\n"
            "⚠️ ส่วนนี้มีข้อกำหนดทางกฎหมายเข้มงวด — ต้องอ้างอิงให้ถูกต้อง\n\n"
            "=== อัตราค่าปรับ (§10) ===\n"
            "ข้อกำหนดทางกฎหมาย:\n"
            "- อัตราค่าปรับต้องอยู่ระหว่าง 0.01%–0.20% ต่อวัน ของราคาค่าจ้างตามสัญญา\n"
            "- ค่าปรับขั้นต่ำ 100 บาท/วัน\n"
            "- คำนวณเป็นรายวัน นับจากวันถัดจากวันครบกำหนดส่งมอบ\n"
            "- ต้องระบุกรณีที่จะถูกปรับอย่างชัดเจน\n"
            "- ต้องระบุสิทธิในการบอกเลิกสัญญาหากค่าปรับสะสมเกินร้อยละ [X]\n\n"
            "กฎหมายที่เกี่ยวข้อง:\n"
            "- ระเบียบกระทรวงการคลังฯ ข้อ 162 (อัตราค่าปรับ)\n"
            "- พ.ร.บ. 2560 มาตรา 97 (การบอกเลิกสัญญา)\n\n"
            "=== ข้อกำหนดด้านรูปแบบ ===\n"
            "- ระบุอัตราค่าปรับเป็นเปอร์เซ็นต์ต่อวัน\n"
            "- ระบุสูตรคำนวณค่าปรับ\n"
            "- ระบุระยะเวลารับประกัน\n"
            "- ระบุเงื่อนไขการบอกเลิกสัญญาที่ชัดเจน\n\n"
            "=== ตัวอย่างโครงสร้าง ===\n"
            "10. อัตราค่าปรับ\n"
            "  10.1 กรณีผู้รับจ้างส่งมอบงานล่าช้ากว่ากำหนดตามสัญญา "
            "ผู้รับจ้างต้องชำระค่าปรับเป็นรายวัน ในอัตราร้อยละ [0.01–0.20] "
            "ของราคาค่าจ้างตามสัญญา แต่ไม่ต่ำกว่า 100 บาท/วัน\n"
            "  10.2 กรณีค่าปรับสะสมเกินร้อยละ [X] ของราคาค่าจ้าง "
            "หน่วยงานมีสิทธิบอกเลิกสัญญาได้\n\n"
            "9. การรับประกัน\n"
            "  9.1 ผู้รับจ้างต้องรับประกันผลงาน/พัสดุ เป็นระยะเวลาไม่น้อยกว่า [X] ปี "
            "นับถัดจากวันที่ตรวจรับมอบงานงวดสุดท้าย\n"
            "  9.2 ในระหว่างระยะเวลารับประกัน หาก [เงื่อนไข] ผู้รับจ้างต้อง [การดำเนินการ] "
            "ภายใน [X] วัน นับจากวันที่ได้รับแจ้ง\n"
        )

    def build_user_message(
        self,
        user_input: dict[str, Any],
        rag_chunks: list,
        template: dict[str, Any] | None = None,
        validation_findings: list | None = None,
        human_feedback: str | None = None,
    ) -> str:
        """Build user message with penalty rate constraint reminder."""
        budget = user_input.get("budget") or user_input.get("งบประมาณ")
        penalty_rate = user_input.get("penalty_rate") or user_input.get("อัตราค่าปรับ")

        notes: list[str] = []
        if penalty_rate and isinstance(penalty_rate, (int, float)):
            if penalty_rate < 0.01 or penalty_rate > 0.20:
                notes.append(
                    f"⚠️ อัตราค่าปรับ {penalty_rate}% ต่อวัน "
                    f"อยู่นอกช่วงที่กฎหมายกำหนด (0.01%–0.20%)"
                )
        notes.append("⚠️ ข้อกำหนด: อัตราค่าปรับ 0.01%–0.20% ต่อวัน, ขั้นต่ำ 100 บาท/วัน")

        if budget and isinstance(budget, (int, float)):
            # Show example calculation
            example_rate = 0.10
            daily_penalty = int(budget) * example_rate / 100
            notes.append(
                f"ตัวอย่าง: อัตรา {example_rate}%/วัน × {int(budget):,} บาท "
                f"= {daily_penalty:,.0f} บาท/วัน"
            )

        if notes:
            user_input = {**user_input, "_penalty_notes": "\n".join(notes)}

        return super().build_user_message(
            user_input=user_input,
            rag_chunks=rag_chunks,
            template=template,
            validation_findings=validation_findings,
            human_feedback=human_feedback,
        )
