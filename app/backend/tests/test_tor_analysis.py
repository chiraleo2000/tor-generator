"""Three-part TOR analyzer: legal, lock-in, and project scores."""

from __future__ import annotations

from app.services.tor_analysis import (
    PART_LOCK_IN,
    PART_WEIGHTS,
    analyze_tor,
    analysis_as_dict,
)


def _base_sections(**overrides: str) -> dict:
    sections = {
        "s1": (
            "ความเป็นมา ตามพระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ "
            "พ.ศ. 2560 และระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้าง"
            "และการบริหารพัสดุภาครัฐ พ.ศ. 2560"
        ),
        "s2": "วัตถุประสงค์เพื่อพัฒนาระบบบริหารสัญญาของหน่วยงาน",
        "s3": "คุณสมบัติผู้เสนอราคา ต้องมีทุนจดทะเบียนไม่น้อยกว่า 1,250,000 บาท",
        "s4": (
            "ขอบเขตของงาน วิเคราะห์ความต้องการ พัฒนาระบบ ทดสอบ และส่งมอบ "
            "ผลงานส่งมอบได้แก่ รายงานวิเคราะห์ ระบบที่ใช้งานได้ และคู่มือ"
        ),
        "s5": "ระยะเวลาดำเนินการ 180 วัน นับจากวันลงนามในสัญญา",
        "s6": (
            "วงเงินงบประมาณ 5,000,000 บาท ราคากลาง 4,800,000 บาท "
            "จัดซื้อด้วยวิธีประกาศเชิญชวนทั่วไป (e-bidding)"
        ),
        "s7": "หลักเกณฑ์พิจารณาคุณภาพและ price-performance",
        "s8": "งวดที่ 1 ร้อยละ 40 เมื่อส่งมอบรายงาน งวดที่ 2 ร้อยละ 60 เมื่อส่งมอบระบบ",
        "s9": "การรับประกัน 1 ปี ระดับบริการ SLA เวลาซ่อมไม่เกิน 24 ชั่วโมง",
        "s10": "ค่าปรับอัตราร้อยละ 0.10 ต่อวัน ขั้นต่ำ 100 บาทต่อวัน",
        "s11": "เงื่อนไขทั่วไป ผู้ว่าจ้างต้องจัดให้ข้อมูลเดิมและบัญชีเข้าถึงระบบ",
        "s12": "เอกสารประกอบ",
        "s13": "ภาคผนวก",
    }
    sections.update(overrides)
    return sections


def test_analyze_tor_public_signature_and_weights():
    result = analyze_tor(
        {
            **_base_sections(),
            "budget": 5_000_000,
            "vendor_capital": 1_250_000,
            "penalty_rate_percent": 0.10,
            "project_type": "buy_goods",
            "timeline_days": 180,
        }
    )
    payload = analysis_as_dict(result)
    assert set(PART_WEIGHTS) == {"legal", "lock_in", "project"}
    assert abs(sum(PART_WEIGHTS.values()) - 1.0) < 1e-9
    assert result.legal.score >= 90
    assert result.lock_in.score >= 90
    assert result.project.score >= 90
    assert "ไม่พบประเด็นในด้านกฎหมาย" in result.legal.explanation
    assert result.total == round(
        result.legal.score * 0.40
        + result.lock_in.score * 0.30
        + result.project.score * 0.30
    )
    assert payload["legal"]["score"] == result.legal.score
    assert "ดึงคะแนน" in result.summary or "ใกล้เคียงกัน" in result.summary


def test_oracle_spec_without_equivalent_lowers_lock_in():
    result = analyze_tor(
        {
            **_base_sections(
                s4=(
                    "ต้องใช้ฐานข้อมูล Oracle Processor license บนเครื่อง Exadata "
                    "และบังคับ hard partitioning ผ่าน Integrated Virtualization Manager "
                    "โดยไม่มีข้อความหรือเทียบเท่า พร้อมส่งมอบผลงานส่งมอบรายงานและระบบ"
                )
            ),
            "budget": 5_000_000,
            "vendor_capital": 1_250_000,
            "penalty_rate_percent": 0.10,
            "project_type": "buy_goods",
            "timeline_days": 180,
        }
    )
    assert result.lock_in.score < result.legal.score or result.lock_in.score < 90
    assert result.lock_in.findings
    quotes = " ".join(item.source_quote for item in result.lock_in.findings)
    reasons = " ".join(item.reason for item in result.lock_in.findings)
    assert "Oracle" in quotes or "Oracle" in reasons
    assert any("หรือเทียบเท่า" in item.suggested_text for item in result.lock_in.findings)
    assert result.lock_in.explanation
    assert "lock" in result.summary.lower() or "lock specs" in result.summary


def test_impossible_timeline_lowers_project():
    result = analyze_tor(
        {
            **_base_sections(
                s4=(
                    "พัฒนาระบบสารสนเทศครบวงจร วิเคราะห์ความต้องการ พัฒนาโมดูล "
                    "ทดสอบความมั่นคง อบรมผู้ใช้ และส่งมอบระบบพร้อมคู่มือ"
                ),
                s5="ผู้รับจ้างต้องส่งมอบงานทั้งหมดภายใน 7 วันนับจากวันลงนาม",
            ),
            "budget": 5_000_000,
            "vendor_capital": 1_250_000,
            "penalty_rate_percent": 0.10,
            "timeline_days": 7,
            "project_type": "buy_goods",
        }
    )
    assert result.project.score < 90
    assert any("7 วัน" in item.reason or "คับแคบ" in item.reason for item in result.project.findings)
    assert result.project.explanation
    assert "บริหารโครงการ" in result.summary


def test_penalty_issues_lower_legal_and_cite_regulation():
    result = analyze_tor(
        {
            "s1": "ความเป็นมาโครงการจัดซื้อจัดจ้างภาครัฐ",
            "s10": "คิดค่าปรับร้อยละ 1 ต่อวัน ของวงเงินตามสัญญา",
            "penalty_rate_percent": 1.0,
            "project_type": "buy_goods",
        }
    )
    assert result.legal.score < 90
    assert result.legal.findings
    assert any(
        "ค่าปรับ" in item.reason and ("0.20" in item.reason or "ระเบียบ" in item.reason)
        for item in result.legal.findings
    )
    assert any(
        item.legal_basis and ("2560" in item.legal_basis or "ระเบียบ" in item.legal_basis)
        for item in result.legal.findings
    )


def test_missing_sections_keep_partial_nonzero_scores():
    result = analyze_tor(
        {
            "s1": (
                "ความเป็นมา ตามพระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ "
                "พ.ศ. 2560 และระเบียบกระทรวงการคลัง พ.ศ. 2560"
            ),
            "s4": "ขอบเขตงานพัฒนาระบบและส่งมอบรายงานความคืบหน้า",
            "project_type": "buy_goods",
        }
    )
    assert result.halted is True
    assert result.missing_sections
    assert "s3" in result.missing_sections
    scores = (result.legal.score, result.lock_in.score, result.project.score)
    assert not all(score == 0 for score in scores)
    assert any(part.explanation for part in (result.legal, result.lock_in, result.project))
    assert "ขาดหมวด" in result.summary or "ยังขาด" in result.legal.explanation
    assert 0 <= result.total <= 100


def test_content_never_returns_three_unexplained_zeros():
    result = analyze_tor({"s4": "จัดซื้อครุภัณฑ์คอมพิวเตอร์สำหรับหน่วยงาน"})
    scores = (result.legal.score, result.lock_in.score, result.project.score)
    if all(score == 0 for score in scores):
        assert result.legal.explanation
        assert result.lock_in.explanation
        assert result.project.explanation
    else:
        assert any(score > 0 for score in scores)


def test_lock_in_part_key_constant():
    assert PART_LOCK_IN == "lock_in"
