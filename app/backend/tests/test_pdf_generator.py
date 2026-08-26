"""Unit tests for the PDF generator.

Tests cover:
- PDF generation returns valid PDF bytes
- Content matches DOCX structure (same sections, same order)
- Thai formatting is preserved (dates, numerals, section headings)
- All TOR sections appear in the generated PDF
- Sub-sections are included
- Empty sections show placeholder
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.export.docx_generator import TOR_SECTION_LABELS, TOR_SECTION_ORDER, TORContent
from app.export.pdf_generator import PDFGenerator, _escape_html


# =============================================================================
# HTML Escape Utility Tests
# =============================================================================


class TestEscapeHtml:
    """Tests for the _escape_html utility function."""

    def test_escapes_ampersand(self):
        assert _escape_html("A & B") == "A &amp; B"

    def test_escapes_less_than(self):
        assert _escape_html("a < b") == "a &lt; b"

    def test_escapes_greater_than(self):
        assert _escape_html("a > b") == "a &gt; b"

    def test_escapes_double_quote(self):
        assert _escape_html('say "hello"') == "say &quot;hello&quot;"

    def test_no_escape_needed(self):
        assert _escape_html("ข้อความปกติ") == "ข้อความปกติ"

    def test_multiple_special_chars(self):
        assert _escape_html("<b>&</b>") == "&lt;b&gt;&amp;&lt;/b&gt;"


# =============================================================================
# PDF Generator Tests
# =============================================================================


class TestPDFGeneratorBasic:
    """Tests for basic PDF generation (with mocked WeasyPrint)."""

    def setup_method(self):
        self.generator = PDFGenerator()

    @patch("app.export.pdf_generator.PDFGenerator._render_pdf")
    def test_generate_returns_bytes(self, mock_render):
        """generate() should return bytes."""
        mock_render.return_value = b"%PDF-1.4 fake content"
        content = TORContent(project_name="Test Project")
        result = self.generator.generate(content)
        assert isinstance(result, bytes)

    @patch("app.export.pdf_generator.PDFGenerator._render_pdf")
    def test_generate_calls_render_with_html(self, mock_render):
        """generate() passes built HTML to _render_pdf."""
        mock_render.return_value = b"%PDF-1.4 fake"
        content = TORContent(project_name="ระบบ ICT")
        self.generator.generate(content)
        mock_render.assert_called_once()
        html_arg = mock_render.call_args[0][0]
        assert "ระบบ ICT" in html_arg

    @patch("app.export.pdf_generator.PDFGenerator._render_pdf")
    def test_generate_empty_content(self, mock_render):
        """Generator handles empty content without error."""
        mock_render.return_value = b"%PDF-1.4 empty"
        content = TORContent()
        result = self.generator.generate(content)
        assert isinstance(result, bytes)

    @patch("app.export.pdf_generator.PDFGenerator._render_pdf")
    def test_generate_with_all_sections(self, mock_render):
        """PDF generation succeeds with all sections populated."""
        mock_render.return_value = b"%PDF-1.4 full"
        sections = {key: f"เนื้อหา {label}" for key, label in TOR_SECTION_LABELS.items()}
        content = TORContent(
            project_name="โครงการทดสอบ",
            ministry="กระทรวงดิจิทัลฯ",
            budget=10_000_000,
            sections=sections,
        )
        result = self.generator.generate(content)
        assert isinstance(result, bytes)
        # Verify html passed to render contains the section content
        html_arg = mock_render.call_args[0][0]
        assert "โครงการทดสอบ" in html_arg


class TestPDFGeneratorHTMLContent:
    """Tests for the HTML building logic (content correctness)."""

    def setup_method(self):
        self.generator = PDFGenerator()

    def test_html_contains_title(self):
        """HTML includes the TOR title."""
        content = TORContent(project_name="Test")
        html = self.generator._build_html(content)
        assert "ร่างขอบเขตของงาน" in html
        assert "Terms of Reference" not in html

    def test_html_contains_project_name(self):
        """HTML includes the project name."""
        content = TORContent(project_name="โครงการ ICT")
        html = self.generator._build_html(content)
        assert "โครงการ ICT" in html

    def test_html_contains_ministry_in_header(self):
        """HTML includes the ministry in the header div."""
        content = TORContent(ministry="กระทรวงการคลัง")
        html = self.generator._build_html(content)
        assert "กระทรวงการคลัง" in html

    def test_html_contains_all_section_labels(self):
        """All 13 TOR section labels appear in the generated HTML."""
        content = TORContent(project_name="Test")
        html = self.generator._build_html(content)
        for label in TOR_SECTION_LABELS.values():
            assert label in html, f"Section label '{label}' not found in HTML"

    def test_sections_in_correct_order(self):
        """Sections appear in the correct numbered order."""
        content = TORContent(project_name="Test")
        html = self.generator._build_html(content)
        positions = []
        for i, key in enumerate(TOR_SECTION_ORDER, start=1):
            label = TOR_SECTION_LABELS[key]
            pos = html.find(f"{i}. {label}")
            assert pos >= 0, f"Section {i}. {label} not found"
            positions.append(pos)
        # Verify ordering
        assert positions == sorted(positions)

    def test_html_contains_section_content(self):
        """Section body text appears in the HTML."""
        content = TORContent(
            project_name="Test",
            sections={"s1": "เนื้อหาความเป็นมา"},
        )
        html = self.generator._build_html(content)
        assert "เนื้อหาความเป็นมา" in html

    def test_empty_section_shows_placeholder(self):
        """Empty sections show the placeholder text."""
        content = TORContent(project_name="Test")
        html = self.generator._build_html(content)
        assert "(ยังไม่ได้กรอกข้อมูล)" in html

    def test_html_contains_sub_sections(self):
        """Sub-sections are included in the HTML."""
        content = TORContent(
            project_name="Test",
            sections={"s4": "ขอบเขตงานหลัก"},
            sub_sections={"s4": {"4.1": "งานย่อยที่ 1", "4.2": "งานย่อยที่ 2"}},
        )
        html = self.generator._build_html(content)
        assert "4.1" in html
        assert "4.2" in html
        assert "งานย่อยที่ 1" in html
        assert "งานย่อยที่ 2" in html

    def test_thai_date_in_html(self):
        """Date appears in Thai Buddhist Era format."""
        content = TORContent(
            project_name="Test",
            export_date=date(2024, 8, 15),
        )
        html = self.generator._build_html(content)
        # Should contain Buddhist Era year 2567
        assert "2567" in html
        assert "สิงหาคม" in html

    def test_thai_numerals_in_sections(self):
        """When use_thai_numerals=True, section numbers use Thai digits."""
        content = TORContent(
            project_name="Test",
            use_thai_numerals=True,
            export_date=date(2024, 1, 1),
        )
        html = self.generator._build_html(content)
        # Section 1 should be "๑. ความเป็นมา"
        assert "๑. ความเป็นมา" in html
        # Date should use Thai numerals
        assert "๒๕๖๗" in html

    def test_html_escapes_special_characters(self):
        """HTML special characters in content are properly escaped."""
        content = TORContent(
            project_name="Test <script>alert('xss')</script>",
        )
        html = self.generator._build_html(content)
        # Should NOT contain raw <script> tags
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestPDFGeneratorMultiParagraph:
    """Tests for multi-paragraph content handling."""

    def setup_method(self):
        self.generator = PDFGenerator()

    def test_multi_paragraph_creates_multiple_p_tags(self):
        """Multiple lines in section content produce multiple <p> tags."""
        content = TORContent(
            project_name="Test",
            sections={"s1": "ย่อหน้าที่ 1\nย่อหน้าที่ 2\nย่อหน้าที่ 3"},
        )
        html = self.generator._build_html(content)
        assert html.count("<p>ย่อหน้าที่") == 3

    def test_empty_lines_are_skipped(self):
        """Empty lines in content don't produce empty paragraphs."""
        content = TORContent(
            project_name="Test",
            sections={"s1": "บรรทัด 1\n\n\nบรรทัด 2"},
        )
        html = self.generator._build_html(content)
        # Should only have 2 paragraphs, not 4
        assert "<p>บรรทัด 1</p>" in html
        assert "<p>บรรทัด 2</p>" in html
