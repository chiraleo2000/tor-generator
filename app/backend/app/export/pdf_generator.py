"""PDF document generator for TOR export.

Generates PDF documents with Thai government formatting using WeasyPrint.
The PDF output has identical textual content to the DOCX generator:
same sections, same order, same formatting (TH Sarabun New, 16pt body, 18pt headings,
1.0 line spacing, 2.54cm top/bottom / 1.91cm left/right margins).

Requirements: 8.2, 8.5
"""

import io
from typing import Optional

from app.export.docx_generator import TORContent
from app.export.format_config import TITLE_BLOCK_NAME, document_css
from app.export.thai_formatting import format_thai_date

_DOCUMENT_CSS = document_css()


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
        parts.append(f"<title>{TITLE_BLOCK_NAME}</title>")
        parts.append("</head>")
        parts.append("<body>")

        # Running header (ministry name)
        parts.append(f'<div class="header">{_escape_html(content.ministry or "")}</div>')

        # Title
        parts.append(f'<div class="title">{TITLE_BLOCK_NAME}</div>')

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
        from app.export.export_plan import build_render_plan

        plan = build_render_plan(content)
        parts.append(self._build_sections_html(plan))
        parts.append(self._build_appendices_html(plan))

        # HTML document end
        parts.append("</body>")
        parts.append("</html>")

        return "\n".join(parts)

    def _build_sections_html(self, plan) -> str:
        """Build HTML for displayed TOR sections from the shared RenderPlan."""
        parts: list[str] = []
        for section in plan.body:
            heading_text = (
                f"{section.number}. {section.label}" if section.number else section.label
            )
            parts.append(
                f'<div class="section-heading">{_escape_html(heading_text)}</div>'
            )
            if section.content:
                parts.append(self._format_body_html(section.content, "section-body"))
            for sub in section.subsections:
                heading = f"{sub.number} {sub.label}".strip()
                parts.append(
                    f'<div class="sub-section-heading">{_escape_html(heading)}</div>'
                )
                if sub.content:
                    parts.append(self._format_body_html(sub.content, "sub-section-body"))
        return "\n".join(parts)

    def _build_appendices_html(self, plan) -> str:
        parts = ['<div class="appendix-divider">ภาคผนวก</div>']
        for item in plan.appendices:
            label = item.number if not item.title else f"{item.number} {item.title}".strip()
            parts.append(f'<div class="section-heading">{_escape_html(label)}</div>')
            if item.content:
                parts.append(self._format_body_html(item.content, "section-body"))
        return "\n".join(parts)

    def _html_table(self, payload: list[list[str]]) -> str:
        rows_html: list[str] = []
        for r_idx, row in enumerate(payload):
            tag = "th" if r_idx == 0 else "td"
            cells = "".join(f"<{tag}>{_escape_html(cell)}</{tag}>" for cell in row)
            rows_html.append(f"<tr>{cells}</tr>")
        return f'<table class="tor-table">{"".join(rows_html)}</table>'

    def _html_paragraphs(self, payload: object) -> list[str]:
        chunks: list[str] = []
        for para_text in str(payload).strip().split("\n"):
            cleaned = para_text.strip()
            if cleaned:
                chunks.append(f"<p>{_escape_html(cleaned)}</p>")
        return chunks

    def _format_body_html(self, text: str, css_class: str) -> str:
        """Format body text as HTML paragraphs and tables."""
        from app.services.thai_draft import split_content_blocks

        chunks: list[str] = []
        for kind, payload in split_content_blocks(text):
            if kind == "table" and isinstance(payload, list):
                chunks.append(self._html_table(payload))
                continue
            chunks.extend(self._html_paragraphs(payload))
        if not chunks:
            return ""
        return f'<div class="{css_class}">{"".join(chunks)}</div>'

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
