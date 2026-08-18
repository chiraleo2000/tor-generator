"""Location Drafter — §7 สถานที่ดำเนินการ."""

from __future__ import annotations

from app.orchestrator.agents.base import THAI_FORMAL_REGISTER_PREAMBLE, BaseDraftingAgent


class LocationDraftingAgent(BaseDraftingAgent):
    """Drafts §7 สถานที่ดำเนินการ."""

    section_key = "s7"
    section_name_th = "สถานที่ดำเนินการ"
    section_name_en = "Location"

    def get_system_prompt(self) -> str:
        return (
            THAI_FORMAL_REGISTER_PREAMBLE
            + "คุณกำลังร่างส่วน «สถานที่ดำเนินการ» (§7) ของเอกสาร TOR\n\n"
            "ต้องระบุ:\n"
            "1. สถานที่ปฏิบัติงานหลัก (ชื่อหน่วยงาน ที่อยู่)\n"
            "2. สถานที่ติดตั้ง/ส่งมอบ (ถ้าต่างจากสถานที่ปฏิบัติงาน)\n"
            "3. ขอบเขตพื้นที่ที่ผู้รับจ้างต้องเข้าปฏิบัติงาน\n"
            "4. เงื่อนไขการเข้าพื้นที่ (บัตรผ่าน เวลาทำการ ความปลอดภัย)\n\n"
            "เขียนเป็นย่อหน้าสั้น ชัดเจน เป็นภาษาราชการ\n"
        )
