"""Tests for Section_Profile (7 procurement categories)."""

from app.domain.section_profile import (
    CATEGORIES_WITHOUT_CURRENT_SYSTEM,
    PROCUREMENT_CATEGORY_ORDER,
    ProfileStatus,
    classify_category,
    extra_legacy_scope_items,
    map_legacy_type,
    profile_export,
    profile_for_project,
    require_profile,
    resolve_profile,
    scope_storage_key,
    subsection_title,
)


def test_seven_categories_in_requirement_order():
    assert PROCUREMENT_CATEGORY_ORDER == [
        "hire_develop",
        "hire_maintain",
        "lease_service",
        "buy_goods",
        "construction",
        "hire_consult",
        "hire_service",
    ]


def test_legacy_map():
    assert map_legacy_type("it") == "hire_develop"
    assert map_legacy_type("general") == "buy_goods"
    assert map_legacy_type("consulting") == "hire_consult"
    assert map_legacy_type("") == "buy_goods"
    assert map_legacy_type("hire_maintain") == "hire_maintain"


def test_empty_category_is_none_until_normalized():
    status, mapped = classify_category("")
    assert status is ProfileStatus.NONE
    assert mapped == ""
    missing = resolve_profile("not_a_type")
    assert missing is ProfileStatus.MISSING


def test_goods_construction_service_omit_current_system():
    for category in CATEGORIES_WITHOUT_CURRENT_SYSTEM:
        titles = [item.title for item in profile_for_project(category).scope_subsections]
        assert "ระบบงานปัจจุบัน" not in titles


def test_legal_required_present_in_every_profile():
    needed = {
        "s1",
        "s2",
        "s3",
        "s4",
        "s5",
        "s6",
        "s7",
        "s8",
        "s11",
        "s13",
    }
    for category in PROCUREMENT_CATEGORY_ORDER:
        keys = {item.storage_key for item in profile_for_project(category).main_sections if item.required}
        assert needed <= keys, category


def test_scope_storage_keys_fit_db():
    for category in PROCUREMENT_CATEGORY_ORDER:
        for item in profile_for_project(category).scope_subsections:
            assert len(item.storage_key) <= 20
            assert len(scope_storage_key(item.semantic_key)) <= 20


def test_display_numbers_are_contiguous():
    profile = profile_for_project("hire_develop")
    for index, _item in enumerate(profile.scope_subsections, start=1):
        assert index == index


def test_legacy_extras_kept():
    extras = extra_legacy_scope_items(
        {"s4.2": "ระบบเดิมของหน่วยงาน", "items": "โต๊ะ 10 ตัว"},
        "buy_goods",
    )
    keys = {item["key"] for item in extras}
    assert "s4.2" in keys
    assert "items" not in keys


def test_require_profile_ok():
    profile = require_profile("it")
    assert profile.category == "hire_develop"
    assert subsection_title("functional", "hire_develop")


def test_profile_export_has_all_categories():
    payload = profile_export()
    assert set(payload["profiles"]) == set(PROCUREMENT_CATEGORY_ORDER)
    goods = payload["profiles"]["buy_goods"]["scope_subsections"]
    titles = [item["title"] for item in goods]
    assert "ระบบงานปัจจุบัน" not in titles
