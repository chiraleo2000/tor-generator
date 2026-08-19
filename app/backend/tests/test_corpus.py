"""Mandatory RAG corpus grouping from ข้อมูลดิบ + handbook PDF."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.corpus import (
    GROUP_MANDATORY_HANDBOOK,
    GROUP_MANDATORY_RAW,
    GROUP_USER,
    HANDBOOK_FILENAME,
    group_counts,
    group_for_filename,
    list_mandatory_sources,
)


def test_group_for_filename_tags_handbook_and_user():
    assert group_for_filename(HANDBOOK_FILENAME) == GROUP_MANDATORY_HANDBOOK
    assert group_for_filename("พรบ. การจัดซื้อจัดจ้าง.pdf") == GROUP_MANDATORY_RAW
    assert group_for_filename("anything.pdf", owner_id="user-1") == GROUP_USER


def test_list_mandatory_sources_groups_tmp_tree(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("RAW_DOCS_DIR", raising=False)
    handbook = tmp_path / HANDBOOK_FILENAME
    handbook.write_bytes(b"%PDF-1.4 handbook")
    raw = tmp_path.joinpath("การจัดซื้อจัดจ้าง", "ข้อมูลดิบ")
    raw.mkdir(parents=True)
    (raw / "พรบ.pdf").write_bytes(b"%PDF-1.4 law")
    (raw / "ระเบียบ.pdf").write_bytes(b"%PDF-1.4 rule")
    (raw / "notes.txt").write_text("skip me", encoding="utf-8")

    files = list_mandatory_sources(tmp_path)
    counts = group_counts(files)
    assert counts[GROUP_MANDATORY_HANDBOOK] == 1
    assert counts[GROUP_MANDATORY_RAW] == 2
    names = {item.path.name for item in files}
    assert HANDBOOK_FILENAME in names
    assert "notes.txt" not in names


def test_raw_docs_dir_adds_extra_pdf(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("RAW_DOCS_DIR", raising=False)
    extra = tmp_path / "extra"
    extra.mkdir()
    (extra / "more.pdf").write_bytes(b"%PDF-1.4 extra")
    monkeypatch.setenv("RAW_DOCS_DIR", str(extra))
    empty_root = tmp_path / "empty-sources"
    empty_root.mkdir()
    files = list_mandatory_sources(empty_root)
    assert any(item.path.name == "more.pdf" for item in files)
    assert all(item.group == GROUP_MANDATORY_RAW for item in files)


def test_live_mandatory_folders_when_present():
    files = list_mandatory_sources()
    if not files:
        pytest.skip("mandatory PDFs are not available on this machine")
    groups = {item.group for item in files}
    assert GROUP_MANDATORY_RAW in groups
    handbook = [item for item in files if item.group == GROUP_MANDATORY_HANDBOOK]
    if handbook:
        assert handbook[0].path.suffix.lower() == ".pdf"
