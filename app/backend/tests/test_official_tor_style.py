from app.orchestrator.agents.background_agent import BackgroundDraftingAgent
from app.orchestrator.agents.evaluation_agent import EvaluationDraftingAgent
from app.orchestrator.agents.payment_agent import PaymentDraftingAgent
from app.orchestrator.agents.qualifications_agent import QualificationsDraftingAgent
from app.orchestrator.agents.scope_agent import ScopeDraftingAgent
from app.services.draft_chat_service import _section_prompt_context
from app.services.thai_draft import SUBSTANCE_RULES, THAI_ONLY_RULES, official_tor_style_block
from app.orchestrator.agents.base import THAI_FORMAL_REGISTER_PREAMBLE


def test_official_style_block_forbids_scaffolding_and_english():
    block = official_tor_style_block("hire_develop", "s1")
    assert "ผู้รับจ้าง" in block
    assert "ห้ามพิมพ์เลขหมวดนำหน้า" in block
    assert "ประวัติ/สถานการณ์ปัจจุบันของระบบเดิม" in block
    assert "จึงมีความจำเป็น" in block
    assert "Server" in block
    assert "Digital Government" in block
    assert "| งวดที่ |" in official_tor_style_block("hire_develop", "s8")
    payment = PaymentDraftingAgent().get_system_prompt("hire_develop")
    assert "| ผลงานที่ต้องส่งมอบ |" in payment
    assert "[deliverable]" not in payment.lower()


def test_payment_and_eval_prompts_use_thai_tables():
    payment = PaymentDraftingAgent().get_system_prompt("hire_develop")
    assert "ผลงานที่ต้องส่งมอบ" in payment
    assert "[deliverable]" not in payment.lower()
    evaluation = EvaluationDraftingAgent().get_system_prompt("hire_develop")
    eval_body = evaluation.replace(THAI_ONLY_RULES, "")
    assert "Price Only" not in eval_body
    assert "เกณฑ์ราคาประกอบเกณฑ์คุณภาพ" in evaluation


def test_qualifications_prompt_lists_profile_headings():
    prompt = QualificationsDraftingAgent().get_system_prompt("hire_develop")
    assert "บุคลากรหลัก" in prompt
    assert "๓.๑" not in prompt
    assert "คุณสมบัติทั่วไปตามกฎหมาย" in prompt


def test_scope_prompt_lists_profile_titles_without_forced_numbers():
    prompt = ScopeDraftingAgent().get_system_prompt("hire_develop")
    assert "๔.๑" not in prompt
    assert "4.1 " not in prompt
    assert "ภาพรวมระบบ" in prompt or "หน้าที่การทำงาน" in prompt


def test_background_prompt_bans_meta_headings():
    prompt = BackgroundDraftingAgent().get_system_prompt("hire_develop")
    assert "ห้ามใช้หัวข้อย่อย" in prompt or "ไม่มีหัวข้อย่อย" in prompt
    assert "จึงมีความจำเป็นต้อง" in prompt


def test_objectives_prompt_requires_json_fields():
    from app.orchestrator.agents.objectives_agent import ObjectivesDraftingAgent

    prompt = ObjectivesDraftingAgent().get_system_prompt("hire_develop")
    assert '"mainObj"' in prompt
    assert '"users"' in prompt
    assert '"kpi"' in prompt
    assert "กลุ่มผู้ใช้" in prompt or "users" in prompt
    assert "ตัวชี้วัด" in prompt
    block = official_tor_style_block("hire_develop", "s2")
    assert "mainObj" in block
    assert "kpi" in block


def test_substance_rules_and_style_block_anti_dupe():
    assert "ข้อบังคับสาระและขอบเขต" in SUBSTANCE_RULES
    assert "ห้ามคัดลอกย่อหน้าจากหมวดอื่น" in SUBSTANCE_RULES
    assert "เป็นเพดาน ไม่ใช่เป้าขั้นต่ำ" in SUBSTANCE_RULES
    assert "ขยายรายละเอียด" not in SUBSTANCE_RULES
    assert "ต้องมีหลายย่อหน้า" not in SUBSTANCE_RULES
    block = official_tor_style_block("hire_develop", "s4")
    assert "เจ้าของสาระต่อหมวด" in block
    assert "ขอบเขต" in block
    preamble = THAI_FORMAL_REGISTER_PREAMBLE
    assert "อยู่เฉพาะในขอบเขตหมวด" in preamble
    assert "LENGTH_RULES" not in preamble


def test_chat_section_prompt_avoids_english_field_keys():
    prompt = _section_prompt_context(
        "s1",
        {"s1": {"content": "ความเป็นมา", "status": "filled"}},
        "",
        "hire_develop",
    )
    assert "ขึ้นต้นแต่ละหัวข้อด้วยบรรทัด ### ตามรหัส" not in prompt
    assert "ผู้รับจ้าง" in prompt
    assert "ห้ามพิมพ์เลขหมวดนำหน้า" in prompt
