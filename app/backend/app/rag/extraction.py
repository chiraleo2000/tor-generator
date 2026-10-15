"""Document text extraction module.

Extracts text content from PDF, DOCX, and plain text files.
Provides OCR fallback for scanned PDFs using Tesseract with Thai + English support.

Requirements: 3.1, 14.1, 14.2, 14.3, 14.5
"""

from __future__ import annotations

import json
import logging
import os
import re
import struct
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal

import fitz  # PyMuPDF
from docx import Document

logger = logging.getLogger(__name__)

# Minimum character count per page to consider text extraction successful
MIN_TEXT_LENGTH = 10
# Pages with only a few junk characters should still go through OCR.
MIN_USABLE_PAGE_CHARS = 80

# Default OCR timeout in seconds (Thai scanned TOR pages are slow)
DEFAULT_OCR_TIMEOUT = 180
_OCR_LANG = "tha+eng"


def _readable_char_count(text: str) -> int:
    return sum(
        1
        for char in text
        if "\u0e00" <= char <= "\u0e7f" or "A" <= char <= "Z" or "a" <= char <= "z" or "0" <= char <= "9"
    )


def _page_text_usable(text: str) -> bool:
    stripped = (text or "").strip()
    if len(stripped) < MIN_TEXT_LENGTH:
        return False
    readable = _readable_char_count(stripped)
    if len(stripped) < MIN_USABLE_PAGE_CHARS:
        return readable >= 40
    return readable >= 20


class ExtractionMethod(str, Enum):
    """Method used for text extraction."""

    DIRECT = "direct"
    OCR = "ocr"
    MIXED = "mixed"  # Some pages direct, some OCR


@dataclass
class ExtractionResult:
    """Result of a document text extraction operation.

    Attributes:
        text: The extracted text content.
        page_count: Number of pages in the document (1 for non-paginated formats).
        method: The extraction method used (direct, ocr, or mixed).
        warnings: List of warning messages encountered during extraction.
    """

    text: str
    page_count: int
    method: Literal["direct", "ocr", "mixed"]
    warnings: list[str] = field(default_factory=list)
    # Per-page text. `text` stays the joined document used for embeddings.
    pages: list[dict[str, str | int | None]] = field(default_factory=list)


def extract_text(file_path: str, mime_type: str) -> ExtractionResult:
    """Main entry point for document text extraction.

    Routes to the appropriate extractor based on MIME type.

    Args:
        file_path: Path to the file to extract text from.
        mime_type: MIME type of the file (e.g. application/pdf, DOCX, text/plain).

    Returns:
        ExtractionResult with extracted text and metadata.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the MIME type is unsupported.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    mime_type = mime_type.lower().strip()

    if _is_kb_json(path, mime_type):
        return _extract_kb_json(file_path)

    if mime_type == "application/pdf":
        return extract_pdf(file_path)
    if mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        return extract_docx(file_path)
    if mime_type in (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-powerpoint",
    ):
        return extract_pptx(file_path)
    if mime_type.startswith("text/"):
        return extract_text_file(file_path)
    if mime_type in ("image/png", "image/jpeg", "image/gif", "image/webp"):
        warnings: list[str] = []
        try:
            text = ocr_layout(file_path)
        except FileNotFoundError:
            warnings.append("ไม่พบ Tesseract สำหรับ OCR รูปสแกน")
            text = ""
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            warnings.append(f"OCR รูปไม่สำเร็จ: {exc}")
            text = ""
        return ExtractionResult(
            text=text.strip(),
            page_count=1,
            method="ocr",
            warnings=warnings,
        )
    raise ValueError(
        f"Unsupported MIME type: {mime_type}. "
        "Supported types: application/pdf, application/json, "
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document, "
        "application/vnd.openxmlformats-officedocument.presentationml.presentation, "
        "image/png, image/jpeg, text/*"
    )


def _pdf_method(used_ocr: bool, used_direct: bool) -> Literal["direct", "ocr", "mixed"]:
    if used_ocr and used_direct:
        return "mixed"
    if used_ocr:
        return "ocr"
    return "direct"


_PLAIN_PAGE_NUMBER = re.compile(r"^(\d{1,4})$")
_DASHED_PAGE_NUMBER = re.compile(r"^-\s*(\d{1,4})\s*-$")
_PRINTED_PAGE_DISTANCE = 15


def printed_page_number(page_text: str, file_index: int) -> str | None:
    """Read a printed page number from the bottom of a page.

    Accepts a bare number such as ``16`` or a dashed footer such as ``- 16 -``
    when that number is close to the 1-based file page index. Other forms,
    including ranges like ``1-14``, stay unset.
    """
    lines = [line.strip() for line in (page_text or "").splitlines() if line.strip()]
    best: int | None = None
    best_distance = _PRINTED_PAGE_DISTANCE + 1
    for line in lines[-8:]:
        match = _PLAIN_PAGE_NUMBER.fullmatch(line) or _DASHED_PAGE_NUMBER.fullmatch(line)
        if match is None:
            continue
        number = int(match.group(1))
        if number < 1:
            continue
        distance = abs(number - file_index)
        if distance < best_distance:
            best = number
            best_distance = distance
    if best is None:
        return None
    return str(best)


def _clean_table_cell(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").replace("|", "/")
    return re.sub(r"\s+", " ", text).strip()


def _grid_markdown(data: list[list[object]] | None) -> str:
    if not data:
        return ""
    rows: list[list[str]] = []
    width = 0
    for raw in data:
        cells = [_clean_table_cell(cell) for cell in raw]
        width = max(width, len(cells))
        if any(cells):
            rows.append(cells)
    if width < 2 or len(rows) < 2:
        return ""
    padded = [row + [""] * (width - len(row)) for row in rows]
    header = padded[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in padded[1:])
    return "\n".join(lines)


def _format_table(grid: list[list[str]] | None) -> str:
    """Markdown when the grid has a header and body; otherwise keep cell text."""
    markdown = _grid_markdown(grid)
    if markdown:
        return markdown
    if not grid:
        return ""
    lines = [" | ".join(cell for cell in row if cell) for row in grid if any(row)]
    return "\n".join(lines)


def _normalize_thai_ocr(text: str) -> str:
    """Join the sara-am pair Tesseract often emits as nikhahit + sara aa."""
    return (text or "").replace("\u0e4d\u0e32", "\u0e33")


def _note_once(warnings: list[str], message: str) -> None:
    if message and message not in warnings:
        warnings.append(message)


@dataclass(frozen=True)
class OcrWord:
    """One Tesseract word box, in image pixels."""

    text: str
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True)
class _LayoutCell:
    left: int
    text: str


_RULE_MARKS = "|/\\│┃┆┇¦"


def _clean_ocr_token(text: str) -> str:
    """Drop rule fragments Tesseract reads from table borders."""
    return (text or "").strip().strip(_RULE_MARKS).strip()


def _tsv_confidence(raw: str) -> float:
    try:
        return float(raw)
    except ValueError:
        return -1.0


def _tsv_box(parts: list[str]) -> tuple[int, int, int, int] | None:
    try:
        left, top, width, height = (int(float(parts[index])) for index in (6, 7, 8, 9))
    except ValueError:
        return None
    if width <= 0 or height <= 0:
        return None
    return left, top, width, height


def _ocr_word_from_tsv(parts: list[str]) -> OcrWord | None:
    if len(parts) < 12 or parts[0] != "5":
        return None
    text = _clean_ocr_token(parts[11])
    if not text:
        return None
    if 0 <= _tsv_confidence(parts[10]) < 30:
        return None
    box = _tsv_box(parts)
    if box is None:
        return None
    left, top, width, height = box
    return OcrWord(text=text, left=left, top=top, width=width, height=height)


def parse_tesseract_tsv(raw: str) -> list[OcrWord]:
    """Read word boxes from Tesseract TSV. Low-confidence noise is dropped."""
    words: list[OcrWord] = []
    lines = (raw or "").splitlines()
    start = 1 if lines and lines[0].lower().startswith("level") else 0
    for line in lines[start:]:
        word = _ocr_word_from_tsv(line.split("\t"))
        if word is not None:
            words.append(word)
    return words


def _cluster_rows(words: list[OcrWord]) -> list[list[OcrWord]]:
    ordered = sorted(words, key=lambda word: (word.top, word.left))
    rows: list[list[OcrWord]] = []
    for word in ordered:
        if not rows:
            rows.append([word])
            continue
        row = rows[-1]
        band_top = min(item.top for item in row)
        band_bottom = max(item.top + item.height for item in row)
        word_bottom = word.top + max(word.height, 1)
        overlap = min(word_bottom, band_bottom) - max(word.top, band_top)
        if overlap >= max(word.height, 1) * 0.45:
            row.append(word)
        else:
            rows.append([word])
    for row in rows:
        row.sort(key=lambda item: item.left)
    return rows


def _column_gap(previous: OcrWord, word: OcrWord) -> bool:
    """True when the next box starts a new table column, not the next glyph."""
    step = word.left - previous.left
    if step <= 0:
        return False
    ink = previous.width
    if previous.left + previous.width > word.left + 4:
        ink = min(previous.width, step)
    ink = max(8, ink)
    return step >= max(40, int(ink * 1.9))


def _has_thai(text: str) -> bool:
    return any("\u0e00" <= char <= "\u0e7f" for char in text)


def _glue_tokens(previous: str, nxt: str, advance: int, typical: int) -> str:
    if _has_thai(previous) or _has_thai(nxt) or advance <= typical * 1.35:
        return previous + nxt
    return f"{previous} {nxt}"


def _split_row(row: list[OcrWord]) -> list[_LayoutCell]:
    if not row:
        return []
    cells = [_LayoutCell(row[0].left, row[0].text)]
    previous = row[0]
    for word in row[1:]:
        if _column_gap(previous, word):
            cells.append(_LayoutCell(word.left, word.text))
        else:
            current = cells[-1]
            cells[-1] = _LayoutCell(
                current.left,
                _glue_tokens(current.text, word.text, word.left - previous.left, 16),
            )
        previous = word
    return cells


def _markdown_from_cells(rows: list[list[_LayoutCell]]) -> str:
    edges: list[int] = []
    for row in rows:
        for cell in row:
            if not any(abs(cell.left - edge) <= 40 for edge in edges):
                edges.append(cell.left)
    edges.sort()
    grid: list[list[str]] = []
    for row in rows:
        slots = [""] * len(edges)
        for cell in row:
            index = min(
                range(len(edges)),
                key=lambda item, cell=cell: abs(edges[item] - cell.left),
            )
            slots[index] = f"{slots[index]} {cell.text}".strip() if slots[index] else cell.text
        grid.append(slots)
    return _format_table(grid)


def _table_block_end(classified: list[list[_LayoutCell]], index: int) -> int:
    end = index + 1
    while end < len(classified) and len(classified[end]) >= 2:
        end += 1
    return end


def _layout_segment(classified: list[list[_LayoutCell]], index: int) -> tuple[str, int]:
    cells = classified[index]
    if len(cells) < 2:
        if cells and cells[0].text.strip():
            return cells[0].text.strip(), index + 1
        return "", index + 1
    end = _table_block_end(classified, index)
    block = classified[index:end]
    if len(block) >= 2:
        segment = _markdown_from_cells(block)
    else:
        segment = " ".join(cell.text for cell in cells)
    return segment.strip(), end


def words_to_layout_text(words: list[OcrWord]) -> str:
    """Rebuild prose and markdown tables from OCR word boxes, top to bottom."""
    usable = [word for word in words if word.text.strip()]
    if not usable:
        return ""
    classified = [_split_row(row) for row in _cluster_rows(usable)]
    segments: list[str] = []
    index = 0
    while index < len(classified):
        segment, index = _layout_segment(classified, index)
        if segment:
            segments.append(segment)
    return _normalize_thai_ocr("\n\n".join(segments))


def _image_pixel_size(blob: bytes) -> tuple[int, int] | None:
    if blob.startswith(b"\x89PNG\r\n\x1a\n") and len(blob) >= 24:
        width, height = struct.unpack(">II", blob[16:24])
        return int(width), int(height)
    if not blob.startswith(b"\xff\xd8"):
        return None
    cursor = 2
    while cursor + 8 < len(blob):
        if blob[cursor] != 0xFF:
            break
        marker = blob[cursor + 1]
        if marker in {0xC0, 0xC1, 0xC2}:
            height, width = struct.unpack(">HH", blob[cursor + 5 : cursor + 9])
            return int(width), int(height)
        if cursor + 4 > len(blob):
            break
        segment = struct.unpack(">H", blob[cursor + 2 : cursor + 4])[0]
        cursor += 2 + segment
    return None


def _image_blob_worth_ocr(blob: bytes) -> bool:
    if len(blob) < 800:
        return False
    size = _image_pixel_size(blob)
    if size is None:
        return len(blob) >= 12_000
    width, height = size
    return width >= 80 and height >= 40


def _gray_pixmap(pix: fitz.Pixmap) -> fitz.Pixmap:
    if pix.alpha:
        pix = fitz.Pixmap(pix, 0)
    if pix.n != 1:
        pix = fitz.Pixmap(fitz.csGRAY, pix)
    return pix


def _stretch_contrast(data: bytearray) -> None:
    if len(data) < 32:
        return
    step = max(1, len(data) // 4000)
    sample = sorted(data[::step])
    low = sample[max(0, int(len(sample) * 0.02))]
    high = sample[min(len(sample) - 1, int(len(sample) * 0.98))]
    span = int(high) - int(low)
    if span < 30:
        return
    for index, value in enumerate(data):
        data[index] = _clamp_channel((int(value) - int(low)) * 255 // span)


def _clamp_channel(scaled: int) -> int:
    if scaled < 0:
        return 0
    if scaled > 255:
        return 255
    return scaled


def _pixel_offset(horizontal: bool, width: int, major: int, minor: int) -> int:
    if horizontal:
        return major * width + minor
    return minor * width + major


def _erase_run(
    data: bytearray,
    horizontal: bool,
    width: int,
    major: int,
    start: int,
    run: int,
) -> None:
    for pixel in range(start, start + run):
        data[_pixel_offset(horizontal, width, major, pixel)] = 255


def _dark_rule_pixel(
    data: bytearray,
    horizontal: bool,
    width: int,
    major: int,
    cursor: int,
    inner: int,
) -> bool:
    if cursor >= inner:
        return False
    return data[_pixel_offset(horizontal, width, major, cursor)] < 100


def _clear_rule_line(
    data: bytearray,
    horizontal: bool,
    width: int,
    major: int,
    inner: int,
    min_run: int,
) -> None:
    run = 0
    start = 0
    for cursor in range(inner + 1):
        if _dark_rule_pixel(data, horizontal, width, major, cursor, inner):
            if run == 0:
                start = cursor
            run += 1
            continue
        if run >= min_run:
            _erase_run(data, horizontal, width, major, start, run)
        run = 0


def _whiten_axis(
    data: bytearray,
    width: int,
    height: int,
    horizontal: bool,
    min_run: int,
) -> None:
    outer = height if horizontal else width
    inner = width if horizontal else height
    for major in range(outer):
        _clear_rule_line(data, horizontal, width, major, inner, min_run)


def _whiten_rules(data: bytearray, width: int, height: int) -> None:
    """Erase long horizontal and vertical rules so OCR can read text inside cells."""
    min_run = max(48, int(min(width, height) * 0.08))
    _whiten_axis(data, width, height, True, min_run)
    _whiten_axis(data, width, height, False, min_run)


def _prepare_ocr_image(src: str) -> str:
    """Upscale small scans, stretch contrast, and remove table rules."""
    pix = fitz.Pixmap(src)
    width, height = pix.width, pix.height
    if max(width, height) < 1400 and min(width, height) >= 20:
        scale = min(2.5, 1600 / max(width, height))
        if scale >= 1.15:
            doc = fitz.open()
            page = doc.new_page(width=width * scale, height=height * scale)
            page.insert_image(page.rect, filename=src)
            pix = page.get_pixmap(alpha=False)
            doc.close()
    pix = _gray_pixmap(pix)
    data = bytearray(pix.samples)
    _stretch_contrast(data)
    _whiten_rules(data, pix.width, pix.height)
    prepared = fitz.Pixmap(fitz.csGRAY, pix.width, pix.height, bytes(data), False)
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    prepared.save(path)
    return path


def _layout_from_image(path: str, *, lang: str, timeout: int) -> str:
    best = ""
    for psm in ("6", "4"):
        tsv = _run_tesseract(path, lang=lang, timeout=timeout, psm=psm, output="tsv")
        text = words_to_layout_text(parse_tesseract_tsv(tsv))
        if _readable_char_count(text) > _readable_char_count(best):
            best = text
        if _readable_char_count(best) >= 40:
            break
    return best


def ocr_layout(
    image_path: str,
    lang: str = _OCR_LANG,
    timeout: int = DEFAULT_OCR_TIMEOUT,
) -> str:
    """OCR an image and keep table rows as markdown when word boxes align."""
    prepared: str | None = None
    try:
        try:
            prepared = _prepare_ocr_image(image_path)
        except Exception as exc:
            logger.warning("OCR image prepare failed: %s", exc)
            prepared = None
        target = prepared or image_path
        text = _layout_from_image(target, lang=lang, timeout=timeout)
        if _readable_char_count(text) >= 20:
            return text
    except (FileNotFoundError, subprocess.TimeoutExpired):
        raise
    except Exception as exc:
        logger.warning("Layout OCR failed: %s", exc)
    finally:
        if prepared:
            try:
                os.unlink(prepared)
            except OSError:
                pass
    return _normalize_thai_ocr(ocr_page(image_path, lang=lang, timeout=timeout))


def _intersection_area(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> float:
    x0 = max(left[0], right[0])
    y0 = max(left[1], right[1])
    x1 = min(left[2], right[2])
    y1 = min(left[3], right[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return (x1 - x0) * (y1 - y0)


def _center_inside(
    inner: tuple[float, float, float, float],
    outer: tuple[float, float, float, float],
) -> bool:
    center_x = (inner[0] + inner[2]) / 2
    center_y = (inner[1] + inner[3]) / 2
    return outer[0] <= center_x <= outer[2] and outer[1] <= center_y <= outer[3]


def _box_tuple(value: object) -> tuple[float, float, float, float]:
    raw = tuple(value)  # type: ignore[arg-type]
    return (float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))


def _same_table(
    bbox: tuple[float, float, float, float],
    seen: list[tuple[float, float, float, float]],
) -> bool:
    if not any(_intersection_area(bbox, prev) > 0 for prev in seen):
        return False
    area = max((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]), 1)
    return any(_intersection_area(bbox, prev) / area > 0.5 for prev in seen)


def _record_table(
    table: object,
    regions: list[tuple[tuple[float, float, float, float], str]],
    seen: list[tuple[float, float, float, float]],
) -> None:
    try:
        bbox = _box_tuple(table.bbox)  # type: ignore[attr-defined]
        grid = table.extract()  # type: ignore[attr-defined]
    except Exception as exc:
        logger.warning("Table extract failed: %s", exc)
        return
    if _same_table(bbox, seen):
        return
    markdown = _grid_markdown(grid)
    if not markdown:
        return
    regions.append((bbox, markdown))
    seen.append(bbox)


def _locate_tables(page: fitz.Page, kwargs: dict[str, str]) -> tuple[object | None, bool]:
    """Return the finder and whether detection must stop."""
    try:
        return page.find_tables(**kwargs), False
    except TypeError:
        return None, not bool(kwargs)
    except Exception as exc:
        logger.warning("Table detection failed: %s", exc)
        return None, False


def _table_regions(page: fitz.Page) -> list[tuple[tuple[float, float, float, float], str]]:
    """Ruled tables first, then text-aligned tables that rules did not catch."""
    regions: list[tuple[tuple[float, float, float, float], str]] = []
    seen: list[tuple[float, float, float, float]] = []
    attempts: list[dict[str, str]] = [
        {},
        {"vertical_strategy": "text", "horizontal_strategy": "text"},
    ]
    for kwargs in attempts:
        if kwargs and regions:
            break
        found, abort = _locate_tables(page, kwargs)
        if abort:
            return regions
        if found is None:
            continue
        for table in getattr(found, "tables", None) or []:
            _record_table(table, regions, seen)
    return regions


def _dict_block_text(block: dict) -> str:
    lines: list[str] = []
    for line in block.get("lines") or []:
        parts = [str(span.get("text") or "") for span in line.get("spans") or []]
        text = "".join(parts).strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def _pdf_image_worth_ocr(
    bbox: tuple[float, float, float, float],
    page_area: float,
    text_boxes: list[tuple[float, float, float, float]],
) -> bool:
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    if width < 72 or height < 36:
        return False
    if (width * height) / page_area > 0.75:
        return False
    area = max(width * height, 1)
    for other in text_boxes:
        if _intersection_area(bbox, other) / area > 0.45:
            return False
    return True


def _ocr_pdf_clip(
    page: fitz.Page,
    bbox: tuple[float, float, float, float],
    timeout: int,
    warnings: list[str],
) -> str:
    tmp_path: str | None = None
    try:
        pix = page.get_pixmap(
            matrix=fitz.Matrix(300 / 72, 300 / 72),
            clip=fitz.Rect(*bbox),
            alpha=False,
        )
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        pix.save(tmp_path)
        return ocr_layout(tmp_path, timeout=timeout)
    except subprocess.TimeoutExpired:
        _note_once(warnings, "OCR รูปในหน้าหมดเวลา")
        return ""
    except Exception as exc:
        logger.warning("Image clip OCR failed: %s", exc)
        _note_once(warnings, f"OCR รูปในหน้าไม่สำเร็จ: {exc}")
        return ""
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _page_dict(page: fitz.Page) -> dict:
    try:
        return page.get_text("dict") or {}
    except Exception:
        return {}


def _covered_by_table(
    bbox: tuple[float, float, float, float],
    tables: list[tuple[tuple[float, float, float, float], str]],
) -> bool:
    if any(_center_inside(bbox, region) for region, _markdown in tables):
        return True
    block_area = max((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]), 1)
    return any(_intersection_area(bbox, region) / block_area > 0.4 for region, _md in tables)


def _collect_text_and_images(
    blocks: list,
    tables: list[tuple[tuple[float, float, float, float], str]],
) -> tuple[
    list[tuple[float, float, str]],
    list[tuple[float, float, float, float]],
    list[tuple[float, float, float, float]],
]:
    pieces: list[tuple[float, float, str]] = []
    text_boxes: list[tuple[float, float, float, float]] = []
    images: list[tuple[float, float, float, float]] = []
    for block in blocks:
        bbox = _box_tuple(block.get("bbox") or (0, 0, 0, 0))
        if _covered_by_table(bbox, tables):
            continue
        if block.get("type") == 0:
            text = _dict_block_text(block).strip()
            if text:
                pieces.append((bbox[1], bbox[0], text))
                text_boxes.append(bbox)
        elif block.get("type") == 1:
            images.append(bbox)
    return pieces, text_boxes, images


def _append_image_ocr(
    page: fitz.Page,
    images: list[tuple[float, float, float, float]],
    text_boxes: list[tuple[float, float, float, float]],
    page_area: float,
    ocr_timeout: int,
    warnings: list[str],
    pieces: list[tuple[float, float, str]],
) -> bool:
    image_ocr = False
    for bbox in images:
        if not _pdf_image_worth_ocr(bbox, page_area, text_boxes):
            continue
        ocr_text = _ocr_pdf_clip(page, bbox, ocr_timeout, warnings).strip()
        if not ocr_text:
            continue
        image_ocr = True
        pieces.append((bbox[1], bbox[0], ocr_text))
    return image_ocr


def compose_text_page(
    page: fitz.Page,
    ocr_timeout: int,
    warnings: list[str],
) -> tuple[str, bool]:
    """Place body text, markdown tables, and OCR'd figures in reading order."""
    tables = _table_regions(page)
    blocks = _page_dict(page).get("blocks") or []
    pieces, text_boxes, images = _collect_text_and_images(blocks, tables)
    page_area = max(float(page.rect.width * page.rect.height), 1.0)
    image_ocr = _append_image_ocr(
        page, images, text_boxes, page_area, ocr_timeout, warnings, pieces
    )
    for bbox, markdown in tables:
        pieces.append((bbox[1], bbox[0], markdown))
    pieces.sort(key=lambda item: (round(item[0], 1), item[1]))
    body = "\n\n".join(piece for _y, _x, piece in pieces if piece.strip())
    return body, image_ocr


def markdown_tables_from_page(page: fitz.Page) -> str:
    """Turn vector tables on a PDF page into markdown, header row included."""
    try:
        found = page.find_tables()
    except Exception as exc:
        logger.warning("Table detection failed: %s", exc)
        return ""
    tables = getattr(found, "tables", None) or []
    blocks: list[str] = []
    for table in tables:
        try:
            grid = table.extract()
        except Exception as exc:
            logger.warning("Table extract failed: %s", exc)
            continue
        markdown = _grid_markdown(grid)
        if markdown:
            blocks.append(markdown)
    return "\n\n".join(blocks)


def _compose_page_text(plain: str, tables_md: str) -> str:
    plain = (plain or "").strip()
    tables_md = (tables_md or "").strip()
    if tables_md and plain:
        return f"{tables_md}\n\n{plain}"
    return tables_md or plain


def _page_plain_text(
    page: fitz.Page,
    page_num: int,
    ocr_timeout: int,
    warnings: list[str],
) -> tuple[str, bool, bool]:
    """Return (plain text, used_direct, used_ocr) for one PDF page."""
    text = page.get_text().strip()
    if _page_text_usable(text):
        return text, True, False
    logger.info(
        "Page %d has insufficient text (%d chars), falling back to OCR",
        page_num + 1,
        len(text),
    )
    ocr_text = _ocr_pdf_page(page, page_num, ocr_timeout, warnings)
    if ocr_text:
        return ocr_text, False, True
    if not text:
        warnings.append(f"Page {page_num + 1}: Could not extract text (direct or OCR)")
    return text, False, False


def _pdf_page_record(
    page: fitz.Page,
    page_num: int,
    ocr_timeout: int,
    warnings: list[str],
) -> tuple[dict[str, str | int | None], bool, bool]:
    plain, used_direct, used_ocr = _page_plain_text(page, page_num, ocr_timeout, warnings)
    if used_direct:
        composed, image_ocr = compose_text_page(page, ocr_timeout, warnings)
        used_ocr = used_ocr or image_ocr
        if composed.strip():
            plain = composed
        else:
            plain = _compose_page_text(plain, markdown_tables_from_page(page))
    file_index = page_num + 1
    record = {
        "index": file_index,
        "printed": printed_page_number(plain, file_index),
        "text": plain.strip(),
    }
    return record, used_direct, used_ocr


def extract_pdf(file_path: str, ocr_timeout: int = DEFAULT_OCR_TIMEOUT) -> ExtractionResult:
    """Extract text from a PDF file using PyMuPDF.

    For each page, attempts direct text extraction first.
    If the page has too little readable text, falls back to OCR.

    Args:
        file_path: Path to the PDF file.
        ocr_timeout: Timeout in seconds for OCR per page.

    Returns:
        ExtractionResult with extracted text and metadata.
    """
    warnings: list[str] = []
    pages: list[dict[str, str | int | None]] = []
    used_ocr = False
    used_direct = False

    doc = fitz.open(file_path)
    page_count = len(doc)

    for page_num in range(page_count):
        record, direct, ocr = _pdf_page_record(
            doc[page_num], page_num, ocr_timeout, warnings
        )
        pages.append(record)
        used_direct = used_direct or direct
        used_ocr = used_ocr or ocr

    doc.close()
    return ExtractionResult(
        text="\n\n".join(str(page["text"]) for page in pages),
        page_count=page_count,
        method=_pdf_method(used_ocr, used_direct),
        warnings=warnings,
        pages=pages,
    )


def _ocr_pdf_page(
    page: fitz.Page,
    page_num: int,
    timeout: int,
    warnings: list[str],
    lang: str = _OCR_LANG,
) -> str:
    """Render a PDF page to image and OCR it.

    Args:
        page: PyMuPDF page object.
        page_num: Zero-based page index (for logging/warnings).
        timeout: OCR timeout in seconds.
        warnings: List to append warnings to.
        lang: Tesseract language string.

    Returns:
        OCR-extracted text, or empty string on failure.
    """
    tmp_path: str | None = None
    try:
        # Render page to a high-resolution PNG image
        # 300 DPI is standard for OCR (default PyMuPDF is 72 DPI, so matrix 300/72 ≈ 4.17)
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat)

        # mkstemp + close before writing: NamedTemporaryFile stays open on Windows
        # and pix.save() then fails with Permission denied.
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        pix.save(tmp_path)
        return ocr_layout(tmp_path, lang=lang, timeout=timeout)

    except subprocess.TimeoutExpired:
        warnings.append(
            f"Page {page_num + 1}: OCR timed out after {timeout}s, returning partial result"
        )
        return ""
    except Exception as e:
        logger.warning("OCR failed for page %d: %s", page_num + 1, str(e))
        warnings.append(f"Page {page_num + 1}: OCR failed ({type(e).__name__}: {e})")
        return ""
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def ocr_page(image_path: str, lang: str = _OCR_LANG, timeout: int = DEFAULT_OCR_TIMEOUT) -> str:
    """OCR a single page image using Tesseract.

    Calls Tesseract via subprocess for better timeout control.

    Args:
        image_path: Path to the image file to OCR.
        lang: Tesseract language(s) to use (default: Thai + English).
        timeout: Maximum time in seconds for OCR processing.

    Returns:
        Extracted text from the image.

    Raises:
        subprocess.TimeoutExpired: If OCR exceeds the timeout.
        FileNotFoundError: If Tesseract is not installed/found.
        RuntimeError: If Tesseract exits with a non-zero status.
    """
    text = _run_tesseract(image_path, lang=lang, timeout=timeout, psm="1")
    if _readable_char_count(text) >= 40:
        return text
    try:
        alt = _run_tesseract(image_path, lang=lang, timeout=timeout, psm="6")
    except (RuntimeError, subprocess.TimeoutExpired):
        return text
    if _readable_char_count(alt) > _readable_char_count(text):
        return alt
    return text


def _tesseract_executable() -> str:
    """Resolve the Tesseract binary (env override, PATH, or Windows default)."""
    override = (os.environ.get("TESSERACT_CMD") or "").strip()
    if override:
        return override
    from shutil import which

    found = which("tesseract")
    if found:
        return found
    windows_default = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if windows_default.is_file():
        return str(windows_default)
    return "tesseract"


def _run_tesseract(
    image_path: str,
    *,
    lang: str,
    timeout: int,
    psm: str,
    output: str = "txt",
) -> str:
    exe = _tesseract_executable()
    cmd = [
        exe,
        image_path,
        "stdout",
        "-l",
        lang,
        "--psm",
        psm,
    ]
    if output == "tsv":
        cmd.append("tsv")
    env = os.environ.copy()
    # Windows Tesseract expects TESSDATA_PREFIX to be the tessdata/ folder itself.
    tessdata_dir = Path(exe).resolve().parent / "tessdata"
    if tessdata_dir.is_dir():
        env["TESSDATA_PREFIX"] = str(tessdata_dir)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            env=env,
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            "Tesseract OCR is not installed or not found in PATH. "
            "Set TESSERACT_CMD or install under "
            r"C:\Program Files\Tesseract-OCR "
            "(Linux: apt-get install tesseract-ocr tesseract-ocr-tha)"
        ) from None
    if result.returncode != 0:
        stderr_msg = result.stderr.strip() if result.stderr else "Unknown error"
        raise RuntimeError(
            f"Tesseract OCR failed (exit code {result.returncode}): {stderr_msg}"
        )
    return result.stdout.strip()


def _heading_prefix(style_name: str) -> str | None:
    if not style_name.startswith("Heading"):
        return None
    try:
        level = int(style_name.split()[-1])
    except (ValueError, IndexError):
        level = 1
    return "#" * level


def _docx_paragraph_line(paragraph: object) -> str | None:
    text = paragraph.text.strip()
    if not text:
        return None
    style = paragraph.style
    style_name = style.name if style else ""
    prefix = _heading_prefix(style_name)
    if prefix is None:
        return text
    return f"{prefix} {text}"


def _tc_grid_span(cell: object) -> int:
    tc_pr = cell._tc.tcPr
    if tc_pr is None or tc_pr.gridSpan is None:
        return 1
    try:
        return max(1, int(tc_pr.gridSpan.val))
    except (TypeError, ValueError):
        return 1


def _tc_vmerge_continue(cell: object) -> bool:
    tc_pr = cell._tc.tcPr
    if tc_pr is None or tc_pr.vMerge is None:
        return False
    value = tc_pr.vMerge.val
    return value in (None, "continue")


def _embed_id(blip: object) -> str:
    for key, value in blip.attrib.items():  # type: ignore[attr-defined]
        if key == "embed" or str(key).endswith("}embed"):
            return str(value)
    return ""


def _blip_text(blip: object, related: dict, warnings: list[str]) -> str:
    rid = _embed_id(blip)
    part = related.get(rid) if rid else None
    blob = getattr(part, "blob", None) if part is not None else None
    if not blob:
        return ""
    text, warning = _ocr_image_bytes(blob)
    if warning:
        _note_once(warnings, warning)
    return text.strip()


def _paragraph_image_texts(paragraph: object, doc: object, warnings: list[str]) -> list[str]:
    try:
        blips = paragraph._p.xpath(".//*[local-name()='blip']")  # type: ignore[attr-defined]
    except Exception:
        return []
    related = getattr(getattr(doc, "part", None), "related_parts", {}) or {}
    texts: list[str] = []
    for blip in blips:
        text = _blip_text(blip, related, warnings)
        if text:
            texts.append(text)
    return texts


def _ocr_image_bytes(blob: bytes) -> tuple[str, str | None]:
    if not _image_blob_worth_ocr(blob):
        return "", None
    if blob.startswith(b"\x89PNG"):
        suffix = ".png"
    elif blob.startswith(b"\xff\xd8"):
        suffix = ".jpg"
    else:
        suffix = ".img"
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        Path(path).write_bytes(blob)
        return ocr_layout(path).strip(), None
    except FileNotFoundError:
        return "", "ไม่พบ Tesseract สำหรับ OCR รูปในเอกสาร"
    except subprocess.TimeoutExpired:
        return "", "OCR รูปในเอกสารหมดเวลา"
    except Exception as exc:
        return "", f"OCR รูปในเอกสารไม่สำเร็จ: {exc}"
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _cell_display_text(cell: object, doc: object, warnings: list[str]) -> str:
    base = "" if _tc_vmerge_continue(cell) else _clean_table_cell(cell.text)
    extras: list[str] = []
    for paragraph in cell.paragraphs:
        extras.extend(_paragraph_image_texts(paragraph, doc, warnings))
    extra = " ".join(item for item in extras if item).strip()
    if base and extra:
        return f"{base} {extra}"
    return base or extra


def _docx_row_cells(row: object, doc: object, warnings: list[str]) -> list[str]:
    cells: list[str] = []
    seen: set[int] = set()
    for cell in row.cells:
        marker = id(cell._tc)
        if marker in seen:
            continue
        seen.add(marker)
        text = _cell_display_text(cell, doc, warnings)
        cells.append(text)
        cells.extend([""] * (_tc_grid_span(cell) - 1))
    return cells


def _docx_table_lines(table: object, doc: object, warnings: list[str]) -> list[str]:
    grid: list[list[str]] = []
    for row in table.rows:
        values = _docx_row_cells(row, doc, warnings)
        if any(values):
            grid.append(values)
    formatted = _format_table(grid)
    return [formatted] if formatted else []


def _estimate_text_pages(full_text: str) -> int:
    length = len(full_text)
    return max(1, length // 3000 + (1 if length % 3000 else 0))


def _append_paragraph_block(
    sections: list[str],
    paragraph: object,
    doc: object,
    warnings: list[str],
) -> None:
    line = _docx_paragraph_line(paragraph)
    if line is not None:
        sections.append(line)
    sections.extend(_paragraph_image_texts(paragraph, doc, warnings))


def _docx_body_sections(doc: object, warnings: list[str]) -> list[str]:
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    sections: list[str] = []
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            _append_paragraph_block(sections, Paragraph(child, doc), doc, warnings)
            continue
        if child.tag != qn("w:tbl"):
            continue
        sections.extend(_docx_table_lines(Table(child, doc), doc, warnings))
    return sections


def _docx_fallback_sections(doc: object, warnings: list[str]) -> list[str]:
    from docx.document import Document as DocxDocument

    if not isinstance(doc, DocxDocument):
        return []
    sections: list[str] = []
    for paragraph in doc.paragraphs:
        _append_paragraph_block(sections, paragraph, doc, warnings)
    for table in doc.tables:
        sections.extend(_docx_table_lines(table, doc, warnings))
    return sections


def extract_docx(file_path: str) -> ExtractionResult:
    """Extract text from a DOCX file preserving document structure.

    Walks the document body in order so tables stay next to surrounding
    paragraphs (critical for Thai budget / TOR proposal forms).

    Args:
        file_path: Path to the DOCX file.

    Returns:
        ExtractionResult with structured text content.
    """
    try:
        doc = Document(file_path)
    except Exception as e:
        raise ValueError(f"Failed to open DOCX file: {e}") from e

    warnings: list[str] = []
    sections = _docx_body_sections(doc, warnings) or _docx_fallback_sections(doc, warnings)
    full_text = "\n".join(sections)
    return ExtractionResult(
        text=full_text,
        page_count=_estimate_text_pages(full_text),
        method="direct",
        warnings=warnings,
    )


def _deduplicate_adjacent(items: list[str]) -> list[str]:
    """Remove adjacent duplicate items (common in merged DOCX table cells).

    Args:
        items: List of cell text strings.

    Returns:
        List with adjacent duplicates removed.
    """
    if not items:
        return []

    result = [items[0]]
    for item in items[1:]:
        if item != result[-1]:
            result.append(item)
    return result


def _pptx_table_lines(shape: object) -> list[str]:
    grid = [
        [_clean_table_cell(cell.text) for cell in row.cells]
        for row in shape.table.rows
    ]
    formatted = _format_table(grid)
    return [formatted] if formatted else []


def _pptx_picture_text(shape: object) -> str:
    image = getattr(shape, "image", None)
    blob = getattr(image, "blob", None) if image is not None else None
    if not blob:
        return ""
    text, _warning = _ocr_image_bytes(blob)
    return text.strip()


def _pptx_shape_lines(shape: object) -> list[str]:
    if getattr(shape, "has_table", False):
        return _pptx_table_lines(shape)
    picture = _pptx_picture_text(shape)
    if picture:
        return [picture]
    text = getattr(shape, "text", "") or ""
    stripped = text.strip()
    return [stripped] if stripped else []


def _pptx_slide_section(index: int, slide: object) -> str | None:
    slide_parts: list[str] = [f"## Slide {index}"]
    for shape in slide.shapes:
        slide_parts.extend(_pptx_shape_lines(shape))
    if len(slide_parts) <= 1:
        return None
    return "\n".join(slide_parts)


def extract_pptx(file_path: str) -> ExtractionResult:
    """Extract headings, lists, and tables from a PowerPoint file."""
    warnings: list[str] = []
    try:
        from pptx import Presentation
    except ImportError:
        warnings.append("python-pptx is not installed")
        return ExtractionResult(text="", page_count=0, method="direct", warnings=warnings)

    presentation = Presentation(file_path)
    sections: list[str] = []
    for index, slide in enumerate(presentation.slides, start=1):
        section = _pptx_slide_section(index, slide)
        if section is not None:
            sections.append(section)
    return ExtractionResult(
        text="\n\n".join(sections),
        page_count=len(list(presentation.slides)),
        method="direct",
        warnings=warnings,
    )


def extract_text_file(file_path: str, encoding: str = "utf-8") -> ExtractionResult:
    """Extract text from a plain text file.

    Args:
        file_path: Path to the text file.
        encoding: File encoding (default UTF-8).

    Returns:
        ExtractionResult with file text content.

    Raises:
        UnicodeDecodeError: If the file cannot be decoded with the given encoding.
    """
    warnings: list[str] = []

    try:
        text = Path(file_path).read_text(encoding=encoding)
    except UnicodeDecodeError:
        # Try Thai encoding fallback (TIS-620 / Windows-874)
        try:
            text = Path(file_path).read_text(encoding="cp874")
            warnings.append(
                "File was not UTF-8 encoded; decoded using Windows-874 (Thai) encoding"
            )
        except UnicodeDecodeError as e:
            raise UnicodeDecodeError(
                e.encoding,
                e.object,
                e.start,
                e.end,
                f"Could not decode file with UTF-8 or Windows-874: {e.reason}",
            )

    return ExtractionResult(
        text=text.strip(),
        page_count=1,
        method="direct",
        warnings=warnings,
    )


def _is_kb_json(path: Path, mime_type: str) -> bool:
    """True when the file should go through a knowledge-base JSON extractor."""
    name = path.name
    if name.endswith(("_tor_extract.json", "_combined.json")):
        return True
    if path.suffix.lower() == ".json" and "04-decision-rules" in path.parts:
        return True
    return mime_type in ("application/json", "text/json")


def _extract_kb_json(file_path: str) -> ExtractionResult:
    """Route combined packs, decision-rules, and TOR extracts."""
    path = Path(file_path)
    name = path.name
    if name.endswith("_combined.json"):
        return extract_combined_kb_json(file_path)
    if "04-decision-rules" in path.parts:
        return flatten_decision_rules_json(file_path)
    return extract_tor_extract_json(file_path)


def _is_raw_json_token(text: str) -> bool:
    """True for identifier-like strings (keys, codes) that should not be embedded."""
    if not text:
        return True
    allowed = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-"
    )
    return all(char in allowed for char in text)


def _remember_prose(text: str, parts: list[str]) -> None:
    cleaned = text.strip()
    if cleaned and not _is_raw_json_token(cleaned):
        parts.append(cleaned)


def _append_dict_prose(value: dict, parts: list[str]) -> None:
    for key, item in value.items():
        if isinstance(key, str):
            _remember_prose(key, parts)
        _append_thai_text(item, parts)


def _append_thai_text(value: object, parts: list[str]) -> None:
    """Collect Thai (and other prose) strings from nested JSON, skipping raw keys."""
    if isinstance(value, str):
        _remember_prose(value, parts)
        return
    if isinstance(value, list):
        for item in value:
            _append_thai_text(item, parts)
        return
    if isinstance(value, dict):
        _append_dict_prose(value, parts)


def _combined_section_contents(payload: object) -> list[str]:
    contents: list[str] = []
    if not isinstance(payload, dict):
        return contents
    name = payload.get("name")
    if isinstance(name, str) and name.strip():
        contents.append(name.strip())
    sections = payload.get("sections")
    if not isinstance(sections, list):
        return contents
    for section in sections:
        if not isinstance(section, dict):
            continue
        content = str(section.get("content") or "").strip()
        if content:
            contents.append(content)
    return contents


def extract_combined_kb_json(file_path: str) -> ExtractionResult:
    """Extract RAG text from a knowledge-base `*_combined.json` file.

    These files store Thai excerpts under `sections[].content`.
    Empty packs return empty text so ingestion can fail.
    """
    payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
    contents = _combined_section_contents(payload)
    text = "\n\n".join(contents).strip()
    return ExtractionResult(
        text=text,
        page_count=1,
        method="direct",
        warnings=[] if text else ["JSON extract has no sections content"],
    )


def flatten_decision_rules_json(file_path: str) -> ExtractionResult:
    """Flatten nested decision-rules JSON into Thai prose for RAG.

    Nested `rules` objects keep condition/result/legal_basis text and drop
    raw English keys such as `step_1_primary_method` or `R1`.
    Empty payloads return empty text so ingestion can fail.
    """
    payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
    parts: list[str] = []
    _append_thai_text(payload, parts)
    text = "\n\n".join(parts).strip()
    return ExtractionResult(
        text=text,
        page_count=1,
        method="direct",
        warnings=[] if text else ["JSON extract has no rule content"],
    )


def _tor_focus_contents(payload: object) -> list[str]:
    contents: list[str] = []
    if not isinstance(payload, dict):
        return contents
    focus = payload.get("focus_areas")
    if not isinstance(focus, dict):
        return contents
    for sections in focus.values():
        if not isinstance(sections, list):
            continue
        for section in sections:
            if not isinstance(section, dict):
                continue
            content = str(section.get("content") or "").strip()
            if content:
                contents.append(content)
    return contents


def extract_tor_extract_json(file_path: str) -> ExtractionResult:
    """Extract RAG text from a knowledge-base `*_tor_extract.json` file.

    These files store Thai legal excerpts under `focus_areas.*.content`.
    Empty extracts (no focus-area content) return empty text so ingestion
    can fail instead of embedding raw JSON keys.
    """
    payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
    contents = _tor_focus_contents(payload)
    source = payload.get("source_file") if isinstance(payload, dict) else None
    parts = [str(source), *contents] if source and contents else contents
    text = "\n\n".join(parts).strip()
    return ExtractionResult(
        text=text,
        page_count=1,
        method="direct",
        warnings=[] if text else ["JSON extract has no focus_areas content"],
    )
