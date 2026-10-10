"""Sonar reads Cobertura paths from the repository root."""

from pathlib import Path

from tests.conftest import align_coverage_xml_for_sonar


def test_align_coverage_xml_source_for_repo_root_scan(tmp_path: Path):
    report = tmp_path / "coverage.xml"
    report.write_text(
        '<?xml version="1.0" ?>\n<coverage><sources><source>app</source></sources></coverage>\n',
        encoding="utf-8",
    )
    align_coverage_xml_for_sonar(report)
    text = report.read_text(encoding="utf-8")
    assert "<source>app/backend/app</source>" in text
    align_coverage_xml_for_sonar(report)
    assert text == report.read_text(encoding="utf-8")
    align_coverage_xml_for_sonar(tmp_path / "missing.xml")
