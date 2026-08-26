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


def split_text_blocks(text: str) -> list[tuple[str, list[str]]]:
    """Split text into ('para'|'table', lines) blocks."""
    lines = (text or "").split("\n")
    blocks: list[tuple[str, list[str]]] = []
    buffer: list[str] = []

    def flush_paras() -> None:
        nonlocal buffer
        if buffer:
            blocks.append(("para", buffer))
            buffer = []

    index = 0
    while index < len(lines):
        line = lines[index]
        # Look ahead for a table starting here
        window: list[str] = []
        cursor = index
        while cursor < len(lines) and (
            "|" in lines[cursor] or (window and not lines[cursor].strip())
        ):
            if not lines[cursor].strip() and window:
                break
            window.append(lines[cursor])
            cursor += 1
            if len(window) >= 2 and parse_markdown_table_rows(window):
                # extend while next lines look like table rows
                while cursor < len(lines) and "|" in lines[cursor]:
                    window.append(lines[cursor])
                    cursor += 1
                break
        table = parse_markdown_table_rows(window) if len(window) >= 2 else None
        if table:
            flush_paras()
            blocks.append(("table", window))
            index = cursor
            continue
        buffer.append(line)
        index += 1
    flush_paras()
    return blocks


def split_scope_subsection_draft(text: str) -> dict[str, str]:
    """Split an s4 draft that uses ### s4.N headings into subsection map."""
    matches = list(_SCOPE_HEADING.finditer(text or ""))
    if not matches:
        return {}
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        raw_key = match.group(2).lower()
        key = raw_key if raw_key.startswith("s") else f"s{raw_key}"
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = (text[start:end] or "").strip()
        title_rest = (match.group(3) or "").strip()
        if title_rest and not body.startswith(title_rest):
            body = f"{title_rest}\n{body}".strip() if body else title_rest
        if body:
            result[key] = body
    return result
