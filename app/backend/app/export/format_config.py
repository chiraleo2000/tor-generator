"""Shared TOR export format constants (Req 2).

DOCX and PDF generators must read page, font, and spacing values from here.
apply_format() sets fields best-effort and never aborts the export.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

logger = logging.getLogger("tor_app.format_config")

FONT_NAME = "TH Sarabun New"
FONT_NAME_FALLBACK = "TH SarabunPSK"
BODY_FONT_SIZE_PT = 16
HEADING_FONT_SIZE_PT = 18
SUBHEADING_FONT_SIZE_PT = 16
HEADER_FONT_SIZE_PT = 12
LINE_SPACING = 1.0
PAGE_WIDTH_CM = 21.0
PAGE_HEIGHT_CM = 29.7
PAGE_MARGIN_TOP_BOTTOM_CM = 2.54
PAGE_MARGIN_LEFT_RIGHT_CM = 1.91
TITLE_BLOCK_NAME = "ร่างขอบเขตของงาน"


def apply_format(setters: dict[str, Callable[[], None]]) -> None:
    """Apply each format setter independently (Req 2.9)."""
    for name, setter in setters.items():
        try:
            setter()
        except Exception:
            logger.warning("format field %s could not be applied; continuing export", name)


def document_css() -> str:
    """WeasyPrint CSS aligned with DOCX FormatConfig values."""
    top = PAGE_MARGIN_TOP_BOTTOM_CM
    side = PAGE_MARGIN_LEFT_RIGHT_CM
    fonts = f'"{FONT_NAME}", "{FONT_NAME_FALLBACK}", sans-serif'
    return f"""\
@page {{
    size: A4;
    margin: {top}cm {side}cm {top}cm {side}cm;
    @top-center {{
        content: element(header);
    }}
    @bottom-center {{
        content: counter(page);
        font-family: {fonts};
        font-size: {HEADER_FONT_SIZE_PT}pt;
    }}
}}

body {{
    font-family: {fonts};
    font-size: {BODY_FONT_SIZE_PT}pt;
    line-height: {LINE_SPACING};
    color: #000000;
}}

.header {{
    position: running(header);
    text-align: center;
    font-size: {HEADER_FONT_SIZE_PT}pt;
    font-family: {fonts};
}}

.title {{
    text-align: center;
    font-size: {HEADING_FONT_SIZE_PT}pt;
    font-weight: bold;
    margin-top: 0;
    margin-bottom: 12pt;
}}

.subtitle {{
    text-align: center;
    font-size: {HEADING_FONT_SIZE_PT}pt;
    font-weight: bold;
    margin-bottom: 6pt;
}}

.date-info {{
    text-align: right;
    margin-bottom: 12pt;
}}

.separator {{
    text-align: left;
    margin-bottom: 12pt;
    color: #000000;
}}

.section-heading {{
    font-size: {HEADING_FONT_SIZE_PT}pt;
    font-weight: bold;
    margin-top: 8pt;
    margin-bottom: 4pt;
}}

.section-body p {{
    text-indent: 1.25cm;
    margin: 0 0 3pt 0;
}}

.appendix-divider {{
    font-size: {HEADING_FONT_SIZE_PT}pt;
    font-weight: bold;
    margin-top: 16pt;
    margin-bottom: 8pt;
}}

.sub-section-heading {{
    font-size: {SUBHEADING_FONT_SIZE_PT}pt;
    font-weight: bold;
    margin-top: 4pt;
    margin-bottom: 2pt;
    margin-left: 1.0cm;
}}

.sub-section-body p {{
    margin: 0 0 3pt 0;
    margin-left: 1.5cm;
}}
"""
