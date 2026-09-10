"""Other Conditions Drafter — §13 เงื่อนไขอื่น ๆ."""

from __future__ import annotations

from app.orchestrator.agents.base import formal_register, BaseDraftingAgent


class ConditionsDraftingAgent(BaseDraftingAgent):
    """Drafts §13 เงื่อนไขอื่น ๆ."""

    section_key = "s13"
    section_name_th = "เงื่อนไขอื่น ๆ"
    section_name_en = "Other Conditions"

    def get_system_prompt(self, category: str | None = None) -> str:
        return (
            formal_register(category, self.section_key)
            + "คุณกำลังร่างส่วน «เงื่อนไขอื่น ๆ» ของเอกสารกำหนดขอบเขตงาน\n\n"
            "เงื่อนไขที่ควรระบุ:\n"
            "๑. หลักประกันสัญญา — ร้อยละ ๕ ของวงเงินตามสัญญา\n"
            "๒. เงื่อนไขการจัดทำสัญญา\n"
            "๓. สิทธิของหน่วยงาน — สงวนสิทธิ์ในการยกเลิกหรือไม่พิจารณา\n"
            "๔. เงื่อนไขอื่นตามระเบียบกระทรวงการคลังฯ\n\n"
            "ใช้หัวข้อย่อยตามสาระ ห้ามพิมพ์ป้ายช่องข้อมูลเป็นหัวข้อ\n"
            "ห้ามซ้ำเนื้อหาจากหมวดอื่น — มีเฉพาะเงื่อนไขสัญญา ลิขสิทธิ์ และความลับ\n"
        )
