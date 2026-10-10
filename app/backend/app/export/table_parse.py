"""Parse markdown pipe tables for TOR export/UI."""

from __future__ import annotations

import re

_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
# Keep [0-9] (not \\d): Python \\d matches Thai digits.
_SCOPE_HEADING = re.compile(
    r"(?m)^(#{1,3}\s+)?(s?4\.[0-9]{1,2})\s*[:：\-]?\s*(.*)$"  # NOSONAR python:S6353
)


def is_table_separator(line: str) -> bool:
    """True if line is a markdown table alignment row (| --- | :---: |)."""
    stripped = line.strip()
    if "|" not in stripped:
        return False
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    if len(cells) < 2:
        return False
    for cell in cells:
        if not cell:
            return False
        core = cell.strip(":")
        if len(core) < 3 or any(ch != "-" for ch in core):
            return False
    return True


def parse_markdown_table_rows(lines: list[str]) -> list[list[str]] | None:
    """Return table cells if `lines` is a markdown pipe table, else None."""
    if len(lines) < 2:
        return None
    rows: list[list[str]] = []
    for index, raw in enumerate(lines):
        line = raw.strip()
        if index == 1 and is_table_separator(line):
            continue
        match = _ROW.match(line)
        if not match:
            if "|" in line and not line.startswith("|"):
                cells = [cell.strip() for cell in line.split("|")]
                rows.append([cell for cell in cells if cell != "" or len(cells) > 1])
                continue
            return None
        cells = [cell.strip() for cell in match.group(1).split("|")]
        rows.append(cells)
    if len(rows) < 2:
        return None
    width = max(len(row) for row in rows)
    return [row + [""] * (width - len(row)) for row in rows]


def _line_in_table_window(lines: list[str], window: list[str], cursor: int) -> bool:
    if "|" in lines[cursor]:
        return True
    return bool(window) and not lines[cursor].strip()


def _extend_parsed_table(lines: list[str], window: list[str], cursor: int) -> int:
    while cursor < len(lines) and "|" in lines[cursor]:
        window.append(lines[cursor])
        cursor += 1
    return cursor


def _table_window(lines: list[str], index: int) -> tuple[list[str], int]:
    window: list[str] = []
    cursor = index
    while cursor < len(lines) and _line_in_table_window(lines, window, cursor):
        if not lines[cursor].strip() and window:
            break
        window.append(lines[cursor])
        cursor += 1
        if len(window) >= 2 and parse_markdown_table_rows(window):
            return window, _extend_parsed_table(lines, window, cursor)
    return window, cursor


def split_text_blocks(text: str) -> list[tuple[str, list[str]]]:
    """Split text into ('para'|'table', lines) blocks."""
    lines = (text or "").split("\n")
    blocks: list[tuple[str, list[str]]] = []
    buffer: list[str] = []
    index = 0
    while index < len(lines):
        window, cursor = _table_window(lines, index)
        table = parse_markdown_table_rows(window) if len(window) >= 2 else None
        if table:
            if buffer:
                blocks.append(("para", buffer))
                buffer = []
            blocks.append(("table", window))
            index = cursor
            continue
        buffer.append(lines[index])
        index += 1
    if buffer:
        blocks.append(("para", buffer))
    return blocks


def split_scope_subsection_draft(text: str) -> dict[str, str]:
    """Split an s4 draft that uses ### s4.N headings into subsection map."""
    matches = list(_SCOPE_HEADING.finditer(text or ""))
    if not matches:
        return {}
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        body = _scope_subsection_body(text or "", matches, index, match)
        if body:
            raw_key = match.group(2).lower()
            key = raw_key if raw_key.startswith("s") else f"s{raw_key}"
            result[key] = body
    return result


def _scope_subsection_body(text: str, matches: list, index: int, match: re.Match[str]) -> str:
    start = match.end()
    end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
    body = (text[start:end] or "").strip()
    title_rest = (match.group(3) or "").strip()
    if title_rest and not body.startswith(title_rest):
        return f"{title_rest}\n{body}".strip() if body else title_rest
    return body
