"""Agent 7: Budget Drafter — §6 วงเงินงบประมาณ (Budget).

Specialized agent for drafting the Budget section of TOR documents.
Focuses on budget justification, cost breakdown, and alignment with scope.
Budget calculations are subject to Rule Engine validation.

This section contains budget calculations and is subject to mandatory human review.

Requirements: 5.6, 6.6, 12.1, 12.7, 16.5
"""

from __future__ import annotations

from typing import Any

from app.domain.consultant_budget import suggest_budget
from app.orchestrator.agents.base import BaseDraftingAgent, formal_register

_LOCK_RULE = (
    "\n=== ตารางที่คำนวณแล้ว ห้ามเปลี่ยนตัวเลข ===\n"
    "ถ้ามีตารางงบที่คำนวณจากอัตราแล้ว ให้คัดลอกตัวเลขทุกช่องตามตาราง "
    "ห้ามเปลี่ยนตัวเลข ห้ามปัดใหม่ และห้ามแทนที่ด้วยอัตราข้าราชการ "
    "บุคลากรในหน่วยงานของรัฐ สถาบันของรัฐ หรือราคาที่ไม่มีในตาราง\n"
    "ใบประมาณการมีห้าหมวดคือ ทรัพยากรบุคคล อุปกรณ์ การจัดซื้อจัดจ้าง "
    "การจ้างที่ปรึกษา และค่าอบรม "
    "ค่าอบรมแยกอาหาร อาหารว่าง เอกสาร และสถานที่\n"
    "ทีมที่ปรึกษาสลับวุฒิปริญญาโทแล้วปริญญาเอก ใช้อัตราภาคเอกชน "
    "หากไม่ได้กำหนดอายุงานให้ใช้ 2 ปี และเลือกแถวราคาต่ำสุดที่เข้าเงื่อนไข "
    "สถานที่อบรมค่าเริ่มต้นเป็นโรงแรมหรือสถานที่เอกชน "
    "ครึ่งวันคิดอาหาร 1 มื้อและอาหารว่าง 1 มื้อ "
    "เต็มวันคิดอาหาร 2 มื้อและอาหารว่าง 2 มื้อ "
    "เอกสารคิดทุกครั้งตามจำนวนผู้เข้าอบรม\n"
)


class BudgetDraftingAgent(BaseDraftingAgent):
    """Drafts §6 วงเงินงบประมาณ — the budget section of a TOR."""

    section_key = "s6"
    section_name_th = "วงเงินงบประมาณ"
    section_name_en = "Budget"

    def get_system_prompt(self, category: str | None = None) -> str:
        """Return the system prompt for Budget section drafting."""
        return (
            formal_register(category, self.section_key)
            + "คุณกำลังร่างส่วน «วงเงินงบประมาณ» ของเอกสารกำหนดขอบเขตงาน\n\n"
            "⚠️ ส่วนนี้มีตัวเลขงบประมาณ — ต้องถูกต้องแม่นยำ\n\n"
            "=== แนวทางการเขียนส่วนงบประมาณ ===\n"
            "ส่วนนี้ต้องประกอบด้วย:\n"
            "1. วงเงินงบประมาณรวม — ระบุจำนวนเงินรวมทั้งโครงการ\n"
            "2. ที่มาของงบประมาณ — แหล่งเงิน (งบประมาณแผ่นดิน/เงินรายได้/เงินกู้ ฯลฯ)\n"
            "3. รายละเอียดค่าใช้จ่าย — แยกตามหมวด/ประเภท\n"
            "4. เงื่อนไขด้านงบประมาณ — รวม/ไม่รวม VAT ค่าขนส่ง ฯลฯ\n\n"
            "=== ข้อกำหนดทางกฎหมาย ===\n"
            "- ต้องระบุวงเงินงบประมาณเป็นตัวเลขและตัวอักษร\n"
            "- ต้องระบุว่ารวมหรือไม่รวมภาษีมูลค่าเพิ่ม\n"
            "- งบประมาณต้องสอดคล้องกับขอบเขตงาน (§4)\n"
            "- ต้องเป็นราคากลางที่สมเหตุสมผล\n"
            "- ระบุวันที่ใช้ในการคำนวณราคากลาง\n\n"
            "=== ข้อกำหนดด้านรูปแบบ ===\n"
            "- ระบุจำนวนเงินทั้งตัวเลขและตัวอักษร\n"
            "  ตัวอย่าง: 10,000,000 บาท (สิบล้านบาทถ้วน)\n"
            "- ใช้ตารางสำหรับรายละเอียดค่าใช้จ่าย\n"
            "- ระบุว่ารวม VAT หรือไม่\n"
            "- หากมีหลายหมวด ให้แสดงยอดรวมแต่ละหมวดและยอดรวมทั้งหมด\n"
            "- ตัวเลขต้องสอดคล้องกัน (ผลรวมถูกต้อง)\n"
            "- ห้ามเล่าขอบเขตงานหรือความเป็นมา — มีเฉพาะวงเงินและราคากลาง\n\n"
            "=== ตัวอย่างโครงสร้าง ===\n"
            "วงเงินงบประมาณในการจัดซื้อ/จัดจ้างครั้งนี้ เป็นเงินทั้งสิ้น "
            "[X] บาท ([จำนวนเงินเป็นตัวอักษร]) รวมภาษีมูลค่าเพิ่มแล้ว\n"
            "โดยใช้จ่ายจากงบประมาณ [แหล่งเงิน] ประจำปีงบประมาณ พ.ศ. [ปี]\n\n"
            "รายละเอียดค่าใช้จ่ายโดยประมาณ:\n"
            "| ลำดับ | รายการ | จำนวน | หน่วยละ (บาท) | รวม (บาท) |\n"
            "| ๑ | ... | ... | ... | ... |\n"
            "| รวมทั้งสิ้น | | | | [X] |\n"
            + _LOCK_RULE
        )

    def build_user_message(
        self,
        user_input: dict[str, Any],
        rag_chunks: list,
        template: dict[str, Any] | None = None,
        validation_findings: list | None = None,
        human_feedback: str | None = None,
    ) -> str:
        """Build user message with budget formatting guidance.

        Enhances the base implementation by formatting budget amounts.
        """
        budget = user_input.get("budget") or user_input.get("งบประมาณ")
        if budget and isinstance(budget, (int, float)):
            user_input = {
                **user_input,
                "_budget_formatted": f"{int(budget):,} บาท",
            }
        locked = _locked_budget_table(user_input)
        if locked:
            user_input = {
                **user_input,
                "_locked_budget_table": locked,
                "_locked_budget_rule": "ห้ามเปลี่ยนตัวเลขในตารางนี้",
            }

        return super().build_user_message(
            user_input=user_input,
            rag_chunks=rag_chunks,
            template=template,
            validation_findings=validation_findings,
            human_feedback=human_feedback,
        )


def _has_calculation_input(user_input: dict[str, Any]) -> bool:
    if user_input.get("apply_calculated"):
        return True
    for key in ("team_size", "training_days", "attendees", "consultants"):
        value = user_input.get(key)
        if value:
            return True
    return False


def _calculation_from_input(user_input: dict[str, Any]) -> dict[str, Any]:
    supplied = user_input.get("calculated_budget")
    if isinstance(supplied, dict) and supplied:
        return supplied
    if not _has_calculation_input(user_input):
        return {}
    consultants = user_input.get("consultants")
    return suggest_budget(
        team_size=int(user_input.get("team_size") or 0),
        months=float(user_input.get("months") or 1),
        years=user_input.get("years"),
        training_days=float(user_input.get("training_days") or 0),
        day_part=str(user_input.get("day_part") or "full"),
        attendees=int(user_input.get("attendees") or 0),
        consultants=consultants if isinstance(consultants, list) else None,
    )


_LOCKED_BUDGET_ROWS = (
    ("ทรัพยากรบุคคล", "personnel"),
    ("อุปกรณ์", "equipment"),
    ("การจัดซื้อจัดจ้าง", "procurement"),
    ("การจ้างที่ปรึกษา", "consultant"),
    ("ค่าอาหาร", "food"),
    ("ค่าอาหารว่าง", "snack"),
    ("ค่าเอกสาร", "documents"),
    ("ค่าสถานที่", "venue"),
    ("ค่าอบรม", "training"),
    ("รวม", "total"),
)


def _table_amount(value: Any) -> int:
    return int(value or 0)


def _consultant_budget_line(person: dict[str, Any]) -> str:
    degree = person.get("degree_label") or person.get("degree")
    rate = _table_amount(person.get("monthly_rate"))
    amount = _table_amount(person.get("amount"))
    return (
        f"ที่ปรึกษาคนที่ {person.get('index')} {degree} อายุงาน {person.get('years')} ปี "
        f"อัตราเดือนละ {rate:,} บาท รวม {amount:,} บาท"
    )


def _locked_budget_table(user_input: dict[str, Any]) -> str:
    calculated = _calculation_from_input(user_input)
    if not calculated:
        return ""
    lines = [
        "ห้ามเปลี่ยนตัวเลขในตารางนี้",
        "| หมวด | จำนวนเงิน (บาท) |",
        "| --- | --- |",
    ]
    for label, key in _LOCKED_BUDGET_ROWS:
        lines.append(f"| {label} | {_table_amount(calculated.get(key)):,} |")
    consultants = calculated.get("consultants")
    if isinstance(consultants, list):
        lines.extend(_consultant_budget_line(person) for person in consultants)
    return "\n".join(lines)
