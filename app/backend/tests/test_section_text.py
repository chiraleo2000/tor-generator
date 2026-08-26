from app.domain.section_text import section_plain_text


def test_section_plain_text_keeps_prose():
    assert section_plain_text("วงเงิน 100000 บาท") == "วงเงิน 100000 บาท"


def test_section_plain_text_flattens_json_fields():
    raw = '{"history":"ระบบเดิมล้าสมัย","problems":"ซ่อมบ่อย"}'
    text = section_plain_text(raw, "s1")
    assert "ระบบเดิมล้าสมัย" in text
    assert "ซ่อมบ่อย" in text
    assert "ประวัติ" in text
