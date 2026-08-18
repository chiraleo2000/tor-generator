"""Tests for Phase 0 heading → canonical section mapping."""

from app.domain.extraction_map import infer_wizard_fields, map_extracted_text
from app.domain.tor_sections import TOR_SECTION_LABELS


def test_maps_thai_headings_to_canonical_keys():
    text = """
1. ความเป็นมา
หน่วยงานต้องการพัฒนาระบบสารสนเทศ
2. วัตถุประสงค์
เพื่อเพิ่มประสิทธิภาพการจัดซื้อจัดจ้าง
5. ระยะเวลาดำเนินการ
ระยะเวลาดำเนินการ 180 วัน นับจากวันลงนามในสัญญา
7. สถานที่ดำเนินการ
กรุงเทพมหานคร
"""
    mapped = map_extracted_text(text)
    assert "หน่วยงานต้องการพัฒนาระบบ" in mapped["s1"]
    assert "เพิ่มประสิทธิภาพ" in mapped["s2"]
    assert "180" in mapped["s5"]
    fields = infer_wizard_fields(mapped)
    assert fields["duration_days"] == 180
    assert "กรุงเทพ" in str(fields["location"])


def test_plain_text_stays_in_s1():
    mapped = map_extracted_text("ข้อความไม่มีหัวข้อใด ๆ เลยทั้งสิ้น")
    assert list(mapped.keys()) == ["s1"]


def test_labels_cover_thirteen_sections():
    assert len(TOR_SECTION_LABELS) == 13
