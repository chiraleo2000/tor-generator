"""Property-based tests for RAG Chunking Preservation (Property 5).

Verifies that for any ingested document, concatenating all chunk texts in order
(accounting for overlap removal) reconstructs the original document text with
no content loss — chunking is a reversible split operation.

**Validates: Requirements 3.2, 3.3**

# Feature: tor-drafting-review-app, Property 5: RAG Chunking Preservation
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from app.rag.chunking import chunk_text, tokenize_thai


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Thai characters and common punctuation that would appear in procurement docs
thai_chars = st.sampled_from(
    list("กขคงจฉชซฌญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรลวศษสหฬอฮ")
    + list("ะาิีึืุูเแโใไำ")
    + list("่้๊๋็์ัิี")
    + list(" .,;:()0123456789")
)

# Strategy to generate Thai-like text that tokenizes into a predictable token count.
# We build text from Thai words to ensure PyThaiNLP produces meaningful tokens.
thai_word_pool = st.sampled_from([
    "การ", "จัดซื้อ", "จัดจ้าง", "และ", "การ", "บริหาร", "พัสดุ", "ภาครัฐ",
    "พ.ศ.", "2560", "งบประมาณ", "โครงการ", "ระบบ", "สำหรับ", "หน่วยงาน",
    "ของ", "รัฐ", "ที่", "ต้องการ", "ส่งเสริม", "หรือ", "สนับสนุน",
    "ขอบเขต", "งาน", "คุณสมบัติ", "ผู้เสนอราคา", "เงื่อนไข", "การจ่าย",
    "ค่าปรับ", "กำหนด", "ส่งมอบ", "ผลงาน", "ตรวจรับ", "พัสดุ",
    "วิธีการ", "ประกาศ", "เชิญชวน", "ทั่วไป", "คัดเลือก", "เฉพาะเจาะจง",
    "ระเบียบ", "กระทรวง", "การคลัง", "ว่าด้วย", "พระราชบัญญัติ",
    "ข้อ", "มาตรา", "หมวด", "บท", "ส่วน", "ตาม", "แห่ง", "ให้", "ไว้",
    "ดังนี้", "ต่อไปนี้", "เป็นต้น", "อย่างน้อย", "อย่างมาก",
    "ทดสอบ", "ระบบ", "พัฒนา", "ติดตั้ง", "บำรุงรักษา", "ซ่อมแซม",
    "รายงาน", "ผล", "การ", "ดำเนินงาน", "ประจำ", "ปี", "เดือน",
])

# Generate text by joining Thai words with spaces
# Min ~600 tokens to ensure multiple chunks, max ~3000 for reasonable test speed
thai_text_strategy = st.lists(
    thai_word_pool,
    min_size=600,
    max_size=3000,
).map(lambda words: "".join(words))

# Strategy for shorter texts that may produce 1 or very few chunks
short_thai_text_strategy = st.lists(
    thai_word_pool,
    min_size=1,
    max_size=100,
).map(lambda words: "".join(words))

# Strategy for texts with section headers
section_header_strategy = st.sampled_from([
    "\n# หมวดที่ 1 บททั่วไป\n",
    "\n## ข้อกำหนดและเงื่อนไข\n",
    "\nข้อ 1 ขอบเขตของงาน\n",
    "\nหมวด 2 การจัดซื้อจัดจ้าง\n",
    "\nมาตรา 5 บทนิยาม\n",
    "\n1. ความเป็นมา\n",
    "\n2. วัตถุประสงค์\n",
    "\n3. ขอบเขตงาน\n",
])

# Strategy for text with sections interspersed
thai_text_with_sections_strategy = st.lists(
    st.one_of(
        st.lists(thai_word_pool, min_size=50, max_size=200).map(lambda w: "".join(w)),
        section_header_strategy,
    ),
    min_size=5,
    max_size=20,
).map(lambda parts: "".join(parts))

# Chunking parameter strategies
overlap_strategy = st.integers(min_value=10, max_value=200)
min_chunk_strategy = st.integers(min_value=50, max_value=500)


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------


@pytest.mark.property
class TestRAGChunkingPreservation:
    """Property 5: RAG Chunking Preservation.

    For any ingested document, the concatenation of all chunk texts (in order,
    accounting for overlap removal) SHALL reconstruct the original document text
    with no content loss — chunking is a reversible split operation.
    """

    @given(text=thai_text_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 5: RAG Chunking Preservation
    def test_chunk_concatenation_preserves_all_tokens(self, text: str):
        """Concatenating chunks (with overlap removed) reconstructs original token sequence.

        For any Thai text, chunking and then reassembling by taking the first chunk
        in full and the non-overlapping portion of subsequent chunks must produce
        the exact same token sequence as tokenizing the original text.

        **Validates: Requirements 3.2, 3.3**
        """
        tokens = tokenize_thai(text)
        assume(len(tokens) > 0)

        overlap = 100
        result = chunk_text(
            text,
            document_id="prop-test-doc",
            min_chunk_size=500,
            max_chunk_size=1000,
            overlap_size=overlap,
        )

        if len(result.chunks) == 0:
            return

        if len(result.chunks) == 1:
            # Single chunk should contain all tokens
            assert result.chunks[0].tokens == tokens
            return

        # Reconstruct: first chunk fully + non-overlapping parts of subsequent chunks
        reconstructed_tokens: list[str] = list(result.chunks[0].tokens)
        for chunk in result.chunks[1:]:
            non_overlap = chunk.tokens[overlap:]
            reconstructed_tokens.extend(non_overlap)

        assert reconstructed_tokens == tokens

    @given(text=thai_text_with_sections_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 5: RAG Chunking Preservation
    def test_chunk_preservation_with_section_boundaries(self, text: str):
        """Chunking preserves content even when section boundaries influence split points.

        When section headers are present in the text, the chunker may split at
        different positions, but the reconstruction must still produce the original
        token sequence.

        **Validates: Requirements 3.2, 3.3**
        """
        tokens = tokenize_thai(text)
        assume(len(tokens) > 0)

        overlap = 100
        result = chunk_text(
            text,
            document_id="prop-test-sections",
            min_chunk_size=500,
            max_chunk_size=1000,
            overlap_size=overlap,
        )

        if len(result.chunks) == 0:
            return

        if len(result.chunks) == 1:
            assert result.chunks[0].tokens == tokens
            return

        # Reconstruct tokens
        reconstructed_tokens: list[str] = list(result.chunks[0].tokens)
        for chunk in result.chunks[1:]:
            non_overlap = chunk.tokens[overlap:]
            reconstructed_tokens.extend(non_overlap)

        assert reconstructed_tokens == tokens

    @given(
        text=thai_text_strategy,
        overlap=st.integers(min_value=10, max_value=150),
    )
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 5: RAG Chunking Preservation
    def test_chunk_preservation_with_varying_overlap(self, text: str, overlap: int):
        """Reconstruction works correctly for any valid overlap size.

        The overlap parameter controls how many tokens are duplicated between
        consecutive chunks. Regardless of the overlap value, removing those
        overlapping tokens must yield the complete original token sequence.

        **Validates: Requirements 3.2, 3.3**
        """
        tokens = tokenize_thai(text)
        assume(len(tokens) > 0)

        # Ensure min_chunk_size > overlap to avoid degenerate cases
        min_chunk_size = max(overlap + 50, 100)
        max_chunk_size = min_chunk_size + 500

        result = chunk_text(
            text,
            document_id="prop-test-overlap",
            min_chunk_size=min_chunk_size,
            max_chunk_size=max_chunk_size,
            overlap_size=overlap,
        )

        if len(result.chunks) == 0:
            return

        if len(result.chunks) == 1:
            assert result.chunks[0].tokens == tokens
            return

        # Reconstruct
        reconstructed_tokens: list[str] = list(result.chunks[0].tokens)
        for chunk in result.chunks[1:]:
            non_overlap = chunk.tokens[overlap:]
            reconstructed_tokens.extend(non_overlap)

        assert reconstructed_tokens == tokens

    @given(text=short_thai_text_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 5: RAG Chunking Preservation
    def test_short_text_single_chunk_preserves_content(self, text: str):
        """Short texts that fit in a single chunk preserve all content exactly.

        When the input text is shorter than min_chunk_size, it should produce
        exactly one chunk containing all original tokens.

        **Validates: Requirements 3.2, 3.3**
        """
        tokens = tokenize_thai(text)
        assume(len(tokens) > 0)

        result = chunk_text(
            text,
            document_id="prop-test-short",
            min_chunk_size=500,
            max_chunk_size=1000,
            overlap_size=100,
        )

        # Short text should produce exactly one chunk
        assert len(result.chunks) == 1
        assert result.chunks[0].tokens == tokens

    @given(text=thai_text_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 5: RAG Chunking Preservation
    def test_total_tokens_matches_original(self, text: str):
        """The reported total_tokens always matches the actual tokenization count.

        **Validates: Requirements 3.2, 3.3**
        """
        tokens = tokenize_thai(text)
        assume(len(tokens) > 0)

        result = chunk_text(
            text,
            document_id="prop-test-total",
            min_chunk_size=500,
            max_chunk_size=1000,
            overlap_size=100,
        )

        assert result.total_tokens == len(tokens)
