"""Unit tests for wizard step ↔ TOR section payload mapping."""

from app.domain.wizard_payload import normalize_step_payload, sections_to_step_data


def test_step3_empty_objectives_keeps_one_blank_row():
    data = sections_to_step_data(3, [], {})
    assert data["objectives"] == [""]


def test_step5_empty_qualifications_keeps_one_blank_row():
    data = sections_to_step_data(5, [], {})
    assert data["qualifications"] == [""]


def test_step3_splits_persisted_objectives():
    data = sections_to_step_data(
        3,
        [{"section_key": "s2", "content": "ข้อ 1\nข้อ 2"}],
        {},
    )
    assert data["objectives"] == ["ข้อ 1", "ข้อ 2"]


def test_step1_rebuilds_from_project_metadata():
    data = sections_to_step_data(
        1,
        [],
        {
            "name": "โครงการทดสอบ",
            "ministry": "กระทรวงดิจิทัลฯ",
            "budget": 1_000_000,
            "project_type": "it",
            "template_id": None,
        },
    )
    assert data["project_name"] == "โครงการทดสอบ"
    assert data["budget"] == 1_000_000
    assert data["project_type"] == "it"


def test_step4_empty_scope_keeps_placeholder_row():
    data = sections_to_step_data(4, [], {})
    assert data["scope_items"] == [{"title": "", "details": ""}]
    assert data["deliverables"] == [""]


def test_normalize_step1_duration_and_location():
    payload = normalize_step_payload(
        1,
        {"duration_days": 90, "location": "กรุงเทพมหานคร", "project_name": "โครงการทดสอบ"},
    )
    assert "90" in payload["s5"]
    assert payload["s7"] == "กรุงเทพมหานคร"
    assert payload["project_name"] == "โครงการทดสอบ"


def test_normalize_step2_description():
    payload = normalize_step_payload(2, {"description": "ระบบเดิมไม่รองรับปริมาณงาน"})
    assert payload["s1"] == "ระบบเดิมไม่รองรับปริมาณงาน"


def test_normalize_step3_objectives_list():
    payload = normalize_step_payload(3, {"objectives": ["เพิ่มประสิทธิภาพ", "ลดขั้นตอน"]})
    assert "- เพิ่มประสิทธิภาพ" in payload["s2"]
    assert "- ลดขั้นตอน" in payload["s2"]


def test_normalize_step4_scope_and_deliverables():
    payload = normalize_step_payload(
        4,
        {
            "scope_items": [{"title": "พัฒนาระบบ", "details": "ออกแบบและติดตั้ง"}],
            "deliverables": ["เอกสารออกแบบ"],
        },
    )
    assert payload["s4.1"] == "พัฒนาระบบ\nออกแบบและติดตั้ง"
    assert "- เอกสารออกแบบ" in payload["s4.8"]
    assert "ผลงานส่งมอบ" in payload["s4"]


def test_normalize_step5_qualifications_and_capital():
    payload = normalize_step_payload(
        5,
        {"qualifications": ["เป็นนิติบุคคล"], "paid_up_capital": 1000000},
    )
    assert "- เป็นนิติบุคคล" in payload["s3"]
    assert "1,000,000" in payload["s3"]


def test_normalize_step6_budget_payment_and_penalty():
    payload = normalize_step_payload(
        6,
        {
            "budget_breakdown": [{"item": "ฮาร์ดแวร์", "amount": "100000"}],
            "payment_schedule": [{"percentage": 50, "deliverable": "งวดแรก"}],
            "penalty_rate": 0.1,
            "warranty": "รับประกัน 1 ปี",
            "duration_days": 120,
        },
    )
    assert "ฮาร์ดแวร์" in payload["s6"]
    assert "งวดที่ 1" in payload["s8"]
    assert payload["s9"] == "รับประกัน 1 ปี"
    assert "0.1" in payload["s10"]
    assert "120" in payload["s5"]


def test_normalize_step6_falls_back_to_section_keys():
    payload = normalize_step_payload(
        6,
        {"s6": "งบประมาณรวม", "s8": "งวดเดียว", "s10": "ค่าปรับร้อยละ 0.1", "s5": "90 วัน"},
    )
    assert payload["s6"] == "งบประมาณรวม"
    assert payload["s8"] == "งวดเดียว"
    assert payload["s10"] == "ค่าปรับร้อยละ 0.1"
    assert payload["s5"] == "90 วัน"


def test_normalize_step7_copies_known_keys():
    payload = normalize_step_payload(7, {"s11": "เกณฑ์ราคา", "s13": "เงื่อนไขอื่น"})
    assert payload["s11"] == "เกณฑ์ราคา"
    assert payload["s13"] == "เงื่อนไขอื่น"


def test_normalize_as_text_handles_dicts_and_detail_only_rows():
    payload = normalize_step_payload(
        3,
        {"objectives": [{"details": "รายละเอียดอย่างเดียว"}, {"title": "หัวข้ออย่างเดียว"}]},
    )
    assert "- รายละเอียดอย่างเดียว" in payload["s2"]
    assert "- หัวข้ออย่างเดียว" in payload["s2"]
    nested = normalize_step_payload(2, {"description": {"note": "บริบท"}})
    assert "บริบท" in nested["s1"]


def test_normalize_step4_plain_string_items_and_s4_fallback():
    items = normalize_step_payload(4, {"scope_items": ["งานติดตั้ง"]})
    assert items["s4.1"] == "งานติดตั้ง"
    fallback = normalize_step_payload(4, {"s4": "ขอบเขตงานทั้งก้อน"})
    assert fallback["s4"] == "ขอบเขตงานทั้งก้อน"


def test_normalize_step1_keeps_existing_s5():
    payload = normalize_step_payload(1, {"s5": "ระยะเวลา 30 วัน"})
    assert payload["s5"] == "ระยะเวลา 30 วัน"


def test_sections_to_step_data_steps_2_6_7_8():
    step2 = sections_to_step_data(2, [{"section_key": "s1", "content": "หลักการ"}])
    assert step2["description"] == "หลักการ"
    step6 = sections_to_step_data(
        6,
        [
            {"section_key": "s6", "content": "งบ"},
            {"section_key": "s8", "content": "งวด"},
            {"section_key": "s9", "content": "ประกัน"},
        ],
    )
    assert step6["warranty"] == "ประกัน"
    step7 = sections_to_step_data(7, [{"section_key": "s11", "content": "เกณฑ์"}])
    assert "s11" in step7
    assert sections_to_step_data(8, []) == {"exported": False}


def test_sections_to_step_data_reads_sub_keys_and_duration():
    data = sections_to_step_data(
        4,
        [
            {"section_key": "s4", "sub_key": "s4.1", "content": "สรุป\nรายละเอียด"},
            {"section_key": "s4", "content": "ภาพรวม"},
        ],
    )
    assert data["scope_items"][0]["title"] == "สรุป"
    duration = sections_to_step_data(1, [{"section_key": "s5", "content": "ระยะเวลา 45 วัน"}], {})
    assert duration["duration_days"] == 45


def test_normalize_list_title_and_details_and_numbers():
    payload = normalize_step_payload(
        3,
        {"objectives": [{"title": "งานหลัก", "details": "ติดตั้งระบบ"}, 12, None]},
    )
    assert "- งานหลัก: ติดตั้งระบบ" in payload["s2"]
    assert "- 12" in payload["s2"]


def test_normalize_step6_schedule_plain_strings():
    payload = normalize_step_payload(
        6,
        {"payment_schedule": ["งวดแรก 50%", "งวดสุดท้าย 50%"], "penalty_rate": ""},
    )
    assert "งวดแรก 50%" in payload["s8"]


def test_sections_to_step_data_step5_capital_and_unknown_step():
    step5 = sections_to_step_data(
        5,
        [{"section_key": "s3", "content": "เป็นนิติบุคคล\nทุนจดทะเบียนชำระแล้วไม่น้อยกว่า 2,500,000 บาท"}],
    )
    assert "เป็นนิติบุคคล" in step5["qualifications"]
    assert step5["paid_up_capital"] == 2500000
    unknown = sections_to_step_data(99, [{"section_key": "s1", "content": "อื่นๆ"}])
    assert unknown["s1"] == "อื่นๆ"


def test_sections_to_step_data_step4_from_s4_and_numeric_sub_key():
    from_s4 = sections_to_step_data(4, [{"section_key": "s4", "content": "ขอบเขตทั้งหมด"}])
    assert from_s4["scope_items"][0]["title"] == "ขอบเขตงาน"
    numeric = sections_to_step_data(
        4,
        [{"section_key": "s4", "sub_key": "1", "content": "หัวข้อย่อย"}],
    )
    assert numeric["scope_items"][0]["title"] == "หัวข้อย่อย"
