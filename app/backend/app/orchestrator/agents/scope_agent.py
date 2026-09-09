"""Agent 4: Scope Drafter — §4 ขอบเขตของงาน.

Specialized agent for drafting the Scope of Work section of TOR documents.
This is typically the longest and most detailed section, supporting up to
14 subsections covering technical requirements, deliverables, and specifications.
"""

from __future__ import annotations

from app.orchestrator.agents.base import THAI_FORMAL_REGISTER_PREAMBLE, BaseDraftingAgent


class ScopeDraftingAgent(BaseDraftingAgent):
    """Drafts §4 ขอบเขตของงาน — the scope of work section of a TOR."""

    section_key = "s4"
    section_name_th = "ขอบเขตของงาน"
    section_name_en = "Scope"

    def get_system_prompt(self, category: str | None = None) -> str:
        from app.domain.section_profile import profile_for_project
        from app.domain.tor_draft_hints import hint_for

        profile = profile_for_project(category)
        lines = []
        for index, item in enumerate(profile.scope_subsections, start=1):
            lines.append(f"4.{index} {item.title}")
        listed = "\n".join(lines) if lines else "(ไม่มีหัวข้อย่อย)"
        hint = hint_for("s4", profile.category)
        return (
            THAI_FORMAL_REGISTER_PREAMBLE
            + "คุณกำลังร่างส่วน «ขอบเขตของงาน» ของเอกสาร TOR\n\n"
            f"ประเภทงาน: {profile.label}\n"
            "เขียนเฉพาะหัวข้อย่อยต่อไปนี้ตามลำดับ ห้ามเพิ่มหัวข้อที่ไม่มีในรายการ:\n\n"
            f"{listed}\n\n"
            f"แนวทาง: {hint}\n\n"
            "=== ข้อกำหนดด้านรูปแบบ ===\n"
            "- เขียนแยกเป็นหัวข้อย่อยตามลำดับด้านบน (ข้ามหัวข้อที่ไม่มีข้อมูล)\n"
            "- เขียนรายละเอียดทางเทคนิคให้ชัดเจน วัดผลได้\n"
            "- ใช้ตารางมาร์กดาวน์สำหรับรายการที่มีหลายแถว หัวคอลัมน์เป็นภาษาไทย\n"
            "- ระบุหน่วยนับ จำนวน และคุณลักษณะที่ชัดเจน\n"
            "- ห้ามระบุยี่ห้อ/รุ่นเฉพาะ ยกเว้นจะมีคำว่า «หรือเทียบเท่า»\n"
            "- ห้ามใช้คำกว้างที่ไม่สามารถตรวจสอบได้ เช่น «คุณภาพดี» «ทันสมัย»\n"
            "- ห้ามใช้ป้าย As-Is หรือ To-Be\n"
            "- ต้องสอดคล้องกับวัตถุประสงค์ และงบประมาณ\n"
            "- เขียนเป็นภาษาไทยเท่านั้น\n"
        )
