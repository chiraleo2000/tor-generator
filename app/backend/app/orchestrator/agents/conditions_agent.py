"""Other Conditions Drafter — §13 เงื่อนไขอื่น ๆ."""

from __future__ import annotations

from app.orchestrator.agents.base import THAI_FORMAL_REGISTER_PREAMBLE, BaseDraftingAgent


class ConditionsDraftingAgent(BaseDraftingAgent):
    """Drafts §13 เงื่อนไขอื่น ๆ."""

    section_key = "s13"
    section_name_th = "เงื่อนไขอื่น ๆ"
    section_name_en = "Other Conditions"

    def get_system_prompt(self) -> str:
        return (
            THAI_FORMAL_REGISTER_PREAMBLE
            + "คุณกำลังร่างส่วน «เงื่อนไขอื่น ๆ» (§13) ของเอกสาร TOR\n\n"
            "เงื่อนไขที่ควรระบุ:\n"
            "1. หลักประกันสัญญา — ร้อยละ 5 ของวงเงินตามสัญญา\n"
            "2. เงื่อนไขการจัดทำสัญญา\n"
            "3. สิทธิของหน่วยงาน — สงวนสิทธิ์ในการยกเลิก/ไม่พิจารณา\n"
            "4. เงื่อนไขอื่นตามระเบียบกระทรวงการคลังฯ\n\n"
            "กฎหมายที่เกี่ยวข้อง:\n"
            "- พ.ร.บ. 2560\n"
            "- ระเบียบกระทรวงการคลังฯ ข้อ 167-171 (หลักประกัน)\n"
        )
