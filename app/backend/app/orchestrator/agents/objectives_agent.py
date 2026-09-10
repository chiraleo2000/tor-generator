"""Agent 2: Objectives Drafter — §2 วัตถุประสงค์ (Objectives).

Specialized agent for drafting the Objectives section of TOR documents.
Focuses on writing SMART objectives that align with the background section
and are measurable, achievable, and time-bound.

Requirements: 5.6, 12.1, 16.5
"""

from __future__ import annotations

from app.orchestrator.agents.base import formal_register, BaseDraftingAgent


class ObjectivesDraftingAgent(BaseDraftingAgent):
    """Drafts §2 วัตถุประสงค์ — the objectives section of a TOR."""

    section_key = "s2"
    section_name_th = "วัตถุประสงค์"
    section_name_en = "Objectives"

    def get_system_prompt(self, category: str | None = None) -> str:
        """Return the system prompt for Objectives section drafting."""
        return (
            formal_register(category, self.section_key)
            + "คุณกำลังร่างส่วน «วัตถุประสงค์» ของเอกสารกำหนดขอบเขตงาน\n\n"
            "=== แนวทางการเขียนส่วนวัตถุประสงค์ ===\n"
            "เขียนเป็นข้อย่อยเรียงลำดับ จำนวน ๓–๗ ข้อ "
            "ทุกข้อขึ้นต้นด้วย «เพื่อ» วัดผลได้ ผูกกับงานจริงในขอบเขต "
            "ห้ามใช้ข้อความกว้างอย่าง «เพื่อพัฒนาองค์กร»\n"
            "ห้ามพิมพ์ป้ายช่องข้อมูลเป็นหัวข้อ\n"
            "ห้ามเล่าความเป็นมาหรือรายละเอียดงาน — มีเฉพาะข้อ «เพื่อ»/วัตถุประสงค์\n"
        )
