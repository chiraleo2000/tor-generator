"""Unit tests for knowledge-base seed helpers."""

from __future__ import annotations

from pathlib import Path

from app.seed_kb import (
    _is_listable_dir,
    _mime_for,
    _resolve_ingest_path,
    _should_seed,
    list_seed_files,
)


def test_list_seed_files_skips_internal_notes(tmp_path: Path):
    (tmp_path / "_coverage_matrix.txt").write_text("internal", encoding="utf-8")
    (tmp_path / "readme.md").write_text("# kb", encoding="utf-8")
    json_path = tmp_path / "พรบ_tor_extract.json"
    json_path.write_text("{}", encoding="utf-8")
    names = {path.name for path in list_seed_files(tmp_path, limit=80)}
    assert "readme.md" in names
    assert "พรบ_tor_extract.json" in names
    assert "_coverage_matrix.txt" not in names


def test_list_seed_files_includes_combined_and_decision_rules(tmp_path: Path):
    (tmp_path / "_coverage_matrix.json").write_text("{}", encoding="utf-8")
    (tmp_path / "_coverage_matrix.txt").write_text("internal", encoding="utf-8")
    (tmp_path / "_external_sources_note.md").write_text("note", encoding="utf-8")
    (tmp_path / "readme.md").write_text("# kb", encoding="utf-8")
    combined_dir = tmp_path / "definitions"
    combined_dir.mkdir()
    (combined_dir / "_definitions_combined.json").write_text("{}", encoding="utf-8")
    rules_dir = tmp_path / "04-decision-rules"
    rules_dir.mkdir()
    (rules_dir / "method_selection.json").write_text("{}", encoding="utf-8")
    names = {path.name for path in list_seed_files(tmp_path, limit=80)}
    assert "readme.md" in names
    assert "_definitions_combined.json" in names
    assert "method_selection.json" in names
    assert "_coverage_matrix.json" not in names
    assert "_coverage_matrix.txt" not in names
    assert "_external_sources_note.md" not in names


def test_should_seed_combined_and_skips_coverage(tmp_path: Path):
    combined = tmp_path / "_guarantee_combined.json"
    combined.write_text("{}", encoding="utf-8")
    coverage = tmp_path / "_coverage_matrix.json"
    coverage.write_text("{}", encoding="utf-8")
    note = tmp_path / "_external_sources_note.md"
    note.write_text("note", encoding="utf-8")
    assert _should_seed(combined) is True
    assert _should_seed(coverage) is False
    assert _should_seed(note) is False


def test_is_listable_dir(tmp_path: Path):
    assert _is_listable_dir(tmp_path) is True
    assert _is_listable_dir(tmp_path / "missing") is False


def test_mime_for_json_extract():
    path = Path("กฎกระทรวง_tor_extract.json")
    assert _mime_for(path, "txt") == "application/json"
    assert _mime_for(Path("note.md"), "txt") == "text/plain"


def test_document_name_uses_sidecar(tmp_path: Path):
    from app.seed_kb import _document_name

    json_path = tmp_path / "007.json"
    json_path.write_text("{}", encoding="utf-8")
    (tmp_path / "007.kbname").write_text("กฎกระทรวงกำหนดวงเงิน_tor_extract", encoding="utf-8")
    assert _document_name(json_path) == "กฎกระทรวงกำหนดวงเงิน_tor_extract"


def test_resolve_ingest_path_matches_filename(tmp_path: Path):
    target = tmp_path / "unique-e2e-ingest-name_tor_extract.json"
    target.write_text("{}", encoding="utf-8")
    resolved = _resolve_ingest_path(
        "/knowledge-base/unique-e2e-ingest-name_tor_extract.json", tmp_path
    )
    assert resolved == target


def test_safe_print_does_not_raise(capsys):
    from app.seed_kb import _safe_print

    _safe_print("seed_kb complete")
    assert "seed_kb complete" in capsys.readouterr().out
