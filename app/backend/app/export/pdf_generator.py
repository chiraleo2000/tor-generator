"""PDF document generator for TOR export.

Generates PDF documents with Thai government formatting using WeasyPrint.
The PDF output has identical textual content to the DOCX generator:
same sections, same order, same formatting (TH Sarabun New, 14pt body, 16pt headings,
2.5cm margins).

Requirements: 8.2, 8.5
"""

import io
from typing import Optional

from app.export.docx_generator import (
    TOR_SECTION_LABELS,
    TOR_SECTION_ORDER,
    TORContent,
)
from app.export.thai_formatting import format_section_number, format_thai_date

# CSS for Thai government formatting matching DOCX output
_DOCUMENT_CSS = """\
@page {
    size: A4;
    margin: 2.5cm;
    @top-center {
        content: element(header);
    }
    @bottom-center {
        content: counter(page);
        font-family: "TH Sarabun New", "TH SarabunPSK", sans-serif;
        font-size: 12pt;
    }
}

body {
    font-family: "TH Sarabun New", "TH SarabunPSK", sans-serif;
    font-size: 14pt;
    line-height: 1.5;
    color: #000000;
}

.header {
    position: running(header);
    text-align: center;
    font-size: 12pt;
    font-family: "TH Sarabun New", "TH SarabunPSK", sans-serif;
}

.title {
    text-align: center;
    font-size: 16pt;
    font-weight: bold;
    margin-top: 0;
    margin-bottom: 12pt;
}

.subtitle {
    text-align: center;
    font-size: 16pt;
    font-weight: bold;
    margin-bottom: 6pt;
}

.date-info {
    text-align: right;
    margin-bottom: 12pt;
}

.separator {
    text-align: left;
    margin-bottom: 12pt;
    color: #000000;
}

.section-heading {
    font-size: 16pt;
    font-weight: bold;
    margin-top: 12pt;
    margin-bottom: 6pt;
}

.section-body p {
    text-indent: 1.25cm;
    margin: 0 0 3pt 0;
}

.section-placeholder {
    font-style: italic;
    color: #808080;
}

.sub-section-heading {
    font-size: 14pt;
    font-weight: bold;
    margin-top: 6pt;
    margin-bottom: 3pt;
    margin-left: 1.0cm;
}

.sub-section-body p {
    margin: 0 0 3pt 0;
    margin-left: 1.5cm;
}
"""


def _escape_html(text: str) -> str:
    """Escape HTML special characters in text."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


class PDFGenerator:
    """Generates PDF documents with Thai government formatting using WeasyPrint.

    The generated PDF has identical textual content and structure to the DOCX
    output — same sections, same order, same Thai formatting conventions.

    Usage:
        generator = PDFGenerator()
        content = TORContent(
            project_name="ระบบ ICT",
            ministry="กระทรวงดิจิทัลฯ",
            budget=5_000_000,
            sections={"s1": "ความเป็นมาของโครงการ..."},
        )
        pdf_bytes = generator.generate(content)
    """

    def __init__(self) -> None:
        """Initialize the PDF generator."""
        pass

    def generate(self, content: TORContent) -> bytes:
        """Generate a PDF file from TOR content.

        Args:
            content: Structured TOR content to render.

        Returns:
            Bytes representing the generated PDF file.
        """
        html_content = self._build_html(content)
        pdf_bytes = self._render_pdf(html_content)
        return pdf_bytes

    def _build_html(self, content: TORContent) -> str:
        """Build the full HTML document from TOR content.

        Mirrors the exact same structure and content as the DOCX generator.

        Args:
            content: TOR content dataclass.

        Returns:
            Complete HTML document string.
        """
        parts: list[str] = []

        # HTML document start
        parts.append("<!DOCTYPE html>")
        parts.append('<html lang="th">')
        parts.append("<head>")
        parts.append('<meta charset="UTF-8">')
        parts.append("<title>ร่างขอบเขตของงาน (TOR)</title>")
        parts.append("</head>")
        parts.append("<body>")

        # Running header (ministry name)
        parts.append(f'<div class="header">{_escape_html(content.ministry or "")}</div>')

        # Title
        parts.append('<div class="title">ร่างขอบเขตของงาน (Terms of Reference: TOR)</div>')

        # Project name subtitle
        if content.project_name:
            parts.append(
                f'<div class="subtitle">{_escape_html(content.project_name)}</div>'
            )

        # Document info: date
        from datetime import date as date_type

        export_date = content.export_date or date_type.today()
        date_str = format_thai_date(export_date, use_thai_numerals=content.use_thai_numerals)
        parts.append(f'<div class="date-info">{_escape_html(date_str)}</div>')

        # Separator line
        parts.append(f'<div class="separator">{"─" * 60}</div>')

        # TOR sections
        parts.append(self._build_sections_html(content))

        # HTML document end
        parts.append("</body>")
        parts.append("</html>")

        return "\n".join(parts)

    def _build_sections_html(self, content: TORContent) -> str:
        """Build HTML for all TOR sections in order.

        Args:
            content: TOR content dataclass.

        Returns:
            HTML string for all sections.
        """
        parts: list[str] = []
        section_num = 1

        for section_key in TOR_SECTION_ORDER:
            section_content = content.sections.get(section_key, "")
            section_label = TOR_SECTION_LABELS.get(section_key, f"ส่วนที่ {section_key}")

            # Section heading
            num_str = format_section_number(section_num, content.use_thai_numerals)
            heading_text = f"{num_str}. {section_label}"
            parts.append(
                f'<div class="section-heading">{_escape_html(heading_text)}</div>'
            )

            # Section body
            if section_content:
                parts.append(self._format_body_html(section_content, "section-body"))
            else:
                parts.append(
                    '<div class="section-placeholder">(ยังไม่ได้กรอกข้อมูล)</div>'
                )

            # Sub-sections
            sub_sections = content.sub_sections.get(section_key, {})
            if sub_sections:
                parts.append(
                    self._build_sub_sections_html(
                        section_num, sub_sections, content.use_thai_numerals
                    )
                )

            section_num += 1

        return "\n".join(parts)

    def _build_sub_sections_html(
        self,
        parent_num: int,
        sub_sections: dict[str, str],
        use_thai_numerals: bool,
    ) -> str:
        """Build HTML for sub-sections.

        Args:
            parent_num: Parent section number (unused here, kept for consistency).
            sub_sections: Dict of sub-section key → content.
            use_thai_numerals: Whether to use Thai numerals.

        Returns:
            HTML string for the sub-sections.
        """
        parts: list[str] = []

        # Sort sub-sections by numeric key
        sorted_keys = sorted(
            sub_sections.keys(),
            key=lambda k: self._parse_sub_key(k),
        )

        for sub_key in sorted_keys:
            sub_content = sub_sections[sub_key]
            sub_num_str = format_section_number(sub_key, use_thai_numerals)

            parts.append(
                f'<div class="sub-section-heading">{_escape_html(sub_num_str)}</div>'
            )

            if sub_content:
                parts.append(self._format_body_html(sub_content, "sub-section-body"))

        return "\n".join(parts)

    def _format_body_html(self, text: str, css_class: str) -> str:
        """Format body text as HTML paragraphs.

        Args:
            text: Raw text content (paragraphs separated by newlines).
            css_class: CSS class for the wrapper div.

        Returns:
            HTML div with paragraph elements.
        """
        paragraphs = text.strip().split("\n")
        para_html = []
        for para_text in paragraphs:
            para_text = para_text.strip()
            if not para_text:
                continue
            para_html.append(f"<p>{_escape_html(para_text)}</p>")

        if not para_html:
            return ""

        return f'<div class="{css_class}">{"".join(para_html)}</div>'

    def _parse_sub_key(self, key: str) -> tuple[int, ...]:
        """Parse a sub-section key like '4.1' into a sortable tuple (4, 1)."""
        parts = key.replace(".", " ").split()
        result = []
        for part in parts:
            try:
                result.append(int(part))
            except ValueError:
                result.append(0)
        return tuple(result)

    def _render_pdf(self, html_content: str) -> bytes:
        """Render HTML to PDF using WeasyPrint.

        WeasyPrint is imported lazily to avoid import errors on systems
        without the required native libraries (GTK/Pango/GLib) installed.

        Args:
            html_content: Full HTML document string.

        Returns:
            PDF file bytes.
        """
        from weasyprint import CSS, HTML

        html_doc = HTML(string=html_content)
        css = CSS(string=_DOCUMENT_CSS)

        buffer = io.BytesIO()
        html_doc.write_pdf(buffer, stylesheets=[css])
        buffer.seek(0)
        return buffer.getvalue()
