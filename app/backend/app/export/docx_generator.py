"""DOCX document generator for TOR export.

Generates Word (.docx) documents with Thai government formatting using python-docx.
Applies TH Sarabun New font, proper margins, headers, page numbering, and supports
Thai/Arabic numeral configuration for section numbering.

Requirements: 8.1, 8.3, 8.4, 16.3
"""

import io
from dataclasses import dataclass, field
from datetime import date, datetime

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from app.export.format_config import (
    BODY_FONT_SIZE_PT,
    FONT_NAME,
    FONT_NAME_FALLBACK,
    HEADER_FONT_SIZE_PT,
    HEADING_FONT_SIZE_PT,
    LINE_SPACING,
    PAGE_HEIGHT_CM,
    PAGE_MARGIN_LEFT_RIGHT_CM,
    PAGE_MARGIN_TOP_BOTTOM_CM,
    PAGE_WIDTH_CM,
    SUBHEADING_FONT_SIZE_PT,
    TITLE_BLOCK_NAME,
    apply_format,
)
from app.export.render_plan import AppendixItem, NumberingScheme
from app.export.thai_formatting import format_thai_date

BODY_FONT_SIZE = Pt(BODY_FONT_SIZE_PT)
HEADING_FONT_SIZE = Pt(HEADING_FONT_SIZE_PT)
SUBHEADING_FONT_SIZE = Pt(SUBHEADING_FONT_SIZE_PT)
HEADER_FONT_SIZE = Pt(HEADER_FONT_SIZE_PT)
PAGE_MARGIN_TOP_BOTTOM = Cm(PAGE_MARGIN_TOP_BOTTOM_CM)
PAGE_MARGIN_LEFT_RIGHT = Cm(PAGE_MARGIN_LEFT_RIGHT_CM)
W_RFONTS = "w:rFonts"


@dataclass
class TORContent:
    """Structured TOR content for DOCX generation.

    Attributes:
        project_name: Name of the project.
        ministry: Ministry/organization name.
        budget: Total budget in baht.
        project_type: Project type (it, construction, consulting, general).
        sections: Dict mapping section_key to content text.
        sub_sections: Dict mapping section_key to sub-section dict (sub_key → content).
        export_date: Date to display on the document (defaults to today).
        use_thai_numerals: Whether to use Thai numerals for dates and numbered headings.
        numbering_scheme: ``none`` (product default) or ``numbered_consecutive``.
        appendices: Optional appendix items; empty list is valid.
    """

    project_name: str = ""
    ministry: str = ""
    budget: int = 0
    project_type: str = "general"
    sections: dict[str, str] = field(default_factory=dict)
    sub_sections: dict[str, dict[str, str]] = field(default_factory=dict)
    export_date: date | datetime | None = None
    use_thai_numerals: bool = True
    numbering_scheme: NumberingScheme | str = NumberingScheme.NONE
    appendices: list[AppendixItem] = field(default_factory=list)


class DOCXGenerator:
    """Generates DOCX documents with Thai government formatting.

    Usage:
        generator = DOCXGenerator()
        content = TORContent(
            project_name="ระบบ ICT",
            ministry="กระทรวงดิจิทัลฯ",
            budget=5_000_000,
            sections={"s1": "ความเป็นมาของโครงการ..."},
        )
        docx_bytes = generator.generate(content)
    """

    def generate(self, content: TORContent) -> bytes:
        """Generate a DOCX file from TOR content.

        Args:
            content: Structured TOR content to render.

        Returns:
            Bytes representing the generated .docx file.
        """
        doc = Document()

        self._configure_page_setup(doc)
        self._set_default_font(doc)
        self._add_header(doc, content)
        self._add_page_numbers(doc)
        self._add_title(doc, content)
        self._add_document_info(doc, content)
        from app.export.export_plan import build_render_plan

        plan = build_render_plan(content)
        self._add_sections(doc, plan)
        self._add_appendices(doc, plan)

        # Write to bytes buffer
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()

    def _configure_page_setup(self, doc: Document) -> None:
        """Configure page orientation, margins, and size (A4)."""
        section = doc.sections[0]
        section.orientation = WD_ORIENT.PORTRAIT

        def set_page() -> None:
            section.page_width = Cm(PAGE_WIDTH_CM)
            section.page_height = Cm(PAGE_HEIGHT_CM)

        def set_margins() -> None:
            section.top_margin = PAGE_MARGIN_TOP_BOTTOM
            section.bottom_margin = PAGE_MARGIN_TOP_BOTTOM
            section.left_margin = PAGE_MARGIN_LEFT_RIGHT
            section.right_margin = PAGE_MARGIN_LEFT_RIGHT

        apply_format({"page": set_page, "margins": set_margins})

    def _apply_line_spacing(self, paragraph) -> None:
        paragraph.paragraph_format.line_spacing = LINE_SPACING

    def _set_default_font(self, doc: Document) -> None:
        """Set the default document font to TH Sarabun New 16pt with single line spacing."""
        style = doc.styles["Normal"]
        font = style.font
        font.name = FONT_NAME
        font.size = BODY_FONT_SIZE
        style.paragraph_format.line_spacing = LINE_SPACING

        self._bind_rfonts(style.element.get_or_add_rPr(), FONT_NAME, FONT_NAME)

        for heading_level in range(1, 4):
            style_name = f"Heading {heading_level}"
            if style_name not in doc.styles:
                continue
            h_style = doc.styles[style_name]
            h_font = h_style.font
            h_font.name = FONT_NAME
            h_font.size = HEADING_FONT_SIZE
            h_font.bold = True
            h_font.color.rgb = RGBColor(0, 0, 0)
            self._bind_rfonts(h_style.element.get_or_add_rPr(), FONT_NAME, FONT_NAME)

    def _add_header(self, doc: Document, content: TORContent) -> None:
        """Add document header with ministry/organization name."""
        section = doc.sections[0]
        header = section.header
        header_para = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
        header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

        run = header_para.add_run(content.ministry or "")
        run.font.name = FONT_NAME
        run.font.size = HEADER_FONT_SIZE
        self._set_run_font_cs(run)

    def _add_page_numbers(self, doc: Document) -> None:
        """Add page numbers to the document footer (centered)."""
        section = doc.sections[0]
        footer = section.footer
        footer_para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Add page number field code
        run = footer_para.add_run()
        fld_char_begin = OxmlElement("w:fldChar")
        fld_char_begin.set(qn("w:fldCharType"), "begin")
        run._r.append(fld_char_begin)

        run2 = footer_para.add_run()
        instr_text = OxmlElement("w:instrText")
        instr_text.set(qn("xml:space"), "preserve")
        instr_text.text = " PAGE "
        run2._r.append(instr_text)

        run3 = footer_para.add_run()
        fld_char_end = OxmlElement("w:fldChar")
        fld_char_end.set(qn("w:fldCharType"), "end")
        run3._r.append(fld_char_end)

    def _add_title(self, doc: Document, content: TORContent) -> None:
        """Add the document title (ร่างขอบเขตของงาน / TOR)."""
        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_para.space_before = Pt(0)
        title_para.space_after = Pt(12)
        self._apply_line_spacing(title_para)

        run = title_para.add_run(TITLE_BLOCK_NAME)
        run.bold = True
        run.font.name = FONT_NAME
        run.font.size = HEADING_FONT_SIZE
        self._set_run_font_cs(run)

        # Project name subtitle
        if content.project_name:
            subtitle_para = doc.add_paragraph()
            subtitle_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            subtitle_para.space_after = Pt(6)
            self._apply_line_spacing(subtitle_para)
            run = subtitle_para.add_run(content.project_name)
            run.bold = True
            run.font.name = FONT_NAME
            run.font.size = HEADING_FONT_SIZE
            self._set_run_font_cs(run)

    def _add_document_info(self, doc: Document, content: TORContent) -> None:
        """Add document metadata (date, budget summary)."""
        export_date = content.export_date or date.today()
        date_str = format_thai_date(export_date, use_thai_numerals=content.use_thai_numerals)

        info_para = doc.add_paragraph()
        info_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        info_para.space_after = Pt(12)
        self._apply_line_spacing(info_para)
        run = info_para.add_run(date_str)
        run.font.name = FONT_NAME
        run.font.size = BODY_FONT_SIZE
        self._set_run_font_cs(run)

        # Separator line
        doc.add_paragraph("─" * 60)

    def _add_sections(self, doc: Document, plan) -> None:
        """Add TOR sections from the shared RenderPlan."""
        for section in plan.body:
            heading_text = (
                f"{section.number}. {section.label}" if section.number else section.label
            )
            heading_para = doc.add_paragraph()
            heading_para.space_before = Pt(8)
            heading_para.space_after = Pt(4)
            self._apply_line_spacing(heading_para)
            run = heading_para.add_run(heading_text)
            run.bold = True
            run.font.name = FONT_NAME
            run.font.size = HEADING_FONT_SIZE
            self._set_run_font_cs(run)

            if section.content:
                self._write_content_blocks(doc, section.content, first_line_indent_cm=1.25)
            for sub in section.subsections:
                sub_heading = f"{sub.number} {sub.label}".strip()
                self._add_sub_heading(doc, sub_heading)
                if sub.content:
                    self._write_content_blocks(doc, sub.content, left_indent_cm=1.5)

    def _add_appendices(self, doc: Document, plan) -> None:
        divider = doc.add_paragraph()
        divider.space_before = Pt(16)
        divider.space_after = Pt(8)
        self._apply_line_spacing(divider)
        run = divider.add_run("ภาคผนวก")
        run.bold = True
        run.font.name = FONT_NAME
        run.font.size = HEADING_FONT_SIZE
        self._set_run_font_cs(run)
        for item in plan.appendices:
            heading_para = doc.add_paragraph()
            heading_para.space_before = Pt(8)
            heading_para.space_after = Pt(4)
            self._apply_line_spacing(heading_para)
            label = item.number if not item.title else f"{item.number} {item.title}".strip()
            run = heading_para.add_run(label)
            run.bold = True
            run.font.name = FONT_NAME
            run.font.size = HEADING_FONT_SIZE
            self._set_run_font_cs(run)
            if item.content:
                self._write_content_blocks(doc, item.content, first_line_indent_cm=1.25)

    def _write_content_blocks(
        self,
        doc: Document,
        text: str,
        *,
        first_line_indent_cm: float | None = None,
        left_indent_cm: float | None = None,
    ) -> None:
        from app.services.thai_draft import split_content_blocks

        for kind, payload in split_content_blocks(text):
            if kind == "table" and isinstance(payload, list):
                self._add_markdown_table(doc, payload)
                continue
            for para_text in str(payload).strip().split("\n"):
                cleaned = para_text.strip()
                if not cleaned:
                    continue
                para = doc.add_paragraph()
                if first_line_indent_cm is not None:
                    para.paragraph_format.first_line_indent = Cm(first_line_indent_cm)
                if left_indent_cm is not None:
                    para.paragraph_format.left_indent = Cm(left_indent_cm)
                self._apply_line_spacing(para)
                run = para.add_run(cleaned)
                run.font.name = FONT_NAME
                run.font.size = BODY_FONT_SIZE
                self._set_run_font_cs(run)

    def _add_markdown_table(self, doc: Document, rows: list[list[str]]) -> None:
        if not rows:
            return
        cols = max(len(row) for row in rows)
        table = doc.add_table(rows=len(rows), cols=cols)
        table.style = "Table Grid"
        for r_idx, row in enumerate(rows):
            for c_idx in range(cols):
                cell_text = row[c_idx] if c_idx < len(row) else ""
                cell = table.rows[r_idx].cells[c_idx]
                cell.text = ""
                para = cell.paragraphs[0]
                self._apply_line_spacing(para)
                run = para.add_run(cell_text)
                run.font.name = FONT_NAME
                run.font.size = BODY_FONT_SIZE
                run.bold = r_idx == 0
                self._set_run_font_cs(run)

    def _add_sub_heading(self, doc: Document, heading: str) -> None:
        sub_heading_para = doc.add_paragraph()
        sub_heading_para.space_before = Pt(4)
        sub_heading_para.space_after = Pt(2)
        sub_heading_para.paragraph_format.left_indent = Cm(1.0)
        self._apply_line_spacing(sub_heading_para)
        run = sub_heading_para.add_run(heading)
        run.bold = True
        run.font.name = FONT_NAME
        run.font.size = SUBHEADING_FONT_SIZE
        self._set_run_font_cs(run)

    @staticmethod
    def _bind_rfonts(rpr, ascii_name: str, east_asia: str) -> None:
        rfonts = rpr.find(qn(W_RFONTS))
        if rfonts is None:
            rfonts = OxmlElement(W_RFONTS)
            rpr.append(rfonts)
        rfonts.set(qn("w:ascii"), ascii_name)
        rfonts.set(qn("w:hAnsi"), ascii_name)
        rfonts.set(qn("w:cs"), east_asia)
        rfonts.set(qn("w:eastAsia"), east_asia)

    def _set_run_font_cs(self, run) -> None:
        """Set Thai-capable fonts on a run (primary + fallback)."""
        rpr = run._r.get_or_add_rPr()
        primary = FONT_NAME or FONT_NAME_FALLBACK
        self._bind_rfonts(rpr, primary, FONT_NAME)
        sz_cs = rpr.find(qn("w:szCs"))
        if sz_cs is None:
            sz_cs = OxmlElement("w:szCs")
            rpr.append(sz_cs)
        if run.font.size:
            sz_cs.set(qn("w:val"), str(int(run.font.size.pt * 2)))
