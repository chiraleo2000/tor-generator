"""Analysis topics for budget, cost, personnel, and training."""

from app.domain.cost_topics import cost_analysis_topics
from app.services.tor_analysis import analyze_tor


def test_core_topics_are_always_listed():
    report = cost_analysis_topics("โครงการจัดซื้อครุภัณฑ์วงเงิน 100000 บาท")
    titles = [item["title"] for item in report["topics"]]
    assert titles[:4] == ["ประมาณงบประมาณ", "ต้นทุน", "บุคลากร", "ค่าอบรม"]
    budget = report["topics"][0]
    assert budget["status"] == "พบในข้อความ"
    assert report["topics"][2]["status"] == "ไม่พบในข้อความ"


def test_training_rate_note_uses_only_the_pdf_figure():
    text = "มีการอบรมบุคคลภายนอกและค่าอาหารพร้อมค่าเอกสาร"
    training = next(item for item in cost_analysis_topics(text)["topics"] if item["id"] == "training")
    assert "800" in training["rate_note"]
    assert "70" in training["rate_note"]
    assert "อัตราค่าจ้างที่ปรึกษา" in training["rate_note"]


def test_personnel_rate_note_names_the_matching_row():
    text = "จ้างที่ปรึกษาปริญญาโท อายุงาน 2 ปี"
    personnel = next(item for item in cost_analysis_topics(text)["topics"] if item["id"] == "personnel")
    assert "บาทต่อเดือน" in personnel["rate_note"]
    assert "ปริญญาโท" in personnel["rate_note"]


def test_related_topic_appears_only_when_mentioned():
    plain = cost_analysis_topics("วงเงินงบประมาณ 1 บาท สำหรับค่าใช้จ่ายบุคลากรและอบรม")
    assert all(item["id"] != "equipment" for item in plain["topics"])
    with_gear = cost_analysis_topics("จัดซื้ออุปกรณ์คอมพิวเตอร์วงเงิน 1 บาท")
    assert any(item["id"] == "equipment" for item in with_gear["topics"])


def test_analyze_attaches_topics_without_replacing_parts():
    result = analyze_tor({"sections": {"s1": "ขอบเขตงานจัดซื้ออุปกรณ์วงเงิน 50000 บาท"}})
    assert result.legal.key == "legal"
    assert result.lock_in.key == "lock_in"
    assert result.project.key == "project"
    titles = [item["title"] for item in result.cost_topics["topics"]]
    assert "ประมาณงบประมาณ" in titles
    assert "ค่าอบรม" in titles
