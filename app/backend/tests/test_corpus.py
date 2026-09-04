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
    monkeypatch.delenv("KB_SOURCES_ROOT", raising=False)
    handbook = tmp_path / HANDBOOK_FILENAME
    handbook.write_bytes(b"%PDF-1.4 handbook")
    raw = tmp_path.joinpath("การจัดซื้อจัดจ้าง", "ข้อมูลดิบ")
    raw.mkdir(parents=True)
    (raw / "พรบ.pdf").write_bytes(b"%PDF-1.4 law")
    nested = raw / "ย่อย"
    nested.mkdir()
    (nested / "หนังสือเวียน.pdf").write_bytes(b"%PDF-1.4 nested")
    (raw / "ระเบียบ.pdf").write_bytes(b"%PDF-1.4 rule")
    (raw / "notes.txt").write_text("skip me", encoding="utf-8")
    extra = tmp_path.joinpath("การจัดจ้างทำของ")
    extra.mkdir()
    (extra / "แบบแปลน.pdf").write_bytes(b"%PDF-1.4 extra")
    samples = tmp_path.joinpath("ตัวอย่าง")
    samples.mkdir()
    (samples / "TOR-ตัวอย่าง.pdf").write_bytes(b"%PDF-1.4 sample")

    files = list_mandatory_sources(tmp_path)
    counts = group_counts(files)
    assert counts[GROUP_MANDATORY_HANDBOOK] == 1
    assert counts[GROUP_MANDATORY_RAW] == 5
    names = {item.path.name for item in files}
    assert HANDBOOK_FILENAME in names
    assert "หนังสือเวียน.pdf" in names
    assert "แบบแปลน.pdf" in names
    assert "TOR-ตัวอย่าง.pdf" in names
    assert "notes.txt" not in names


def test_kb_sources_root_env_overrides_repo_walk(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("RAW_DOCS_DIR", raising=False)
    handbook = tmp_path / HANDBOOK_FILENAME
    handbook.write_bytes(b"%PDF-1.4 handbook")
    raw = tmp_path.joinpath("การจัดซื้อจัดจ้าง", "ข้อมูลดิบ")
    raw.mkdir(parents=True)
    (raw / "พรบ.pdf").write_bytes(b"%PDF-1.4 law")
    monkeypatch.setenv("KB_SOURCES_ROOT", str(tmp_path))
    files = list_mandatory_sources()
    names = {item.path.name for item in files}
    assert HANDBOOK_FILENAME in names
    assert "พรบ.pdf" in names


def test_raw_docs_dir_adds_extra_pdf(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("RAW_DOCS_DIR", raising=False)
    monkeypatch.delenv("KB_SOURCES_ROOT", raising=False)
    extra = tmp_path / "extra"
    extra.mkdir()
    (extra / "more.pdf").write_bytes(b"%PDF-1.4 extra")
    monkeypatch.setenv("RAW_DOCS_DIR", str(extra))
    empty_root = tmp_path / "empty-sources"
    empty_root.mkdir()
    files = list_mandatory_sources(empty_root)
    assert any(item.path.name == "more.pdf" for item in files)
    assert all(item.group == GROUP_MANDATORY_RAW for item in files)


def test_live_mandatory_folders_when_present(monkeypatch):
    monkeypatch.delenv("KB_SOURCES_ROOT", raising=False)
    monkeypatch.delenv("RAW_DOCS_DIR", raising=False)
    files = list_mandatory_sources()
    if not files:
        pytest.skip("mandatory PDFs are not available on this machine")
    groups = {item.group for item in files}
    if GROUP_MANDATORY_RAW not in groups:
        pytest.skip("raw corpus is not mounted in this environment")
    handbook = [item for item in files if item.group == GROUP_MANDATORY_HANDBOOK]
    if handbook:
        assert handbook[0].path.suffix.lower() == ".pdf"


def test_raw_docs_dir_single_pdf_file(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("KB_SOURCES_ROOT", raising=False)
    pdf = tmp_path / "alone.pdf"
    pdf.write_bytes(b"%PDF-1.4 alone")
    monkeypatch.setenv("RAW_DOCS_DIR", str(pdf))
    empty_root = tmp_path / "empty-sources"
    empty_root.mkdir()
    files = list_mandatory_sources(empty_root)
    assert any(item.path.name == "alone.pdf" for item in files)


def test_group_counts_includes_unknown_group():
    from app.domain.corpus import CorpusFile

    files = [CorpusFile(path=Path("x.pdf"), group="other")]
    counts = group_counts(files)
    assert counts["other"] == 1

