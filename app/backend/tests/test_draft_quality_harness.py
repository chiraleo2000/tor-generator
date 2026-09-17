"""Tests for TOR draft quality harness (baseline SKK reports)."""

from __future__ import annotations

import json
from pathlib import Path

from app.export.draft_quality import score_draft_text, score_fixture_report


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "Discussions" / "test-evidence").is_dir():
            return parent
        if (parent / "docker-compose.yml").is_file() and (parent / "Discussions").is_dir():
            return parent
    return here.parents[min(3, len(here.parents) - 1)]


EVIDENCE = _repo_root() / "Discussions" / "test-evidence"
SEP9 = EVIDENCE / "_round-2026-09-09-skk-quality.json"
SEP10 = EVIDENCE / "_round-2026-09-10-skk-quality-thinking.json"


def test_baseline_sep9_export_still_has_english_and_is_shorter_than_old_tor():
    report = json.loads(SEP9.read_text(encoding="utf-8"))
    metrics = score_fixture_report(report)
    assert metrics["export_english"], "baseline still leaked Cyber Attack"
    assert "Cyber Attack" in metrics["export_english"]
    assert int(metrics["export_chars"] or 0) < int(metrics["old_chars"] or 0)
    assert "งวดงานและการจ่ายเงิน**" in str(report.get("s8_sample") or "")
    leaks = score_draft_text(str(report.get("s8_sample") or "")).get("markdown_leak")
    assert leaks


def test_thinking_round_had_empty_payment_and_evaluation():
    report = json.loads(SEP10.read_text(encoding="utf-8"))
    metrics = score_fixture_report(report)
    assert "s8" in metrics["section_empty"]
    assert "s11" in metrics["section_empty"]
    assert (report.get("new_export") or {}).get("error") == "no docx"


def test_clean_thai_draft_scores_empty_leaks():
    text = (
        "สำนักงานเศรษฐกิจการเกษตรมีภารกิจหลักในการศึกษาและวิเคราะห์ข้อมูล "
        "จึงมีความจำเป็นต้องพัฒนาระบบประมวลผลภาวะเศรษฐกิจสังคมครัวเรือน\n"
        "งวดที่ ๑ ร้อยละ ๒๐"
    )
    metrics = score_draft_text(text, draft_chars={"s1": 80, "s8": 40})
    assert metrics["unauthorized_english_count"] == 0
    assert metrics["scaffold"] == []
    assert metrics["section_empty"] == []
    assert metrics["has_payment_table"]


def test_gold_pack_fixture_is_hire_develop_tone():
    pack = Path(__file__).resolve().parent / "fixtures" / "hire_develop_gold_pack.txt"
    text = pack.read_text(encoding="utf-8")
    assert "ผู้รับจ้าง" in text
    assert "functional" in text
    assert "testing" in text
    assert "hire_develop" in text
    maintain = Path(__file__).resolve().parent / "fixtures" / "hire_maintain_smoke_pack.txt"
    assert "asset_list" in maintain.read_text(encoding="utf-8")


def test_score_draft_text_flags_filename_type_and_orphan_separator():
    leaked = (
        "[ข้อความผู้ใช้.txt]\n"
        "ผู้ขายส่งมอบครุภัณฑ์\n"
        "| --- |\n"
        "งานจัดซื้อครุภัณฑ์"
    )
    metrics = score_draft_text(leaked, category="hire_develop")
    assert metrics["filename_leak"]
    assert metrics["markdown_separator"]
    assert "ผู้ขาย" in metrics["type_forbidden"]
    table = "| งวดที่ | ร้อยละ |\n| --- | --- |\n| ๑ | ๒๐ |"
    clean = score_draft_text(table, category="hire_develop")
    assert clean["markdown_separator"] == []
    assert clean["filename_leak"] == []


def test_reject_intake_echo_and_strip_wrappers():
    from app.services.thai_draft import reject_intake_echo, strip_intake_wrappers

    pack = "กรมบัญชีกลางจ้างพัฒนาระบบสารสนเทศบริหารสัญญาจัดซื้อจัดจ้างภาครัฐ " * 8
    assert strip_intake_wrappers("[ข้อความผู้ใช้.txt]\nเนื้อหา") == "เนื้อหา"
    assert reject_intake_echo(pack, pack) == ""
    assert "ผู้รับจ้างพัฒนาโมดูลทะเบียนสัญญา" in reject_intake_echo(
        "ผู้รับจ้างพัฒนาโมดูลทะเบียนสัญญาและทดสอบระบบตามเกณฑ์ที่ยอมรับ",
        pack,
    )
