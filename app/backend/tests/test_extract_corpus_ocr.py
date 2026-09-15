"""OCR fallback for scanned sample TORs (corpus/few-shot only)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND = Path(__file__).resolve().parents[1]
MODULE_PATH = BACKEND / "scripts" / "extract_corpus_standard.py"


def _load():
    spec = importlib.util.spec_from_file_location("extract_corpus_standard", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ocr_pdf_skips_cleanly_when_tesseract_missing():
    mod = _load()
    with patch.object(mod, "ocr_available", return_value=(False, "Tesseract not available")):
        text, reason = mod.ocr_pdf_pages(Path("missing.pdf"))
    assert text == ""
    assert reason


def test_ocr_pdf_returns_text_when_engine_ready(tmp_path):
    mod = _load()
    page = MagicMock()
    pix = MagicMock()
    pix.tobytes.return_value = b"png-bytes"
    page.get_pixmap.return_value = pix
    doc = MagicMock()
    doc.__iter__.return_value = iter([page])

    with (
        patch.object(mod, "ocr_available", return_value=(True, "")),
        patch.object(mod, "_try_open_pdf", return_value=doc),
        patch.object(mod, "OCR_DIR", tmp_path),
        patch("PIL.Image.open", return_value=MagicMock()),
        patch("pytesseract.image_to_string", return_value="ความเป็นมาของโครงการ " * 20),
    ):
        text, reason = mod.ocr_pdf_pages(tmp_path / "scan.pdf")
        sidecar = mod.write_ocr_sidecar(tmp_path / "scan.pdf", text)
    assert reason == ""
    assert len(text) >= mod.MIN_TEXT_CHARS
    assert sidecar.is_file()
    assert "ความเป็นมา" in sidecar.read_text(encoding="utf-8")
