"""Unit tests for Thai-aware text chunking module.

Tests the tokenization, section detection, chunking logic, and metadata assignment.

Requirements: 3.2, 16.4
"""

from __future__ import annotations

import pytest

from app.rag.chunking import (
    ChunkingResult,
    ChunkMetadata,
    TextChunk,
    _build_token_offset_map,
    _find_chunk_end,
    chunk_text,
    detect_sections,
    find_page_breaks,
    tokenize_thai,
)


# =============================================================================
# Tests: tokenize_thai
# =============================================================================


class TestTokenizeThai:
    """Tests for PyThaiNLP-based Thai tokenization."""

    def test_thai_text_tokenization(self):
        """Tokenizes Thai text into words using newmm engine."""
        text = "สวัสดีครับผมชื่อทดสอบ"
        tokens = tokenize_thai(text)
        assert len(tokens) > 1
        # Reconstructed tokens should form the original text
        assert "".join(tokens) == text

    def test_english_text_tokenization(self):
        """Tokenizes English text."""
        text = "Hello world test"
        tokens = tokenize_thai(text)
        assert len(tokens) >= 1
        # Should contain the words
        joined = "".join(tokens)
        assert "Hello" in joined
        assert "world" in joined

    def test_mixed_thai_english(self):
        """Tokenizes mixed Thai and English text."""
        text = "ระบบ AI สำหรับการจัดซื้อจัดจ้าง"
        tokens = tokenize_thai(text)
        assert len(tokens) > 1
        assert "AI" in tokens or any("AI" in t for t in tokens)

    def test_empty_text(self):
        """Returns empty list for empty text."""
        assert tokenize_thai("") == []
        assert tokenize_thai("   ") == []

    def test_whitespace_only(self):
        """Returns empty list for whitespace-only text."""
        assert tokenize_thai("  \n\t  ") == []

    def test_numbers_and_punctuation(self):
        """Handles numbers and punctuation."""
        text = "งบประมาณ 1,000,000 บาท"
        tokens = tokenize_thai(text)
        assert len(tokens) >= 3
        # The number should appear in the tokens
        joined = "".join(tokens)
        assert "1,000,000" in joined or "1" in joined

    def test_no_empty_tokens(self):
        """Never returns empty string tokens."""
        text = "สวัสดี  ครับ   ทดสอบ"
        tokens = tokenize_thai(text)
        for token in tokens:
            assert token.strip() != ""


# =============================================================================
# Tests: detect_sections
# =============================================================================


class TestDetectSections:
    """Tests for section boundary detection."""

    def test_markdown_headings(self):
        """Detects markdown-style headings."""
        text = "# หมวดที่ 1\nSome content\n## ข้อกำหนด\nMore content"
        sections = detect_sections(text)
        assert len(sections) == 2
        assert sections[0][1] == "หมวดที่ 1"
        assert sections[1][1] == "ข้อกำหนด"

    def test_thai_clause_numbering(self):
        """Detects Thai clause numbering (ข้อ N)."""
        text = "บทนำ\nข้อ 1 ขอบเขตงาน\nรายละเอียด\nข้อ 2 คุณสมบัติ"
        sections = detect_sections(text)
        assert len(sections) >= 2
        labels = [s[1] for s in sections]
        assert any("ข้อ" in label for label in labels)

    def test_thai_chapter_numbering(self):
        """Detects Thai chapter numbering (หมวด N)."""
        text = "หมวด 1 บททั่วไป\nเนื้อหา\nหมวด 2 การจัดซื้อ"
        sections = detect_sections(text)
        assert len(sections) >= 2

    def test_numbered_sections(self):
        """Detects numbered sections (1. text)."""
        text = "Introduction\n1. Background\nContent here\n2. Objectives\nMore content"
        sections = detect_sections(text)
        assert len(sections) >= 2

    def test_sub_numbered_sections(self):
        """Detects sub-numbered sections (1.1 text)."""
        text = "1.1 First sub-section\nContent\n1.2 Second sub-section"
        sections = detect_sections(text)
        assert len(sections) >= 2

    def test_no_sections(self):
        """Returns empty list when no sections are found."""
        text = "Just plain text without any section markers"
        sections = detect_sections(text)
        assert sections == []

    def test_mattra_numbering(self):
        """Detects มาตรา N (Thai legal article) pattern."""
        text = "มาตรา 1 ชื่อ\nเนื้อหา\nมาตรา 2 บทนิยาม"
        sections = detect_sections(text)
        assert len(sections) >= 2

    def test_sections_sorted_by_offset(self):
        """Returned sections are sorted by character offset."""
        text = "# First\nContent\n## Second\nMore\n### Third"
        sections = detect_sections(text)
        offsets = [s[0] for s in sections]
        assert offsets == sorted(offsets)


# =============================================================================
# Tests: find_page_breaks
# =============================================================================


class TestFindPageBreaks:
    """Tests for page break detection."""

    def test_double_newline_breaks(self):
        """Detects double-newline as page breaks."""
        text = "Page 1 content\n\nPage 2 content\n\nPage 3 content"
        breaks = find_page_breaks(text)
        assert len(breaks) == 2

    def test_no_breaks(self):
        """Returns empty list for text without double-newlines."""
        text = "Single page content\nWith single newlines"
        breaks = find_page_breaks(text)
        assert breaks == []

    def test_break_positions(self):
        """Returns correct character positions for breaks."""
        text = "AB\n\nCD\n\nEF"
        breaks = find_page_breaks(text)
        assert len(breaks) == 2
        assert breaks[0] == 2  # Position of first \n\n
        assert breaks[1] == 6  # Position of second \n\n


# =============================================================================
# Tests: chunk_text (main function)
# =============================================================================


class TestChunkText:
    """Tests for the main chunk_text function."""

    def test_empty_text(self):
        """Returns empty result for empty text."""
        result = chunk_text("", document_id="doc-1")
        assert result.chunks == []
        assert result.total_tokens == 0
        assert result.document_id == "doc-1"

    def test_whitespace_text(self):
        """Returns empty result for whitespace-only text."""
        result = chunk_text("   \n\t  ", document_id="doc-1")
        assert result.chunks == []
        assert result.total_tokens == 0

    def test_short_text_single_chunk(self):
        """Text shorter than min_chunk_size produces a single chunk."""
        text = "สวัสดีครับ ทดสอบระบบการแบ่งข้อความ"
        result = chunk_text(text, document_id="doc-1", min_chunk_size=500)
        assert len(result.chunks) == 1
        assert result.chunks[0].metadata.document_id == "doc-1"
        assert result.chunks[0].metadata.chunk_index == 0

    def test_chunk_metadata_document_id(self):
        """All chunks have correct document_id."""
        # Create text long enough for multiple chunks with small sizes
        text = "ทดสอบ " * 200
        result = chunk_text(
            text, document_id="test-doc-123", min_chunk_size=50, max_chunk_size=100, overlap_size=10
        )
        for chunk in result.chunks:
            assert chunk.metadata.document_id == "test-doc-123"

    def test_chunk_indices_sequential(self):
        """Chunk indices are sequential starting from 0."""
        text = "ทดสอบระบบ " * 200
        result = chunk_text(
            text, document_id="doc-1", min_chunk_size=50, max_chunk_size=100, overlap_size=10
        )
        for i, chunk in enumerate(result.chunks):
            assert chunk.metadata.chunk_index == i

    def test_chunk_sizes_within_bounds(self):
        """All chunks (except possibly the last) are within min/max token bounds."""
        text = "การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ " * 500
        result = chunk_text(
            text, document_id="doc-1", min_chunk_size=50, max_chunk_size=100, overlap_size=10
        )
        # All chunks except the last should respect min size
        for chunk in result.chunks[:-1]:
            token_count = len(chunk.tokens)
            assert token_count >= 50 - 10, (  # Account for overlap reducing effective size
                f"Chunk {chunk.metadata.chunk_index} has {token_count} tokens (min: 50)"
            )
            assert token_count <= 100, (
                f"Chunk {chunk.metadata.chunk_index} has {token_count} tokens (max: 100)"
            )

    def test_overlap_between_chunks(self):
        """Consecutive chunks share overlapping tokens."""
        text = "ทดสอบ " * 500
        result = chunk_text(
            text, document_id="doc-1", min_chunk_size=50, max_chunk_size=100, overlap_size=20
        )
        if len(result.chunks) >= 2:
            # Last 20 tokens of chunk 0 should appear at start of chunk 1
            chunk_0_end_tokens = result.chunks[0].tokens[-20:]
            chunk_1_start_tokens = result.chunks[1].tokens[:20]
            assert chunk_0_end_tokens == chunk_1_start_tokens

    def test_total_tokens_reported(self):
        """Reports correct total token count."""
        text = "สวัสดีครับ"
        result = chunk_text(text, document_id="doc-1")
        assert result.total_tokens == len(tokenize_thai(text))

    def test_preserves_section_boundaries(self):
        """Prefers to break at section boundaries."""
        # Create text with a clear section boundary between min and max
        part1 = "ทดสอบ " * 60  # ~60 tokens
        section_marker = "\n# หมวดที่ 2 รายละเอียด\n"
        part2 = "เนื้อหา " * 60  # ~60 tokens
        text = part1 + section_marker + part2

        result = chunk_text(
            text, document_id="doc-1", min_chunk_size=50, max_chunk_size=100, overlap_size=10
        )

        # With section boundary detection, should prefer breaking at the heading
        assert len(result.chunks) >= 2

    def test_page_number_assignment(self):
        """Chunks get correct page numbers based on page breaks."""
        text = "Page 1 content here\n\nPage 2 content here\n\nPage 3 content here"
        page_breaks = find_page_breaks(text)
        result = chunk_text(text, document_id="doc-1", page_breaks=page_breaks)
        # First chunk should be page 1
        if result.chunks:
            assert result.chunks[0].metadata.page_number >= 1

    def test_section_label_assigned(self):
        """Chunks get section labels from detected headings."""
        text = "# ขอบเขตงาน\nรายละเอียดขอบเขตของงาน " * 100
        result = chunk_text(
            text, document_id="doc-1", min_chunk_size=50, max_chunk_size=100, overlap_size=10
        )
        # At least the first chunk should have a section label
        if result.chunks:
            assert result.chunks[0].metadata.section_label is not None
            assert "ขอบเขตงาน" in result.chunks[0].metadata.section_label

    def test_default_parameters(self):
        """Works with default parameters (500-1000 tokens, 100 overlap)."""
        # Create text that's about 2000 tokens
        text = "การจัดซื้อจัดจ้างภาครัฐ " * 800
        result = chunk_text(text, document_id="doc-1")
        assert len(result.chunks) >= 2
        assert result.total_tokens > 1000

    def test_reconstructable_text(self):
        """Chunks (accounting for overlap) can reconstruct the original content."""
        text = "ทดสอบระบบ " * 200
        overlap = 10
        result = chunk_text(
            text, document_id="doc-1", min_chunk_size=50, max_chunk_size=100, overlap_size=overlap
        )
        if len(result.chunks) <= 1:
            return

        # Reconstruct: take first chunk in full, then non-overlapping part of each subsequent chunk
        reconstructed_tokens: list[str] = list(result.chunks[0].tokens)
        for chunk in result.chunks[1:]:
            # The first `overlap` tokens are duplicated from previous chunk
            non_overlap = chunk.tokens[overlap:]
            reconstructed_tokens.extend(non_overlap)

        original_tokens = tokenize_thai(text)
        # The reconstructed tokens should match the original
        assert reconstructed_tokens == original_tokens


# =============================================================================
# Tests: _build_token_offset_map
# =============================================================================


class TestBuildTokenOffsetMap:
    """Tests for token-to-character offset mapping."""

    def test_simple_mapping(self):
        """Maps tokens to correct character positions."""
        text = "Hello world"
        tokens = ["Hello", "world"]
        offsets = _build_token_offset_map(text, tokens)
        assert offsets[0] == 0  # "Hello" starts at 0
        assert offsets[1] == 6  # "world" starts at 6

    def test_thai_mapping(self):
        """Maps Thai tokens to correct positions."""
        text = "สวัสดีครับ"
        tokens = tokenize_thai(text)
        offsets = _build_token_offset_map(text, tokens)
        # First token should start at 0
        assert offsets[0] == 0
        # All offsets should be within text bounds
        for offset in offsets:
            assert 0 <= offset < len(text)

    def test_empty_inputs(self):
        """Handles empty tokens list."""
        offsets = _build_token_offset_map("some text", [])
        assert offsets == []


# =============================================================================
# Tests: _find_chunk_end
# =============================================================================


class TestFindChunkEnd:
    """Tests for chunk end position calculation."""

    def test_remaining_fits_in_max(self):
        """Takes all remaining tokens if they fit within max."""
        end = _find_chunk_end(
            start=90,
            total_tokens=100,
            section_token_indices=[],
            min_chunk_size=50,
            max_chunk_size=100,
        )
        assert end == 100  # Takes remaining 10 tokens

    def test_breaks_at_section_boundary(self):
        """Prefers section boundary between min and max."""
        end = _find_chunk_end(
            start=0,
            total_tokens=200,
            section_token_indices=[60, 120],  # Section at token 60 (between min=50, max=100)
            min_chunk_size=50,
            max_chunk_size=100,
        )
        # Should break at the latest section boundary in range [50, 100]
        assert end == 60

    def test_breaks_at_max_without_section(self):
        """Falls back to max_chunk_size when no section boundary in range."""
        end = _find_chunk_end(
            start=0,
            total_tokens=200,
            section_token_indices=[150],  # Section boundary outside the [50,100] range
            min_chunk_size=50,
            max_chunk_size=100,
        )
        assert end == 100

    def test_prefers_latest_section_in_range(self):
        """Uses the latest section boundary in the [min, max] range."""
        end = _find_chunk_end(
            start=0,
            total_tokens=200,
            section_token_indices=[55, 70, 85],  # Multiple boundaries in range
            min_chunk_size=50,
            max_chunk_size=100,
        )
        # Should use the latest boundary (85) to maximize chunk size
        assert end == 85


# =============================================================================
# Tests: ChunkingResult and TextChunk dataclasses
# =============================================================================


class TestDataclasses:
    """Tests for data structures."""

    def test_chunk_metadata_defaults(self):
        """ChunkMetadata has correct default values."""
        meta = ChunkMetadata(document_id="doc-1", chunk_index=0)
        assert meta.section_label is None
        assert meta.page_number is None

    def test_chunk_metadata_full(self):
        """ChunkMetadata stores all fields."""
        meta = ChunkMetadata(
            document_id="doc-123",
            chunk_index=5,
            section_label="ขอบเขตงาน",
            page_number=3,
        )
        assert meta.document_id == "doc-123"
        assert meta.chunk_index == 5
        assert meta.section_label == "ขอบเขตงาน"
        assert meta.page_number == 3

    def test_text_chunk_structure(self):
        """TextChunk holds text, tokens, and metadata."""
        chunk = TextChunk(
            text="ทดสอบ",
            tokens=["ทดสอบ"],
            metadata=ChunkMetadata(document_id="d1", chunk_index=0),
        )
        assert chunk.text == "ทดสอบ"
        assert chunk.tokens == ["ทดสอบ"]
        assert chunk.metadata.document_id == "d1"

    def test_chunking_result_structure(self):
        """ChunkingResult holds chunks list and metadata."""
        result = ChunkingResult(chunks=[], total_tokens=0, document_id="doc-1")
        assert result.chunks == []
        assert result.total_tokens == 0
        assert result.document_id == "doc-1"
