"""Unit tests for labelled-paste slot extraction."""

from app.services.intake_heuristic import extract_slot_contents, overlay_filled_slots


def test_extract_slot_contents_reads_codes():
    text = (
        "ความเป็นมา (s1): กรมบัญชีกลางจัดซื้อระบบ\n"
        "วัตถุประสงค์ (s2): เพื่อบริหารสัญญา\n"
        "ระยะเวลาดำเนินการ (s5): 180 วัน\n"
        "วงเงินงบประมาณ (s6): 2500000 บาท"
    )
    found = extract_slot_contents(text)
    assert "กรมบัญชีกลาง" in found["s1"]
    assert "บริหารสัญญา" in found["s2"]
    assert "180" in found["s5"]
    assert "2500000" in found["s6"]


ECT_CHATBOT_PACK = """
โครงการพัฒนาระบบตอบกลับอัตโนมัติคลังความรู้ปัญญาประดิษฐ์ (ECT AI Chatbot) ของสำนักงาน กกต. วงเงินงบประมาณ 15,000,000 บาท (ราคากลาง 15,075,250 บาท) ด้วยวิธี e-bidding กำหนดระยะเวลาดำเนินงาน 360 วัน โดยมีแนวทางการพัฒนาระบบและกฎระเบียบข้อบังคับตามขอบเขตงาน (TOR) ดังนี้
แนวทางการพัฒนาระบบและสถาปัตยกรรม (3 ระบบหลัก)
 - โครงสร้างพื้นฐาน: พัฒนาแบบ Containerized บน Kubernetes ติดตั้งบนบริการคลาวด์ในประเทศ
 - ระบบฐานข้อมูลความรู้ร่วม (Knowledge Base): รองรับข้อมูลเริ่มต้น 1.5 TB
 - ระบบ ECT AI Chatbot สำหรับบุคลากรภายใน: ใช้สถาปัตยกรรม RAG แบบ Strict Grounding
แผนการส่งมอบงานและการจ่ายเงิน (4 งวดงาน)
 - งวดที่ 1 (ภายใน 60 วัน, 15%): ส่งมอบแผนงานโครงการ
 - งวดที่ 2 (ภายใน 240 วัน, 35%): ติดตั้ง Cloud และ 3 ระบบหลัก
กฎระเบียบ มาตรฐาน และข้อบังคับสำคัญ
 - คุณสมบัติผู้ยื่นข้อเสนอและทีมงาน: เป็นนิติบุคคลไทยอายุ 3 ปี ทุนจดทะเบียนชำระแล้ว 3 ล้านบาท มีบุคลากรหลักครบ 8 ตำแหน่ง
 - เกณฑ์การคัดเลือก (Price Performance): สัดส่วนราคา 20% และข้อเสนอด้านเทคนิค 80%
 - ความมั่นคงปลอดภัยและ External LLM: ปฏิบัติตาม PDPA เข้ารหัส AES-256 และ TLS 1.3
 - กรรมสิทธิ์ SLA และ Exit Strategy: ข้อมูลเป็นกรรมสิทธิ์ของ กกต. ค่าปรับส่งมอบงานล่าช้า 0.10%/วัน
"""


def test_extract_unstructured_ect_chatbot_pack():
    found = extract_slot_contents(ECT_CHATBOT_PACK)
    assert found["s1"].startswith("โครงการพัฒนาระบบตอบกลับอัตโนมัติ")
    assert "15,000,000" in found["s6"]
    assert "360" in found["s5"]
    assert "กกต" in found["s7"]
    assert "Kubernetes" in found["s4.1"]
    assert "งวดที่ 1" in found["s8"]
    assert "นิติบุคคลไทย" in found["s3"]
    assert "Price Performance" in found["s11"] or "80%" in found["s11"]
    assert "PDPA" in found["s4.14"]
    assert "กรรมสิทธิ์" in found["s13"]
    assert "ค่าปรับ" in found["s10"]
    assert found.get("s4")
    assert "SLA" in found["s9"] or "กรรมสิทธิ์" in found["s9"]
    assert "Kubernetes" in found["s4.3"]


def test_extract_full_ect_ai_chatbot_fixture():
    from pathlib import Path

    text = Path(__file__).with_name("fixtures").joinpath("ect_ai_chatbot_pack.txt").read_text(
        encoding="utf-8"
    )
    found = extract_slot_contents(text)
    for key in ("s1", "s2", "s5", "s6", "s7", "s4.1", "s8", "s3", "s11", "s4.14", "s13", "s10"):
        assert found.get(key), f"expected {key} filled from ECT pack"
    assert found.get("s12")
    assert found.get("s4.6")
    assert found.get("s4.13")
    assert "กกต" in found["s4.6"] or "Web Chat" in found["s4.6"]


def test_connect_alone_does_not_inject_ect_sample():
    """Budget/TOR forms that merely say เชื่อมต่อ must not get กกต. Widget sample text."""
    text = (
        "หลักการและเหตุผล\n"
        "หน่วยงานต้องพัฒนาระบบที่เชื่อมต่อกับฐานข้อมูลภายใน\n"
        "วัตถุประสงค์\n"
        "เพื่อเชื่อมต่อข้อมูลระหว่างส่วนกลางและส่วนภูมิภาค\n"
        "งบประมาณรวม .......... 1,000,000............ บาท\n"
        "จำนวน 120 วัน\n"
        "ระยะเวลาดำเนินงาน\n"
        "จำนวน 120 วัน\n"
        "ชื่อสถานที่ตั้ง\n"
        "กรุงเทพมหานคร\n"
    )
    found = extract_slot_contents(text)
    assert "1,000,000" in found["s6"]
    assert found["s5"] == "120 วัน"
    assert "กรุงเทพมหานคร" in found["s7"]
    s46 = found.get("s4.6") or ""
    assert "กกต" not in s46
    assert "Zero Data Retention" not in s46
    assert "Web Chat Widget" not in s46


def test_extract_skk_budget_form_fixture():
    from pathlib import Path

    path = Path(__file__).with_name("fixtures").joinpath("skk_budget_form_pack.txt")
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    found = extract_slot_contents(text)
    assert "ภายใต้สภาวะการเปลี่ยนแปลง" in found["s1"]
    assert "เพื่อออกแบบและพัฒนาระบบ" in found["s2"]
    assert found["s5"] == "270 วัน"
    assert "5,730,000" in found["s6"]
    assert "มหาวิทยาลัยเกษตรศาสตร์" in found["s7"]
    assert "Web Application" in found["s4.1"]
    assert "ระบบงาน" in found["s4.2"]
    assert "แท็บเล็ต" in found["s4.4"] or "Hardware" in found["s4.4"]
    assert "เชื่อมโยง" in (found.get("s4.6") or "")
    assert "กกต" not in (found.get("s4.6") or "")
    assert "Zero Data Retention" not in (found.get("s4.6") or "")
    assert "ผู้จัดการโครงการ" in found["s4.10"] or "Programmer" in found["s4.10"]


def test_short_mention_of_project_does_not_fake_background():
    found = extract_slot_contents("เนื้อหาโครงการยังไม่ติดรหัสช่อง")
    assert "s1" not in found
    assert "s6" not in found


def test_extract_inline_colon_labels_without_newlines():
    text = (
        "ความเป็นมา: กรมบัญชีกลางมีความจำเป็นต้องจัดซื้อระบบสารสนเทศบริหารสัญญาจัดซื้อจัดจ้าง "
        "วัตถุประสงค์: เพื่อให้เจ้าหน้าที่พัสดุบริหารสัญญา "
        "วงเงินงบประมาณ: 5,000,000 บาท จากงบดำเนินงานประจำปี "
        "ระยะเวลาดำเนินการ: 180 วัน นับจากวันที่ลงนามในสัญญา "
        "สถานที่ดำเนินการ: สำนักงานปลัดกระทรวง กรุงเทพมหานคร "
        "ขอบเขตงานหลัก: วิเคราะห์ความต้องการ พัฒนาโมดูลบริหารสัญญา"
    )
    found = extract_slot_contents(text)
    assert "กรมบัญชีกลาง" in found["s1"]
    assert "เจ้าหน้าที่พัสดุ" in found["s2"]
    assert "5,000,000" in found["s6"]
    assert "180" in found["s5"]
    assert "สำนักงานปลัดกระทรวง" in found["s7"]
    assert "โมดูลบริหารสัญญา" in found["s4.1"]


def test_overlay_filled_slots_keeps_paste_facts():
    base = {
        "s1": {"content": "จากเอกสาร", "status": "filled", "sources": ["paste"]},
        "s10": {"content": "", "status": "gap", "sources": []},
    }
    incoming = {
        "s1": {"content": "จากโมเดล", "status": "filled", "sources": ["llm"]},
        "s10": {"content": "พ.ร.บ.", "status": "reference_only", "sources": ["rag"]},
    }
    merged = overlay_filled_slots(base, incoming)
    assert merged["s1"]["content"] == "จากเอกสาร"
    assert merged["s10"]["status"] == "reference_only"


def test_repair_moves_qualifications_out_of_duration():
    from app.services.intake_heuristic import repair_misplaced_slots

    slots = {
        "s3": {"content": "", "status": "gap", "sources": []},
        "s5": {
            "content": "นิติบุคคลไทยจัดตั้งมาแล้วไม่น้อยกว่า 3 ปี ทุนจดทะเบียนชำระเต็ม",
            "status": "filled",
            "sources": ["llm"],
        },
    }
    fixed = repair_misplaced_slots(slots)
    assert fixed["s5"]["status"] == "gap"
    assert "นิติบุคคล" in fixed["s3"]["content"]
    assert fixed["s3"]["status"] == "filled"


def test_extract_reads_semantic_scope_codes_and_headings():
    text = (
        "(functional): พัฒนาโมดูลลงทะเบียนและรายงานผล\n"
        "การทดสอบระบบและเกณฑ์การยอมรับ\n"
        "ต้องผ่าน UAT และทดสอบความปลอดภัยก่อนขึ้นระบบจริง\n"
        "งวดงานและการจ่ายเงิน\n"
        "แบ่ง 3 งวด\n"
    )
    found = extract_slot_contents(text)
    assert "โมดูลลงทะเบียน" in found.get("functional", "")
    assert "UAT" in found.get("testing", "") or "UAT" in found.get("s4.8", "")


def test_remap_legacy_s4_onto_hire_develop_scope():
    from app.domain.slots import remap_extracted_slots

    remapped = remap_extracted_slots(
        {
            "s4.3": "งานหลักพัฒนาระบบลงทะเบียน",
            "s4.8": "ส่งมอบซอร์สโค้ดและคู่มือ",
            "s4.6": "เชื่อมโยง API กับระบบเดิม",
            "s4.1": "สรุปขอบเขตจ้างพัฒนา",
        },
        "hire_develop",
    )
    assert "พัฒนาระบบลงทะเบียน" in remapped["functional"]
    assert "ซอร์สโค้ด" in remapped["deliverable_docs"]
    assert "API" in remapped["integration"]
    assert remapped["functional"]


def test_mixed_develop_and_hardware_pack_suggests_hire_develop():
    from app.services.intake_heuristic import suggest_procurement_category

    skk = (
        "โครงการพัฒนาระบบสารสนเทศของสกก. จ้างพัฒนาเว็บแอปพลิเคชัน "
        "พร้อมจัดหาเครื่องแม่ข่ายและแท็บเล็ตสำหรับเจ้าหน้าที่"
    )
    assert suggest_procurement_category(skk, "buy_goods") == "hire_develop"
    goods = "จัดซื้อเครื่องคอมพิวเตอร์และครุภัณฑ์โต๊ะเก้าอี้ จำนวน 20 ชุด"
    assert suggest_procurement_category(goods, "buy_goods") is None

