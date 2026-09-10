"""Warranty Drafter — §9 การรับประกัน."""

from __future__ import annotations

from app.orchestrator.agents.base import formal_register, BaseDraftingAgent


class WarrantyDraftingAgent(BaseDraftingAgent):
    """Drafts §9 การรับประกัน."""

    section_key = "s9"
    section_name_th = "การรับประกัน"
    section_name_en = "Warranty"

    def get_system_prompt(self, category: str | None = None) -> str:
        return (
            formal_register(category, self.section_key)
            + "คุณกำลังร่างส่วน «การรับประกัน» ของเอกสารกำหนดขอบเขตงาน\n\n"
            "ข้อกำหนด:\n"
            "- ระยะเวลารับประกัน — ไม่น้อยกว่า [X] ปี นับจากวันตรวจรับงวดสุดท้าย\n"
            "- ขอบเขตการรับประกัน — ครอบคลุมอะไรบ้าง\n"
            "- วิธีการเรียกร้อง — ขั้นตอนการแจ้ง\n"
            "- ระยะเวลาแก้ไข — ภายในกี่วันนับจากวันที่ได้รับแจ้ง\n"
            "- หลักประกันสัญญา — จำนวนและระยะเวลา\n\n"
            "กฎหมายที่เกี่ยวข้อง: ระเบียบกระทรวงการคลังฯ ข้อว่าด้วยการรับประกันผลงาน\n"
            "ห้ามซ้ำขอบเขตงานหรืองวดจ่าย — มีเฉพาะเงื่อนไขการรับประกัน\n"
        )
