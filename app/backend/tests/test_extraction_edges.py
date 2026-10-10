"""Pure extraction helpers and OCR failure paths, without a live Tesseract run."""

import subprocess
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.rag.extraction import (
    _clean_table_cell,
    _deduplicate_adjacent,
    _grid_markdown,
    _ocr_pdf_page,
    _pptx_shape_lines,
    _pptx_slide_section,
    _tesseract_executable,
    extract_pptx,
    markdown_tables_from_page,
    ocr_page,
    printed_page_number,
)


def test_table_markdown_and_printed_page_edges():
    assert _clean_table_cell(None) == ""
    assert "/" in _clean_table_cell("ก\n|ข")
    assert _grid_markdown(None) == ""
    assert _grid_markdown([["อย่างเดียว"]]) == ""
    table = _grid_markdown([["หัว", "คอลัมน์"], ["ก", "ข"]])
    assert table.startswith("| หัว |")
    assert printed_page_number("ไม่มีเลข", 1) is None
    assert printed_page_number("0\n- 4 -", 3) == "4"
    assert _deduplicate_adjacent([]) == []
    assert _deduplicate_adjacent(["ก", "ก", "ข"]) == ["ก", "ข"]


def test_pptx_shapes_and_missing_package(monkeypatch):
    table_shape = SimpleNamespace(
        has_table=True,
        table=SimpleNamespace(
            rows=[
                SimpleNamespace(cells=[SimpleNamespace(text="หัว"), SimpleNamespace(text="ค่า")]),
            ]
        ),
    )
    blank = SimpleNamespace(has_table=False, text="  ")
    titled = SimpleNamespace(has_table=False, text="สารบัญ")
    assert _pptx_shape_lines(table_shape)[0].startswith("หัว")
    assert _pptx_shape_lines(blank) == []
    slide = SimpleNamespace(shapes=[titled, table_shape])
    section = _pptx_slide_section(1, slide)
    assert section is not None
    assert "Slide 1" in section
    assert _pptx_slide_section(2, SimpleNamespace(shapes=[])) is None

    import builtins

    real_import = builtins.__import__

    def _block_pptx(name, *args, **kwargs):
        if name == "pptx":
            raise ImportError("pptx missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block_pptx)
    missing = extract_pptx("unused.pptx")
    assert missing.page_count == 0
    assert any("python-pptx" in warning for warning in missing.warnings)


def test_ocr_page_falls_back_and_pdf_ocr_errors(monkeypatch, tmp_path):
    calls = {"n": 0}

    def _fake_tesseract(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return "สั้น"
        if calls["n"] == 2:
            raise RuntimeError("psm")
        return "ก" * 50

    monkeypatch.setattr("app.rag.extraction._run_tesseract", _fake_tesseract)
    assert ocr_page("page.png") == "สั้น"
    long_text = ocr_page("page.png")
    assert len(long_text) >= 40

    page = MagicMock()
    page.get_pixmap.side_effect = RuntimeError("render")
    warnings: list[str] = []
    assert _ocr_pdf_page(page, 0, 5, warnings) == ""
    assert warnings
    assert "OCR failed" in warnings[0]

    page.get_pixmap.side_effect = None
    pix = MagicMock()

    def _save(path):
        raise subprocess.TimeoutExpired(cmd="tesseract", timeout=5)

    pix.save.side_effect = _save
    page.get_pixmap.return_value = pix
    warnings.clear()
    assert _ocr_pdf_page(page, 1, 3, warnings) == ""
    assert any("timed out" in item for item in warnings)

    page = MagicMock()
    page.find_tables.side_effect = RuntimeError("no tables")
    assert markdown_tables_from_page(page) == ""
    found = SimpleNamespace(
        tables=[SimpleNamespace(extract=MagicMock(side_effect=RuntimeError("extract")))]
    )
    page.find_tables.side_effect = None
    page.find_tables.return_value = found
    assert markdown_tables_from_page(page) == ""

    monkeypatch.setenv("TESSERACT_CMD", str(tmp_path / "tesseract"))
    assert _tesseract_executable().endswith("tesseract")


def test_tesseract_which_and_windows_default(monkeypatch):
    monkeypatch.delenv("TESSERACT_CMD", raising=False)
    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr("app.rag.extraction.Path.is_file", lambda self: False)
    assert _tesseract_executable() == "tesseract"
