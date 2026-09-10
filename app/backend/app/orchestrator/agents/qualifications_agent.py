"""Agent 3: Qualifications Drafter — §3 คุณสมบัติผู้เสนอราคา (Vendor Qualifications).

Specialized agent for drafting the Qualifications section of TOR documents.
Focuses on legal requirements, paid-up capital calculation, experience criteria,
personnel qualifications, and fairness (avoiding brand-lock).

This section contains legal references and is subject to mandatory human review.

Requirements: 5.6, 6.2, 12.1, 12.7, 16.5
"""

from __future__ import annotations

from typing import Any

from app.orchestrator.agents.base import formal_register, BaseDraftingAgent


class QualificationsDraftingAgent(BaseDraftingAgent):
    """Drafts §3 คุณสมบัติผู้เสนอราคา — vendor qualification requirements."""

    section_key = "s3"
    section_name_th = "คุณสมบัติผู้เสนอราคา"
    section_name_en = "Qualifications"

    def get_system_prompt(self, category: str | None = None) -> str:
        """Return the system prompt for Qualifications section drafting."""
        from app.domain.tor_taxonomy import (
            QUALIFICATION_SUBSECTIONS,
            qualification_subsections,
        )

        from app.domain.section_profile import profile_for_project

        cat = profile_for_project(category).category
        listed = []
        for key in qualification_subsections(cat):
            listed.append(QUALIFICATION_SUBSECTIONS.get(key, key))
        listed_text = "\n".join(f"- {title}" for title in listed) if listed else "คุณสมบัติทั่วไปตามกฎหมาย"
        personnel_note = ""
        if "qual.personnel" in qualification_subsections(cat):
            personnel_note = (
                "\nเมื่อมีบุคลากรหลัก ให้ใส่ตาราง "
                "| ตำแหน่ง | คุณวุฒิ | ประสบการณ์ | จำนวน | ระยะเวลา (เดือน) |\n"
            )
        return (
            formal_register(category, self.section_key)
            + "คุณกำลังร่างส่วน «คุณสมบัติผู้เสนอราคา» ของเอกสารกำหนดขอบเขตงาน\n\n"
            "ส่วนนี้มีข้อกำหนดทางกฎหมาย — ต้องอ้างอิง พ.ร.บ. ๒๕๖๐ อย่างถูกต้อง\n\n"
            "=== แนวทางการเขียนส่วนคุณสมบัติ ===\n"
            "เขียนตามลำดับหัวข้อย่อยของประเภทงานนี้เท่านั้น "
            "ห้ามพิมพ์เลขนำหน้าชื่อหัวข้อ ห้ามพิมพ์รหัส qual.*:\n"
            f"{listed_text}\n"
            f"{personnel_note}"
            "ข้อแรกต้องเป็นคุณสมบัติทั่วไปตามกฎหมาย "
            "ข้อต่อมาเป็นทุนจดทะเบียนหรือมูลค่าสุทธิเมื่อโปรไฟล์มี "
            "แล้วจึงเป็นคุณสมบัติเฉพาะ และปิดท้ายด้วยเอกสารที่ต้องยื่น\n\n"
            "=== กฎหมายที่เกี่ยวข้อง ===\n"
            "- พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. ๒๕๖๐ มาตรา ๕๐ (คุณสมบัติผู้ยื่นข้อเสนอ)\n"
            "- กฎกระทรวงกำหนดหลักเกณฑ์เกี่ยวกับผู้ที่มีสิทธิขึ้นทะเบียนผู้ประกอบการ\n"
            "- ระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างฯ พ.ศ. ๒๕๖๐ ข้อ ๑๖\n\n"
            "=== ข้อกำหนดด้านรูปแบบ ===\n"
            "- เขียนเป็นรายการตามหัวข้อย่อยด้านบน\n"
            "- ห้ามกำหนดคุณสมบัติที่เป็นการกีดกัน (ห้ามระบุยี่ห้อเฉพาะโดยไม่มีคำว่า หรือเทียบเท่า)\n"
            "- ต้องเปิดโอกาสให้มีการแข่งขันอย่างเป็นธรรม\n"
            "- ห้ามใส่สเปกฮาร์ดแวร์หรือขอบเขตงาน — มีเฉพาะคุณสมบัติผู้เสนอราคา\n\n"
            "=== สูตรคำนวณทุนจดทะเบียน ===\n"
            "ทุนจดทะเบียน = floor(งบประมาณโครงการ ÷ ๔)\n"
            "ตัวอย่าง: งบประมาณ ๑๐,๐๐๐,๐๐๐ บาท → ทุนจดทะเบียนไม่น้อยกว่า ๒,๕๐๐,๐๐๐ บาท "
            "(สองล้านห้าแสนบาทถ้วน)\n"
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
