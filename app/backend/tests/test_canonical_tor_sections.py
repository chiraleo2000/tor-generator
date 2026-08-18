"""Canonical TOR section model tests."""

from app.domain.tor_sections import (
    STEP_SECTION_MAP,
    TOR_SECTION_LABELS,
    TOR_SECTION_ORDER,
    sample_complete_sections,
)
from app.orchestrator.agents.registry import AGENT_REGISTRY
from app.rule_engine.rules.completeness import TOR_REQUIRED_SECTIONS


def test_canonical_keys_are_s1_to_s13():
    assert TOR_SECTION_ORDER == [f"s{i}" for i in range(1, 14)]
    assert set(TOR_SECTION_LABELS) == set(TOR_SECTION_ORDER)


def test_wizard_map_covers_all_legal_sections():
    covered = {key for keys in STEP_SECTION_MAP.values() for key in keys}
    assert set(TOR_SECTION_ORDER) <= covered
    assert STEP_SECTION_MAP[8] == []
    assert STEP_SECTION_MAP[2] == ["s1"]
    assert STEP_SECTION_MAP[5] == ["s3"]


def test_agents_registered_for_all_sections():
    assert set(AGENT_REGISTRY) == set(TOR_SECTION_ORDER)
    assert AGENT_REGISTRY["s6"].section_name_en == "Budget"
    assert AGENT_REGISTRY["s11"].section_name_en == "Evaluation"
    assert AGENT_REGISTRY["s7"].section_key == "s7"


def test_completeness_labels_match_canonical():
    assert TOR_REQUIRED_SECTIONS["s6"].startswith("วงเงินงบประมาณ")
    assert TOR_REQUIRED_SECTIONS["s7"].startswith("สถานที่ดำเนินการ")
    assert TOR_REQUIRED_SECTIONS["s10"].startswith("อัตราค่าปรับ")


def test_sample_complete_sections_has_thirteen_keys():
    sample = sample_complete_sections()
    assert set(sample) == set(TOR_SECTION_ORDER)
