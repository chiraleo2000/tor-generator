"""Thai-aware text chunking module.

Segments text using PyThaiNLP's newmm dictionary-based tokenizer for proper Thai
word boundaries, then splits into chunks of 500–1000 tokens with 100-token overlap,
preserving section boundaries.

Requirements: 3.2, 16.4
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from pythainlp.tokenize import word_tokenize

logger = logging.getLogger(__name__)

# Chunking parameters (in tokens)
DEFAULT_MIN_CHUNK_SIZE = 500
DEFAULT_MAX_CHUNK_SIZE = 1000
DEFAULT_OVERLAP_SIZE = 100

# Pattern to detect section headers in extracted text
# Matches lines starting with:
#   - Markdown-style headings: # Heading, ## Subheading
#   - Thai section numbering: ข้อ 1, หมวด 1, ส่วนที่ 1
#   - Arabic/Thai numeral section patterns: 1. , 1.1 , ๑. , ๑.๑
SECTION_HEADER_PATTERN = re.compile(
    r"^(?:"
    r"#{1,6}\s+.+"  # Markdown headings
    r"|ข้อ\s*\d+"  # ข้อ N (Thai clause)
    r"|หมวด\s*\d+"  # หมวด N (Thai chapter)
    r"|ส่วนที่\s*\d+"  # ส่วนที่ N (Thai part)
    r"|มาตรา\s*\d+"  # มาตรา N (Thai section/article)
    r"|\d+\.\s+\S"  # 1. ... (numbered section)
    r"|\d+\.\d+\s+\S"  # 1.1 ... (sub-numbered section)
    r"|[๐-๙]+\.\s+\S"  # ๑. ... (Thai numeral section)
    r"|[๐-๙]+\.[๐-๙]+\s+\S"  # ๑.๑ ... (Thai numeral sub-section)
    r")",
    re.MULTILINE,
)


@dataclass
class ChunkMetadata:
    """Metadata associated with a text chunk.

    Attributes:
        document_id: Identifier of the source document.
        chunk_index: Zero-based index of this chunk within the document.
        section_label: Label of the section this chunk belongs to (if detected).
        page_number: Page number where this chunk starts (if available).
    """

    document_id: str
    chunk_index: int
    section_label: str | None = None
    page_number: int | None = None


@dataclass
class TextChunk:
    """A chunk of text with associated metadata.

    Attributes:
        text: The chunk text content.
        tokens: List of tokens (words) in this chunk.
        metadata: Chunk metadata including position and source info.
    """

    text: str
    tokens: list[str]
    metadata: ChunkMetadata


@dataclass
class ChunkingResult:
    """Result of chunking a document.

    Attributes:
        chunks: List of TextChunk objects produced from the document.
        total_tokens: Total number of tokens in the original document.
        document_id: The source document identifier.
    """

    chunks: list[TextChunk]
    total_tokens: int
    document_id: str


def tokenize_thai(text: str) -> list[str]:
    """Tokenize text using PyThaiNLP's newmm (dictionary-based) engine.

    Handles mixed Thai/English text. The newmm engine uses maximum matching
    with a Thai dictionary for proper word boundary detection.

    Args:
        text: Input text (Thai, English, or mixed).

    Returns:
        List of word tokens.
    """
    if not text or not text.strip():
        return []

    tokens = word_tokenize(text, engine="newmm", keep_whitespace=False)
    # Filter out empty tokens
    return [t for t in tokens if t.strip()]


def detect_sections(text: str) -> list[tuple[int, str]]:
    """Detect section boundaries in the text.

    Finds lines that appear to be section headers and returns their
    character positions and labels.

    Args:
        text: The full document text.

    Returns:
        List of (char_offset, section_label) tuples, sorted by offset.
    """
    sections: list[tuple[int, str]] = []

    for match in SECTION_HEADER_PATTERN.finditer(text):
        offset = match.start()
        label = match.group().strip()
        # Clean up markdown heading markers for the label
        if label.startswith("#"):
            label = label.lstrip("#").strip()
        sections.append((offset, label))

    return sections


def _estimate_page_at_offset(
    char_offset: int, page_breaks: list[int], default_page: int = 1
) -> int:
    """Estimate the page number for a given character offset.

    Args:
        char_offset: Character position in the text.
        page_breaks: Sorted list of character offsets where page breaks occur.
        default_page: Default page number if no page breaks are provided.

    Returns:
        Estimated page number (1-based).
    """
    if not page_breaks:
        return default_page

    page = 1
    for break_offset in page_breaks:
        if char_offset >= break_offset:
            page += 1
        else:
            break
    return page


def find_page_breaks(text: str) -> list[int]:
    """Find page break positions in text.

    Looks for double-newline separated blocks (from PDF page concatenation)
    as page boundary indicators.

    Args:
        text: The full document text.

    Returns:
        List of character offsets where page breaks occur.
    """
    breaks: list[int] = []
    # PDF extraction joins pages with double newline
    pattern = re.compile(r"\n\n")
    for match in pattern.finditer(text):
        breaks.append(match.start())
    return breaks


def chunk_text(
    text: str,
    document_id: str,
    min_chunk_size: int = DEFAULT_MIN_CHUNK_SIZE,
    max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
    overlap_size: int = DEFAULT_OVERLAP_SIZE,
    page_breaks: list[int] | None = None,
) -> ChunkingResult:
    """Chunk text into segments preserving Thai word boundaries and section structure.

    The algorithm:
    1. Tokenize the full text using PyThaiNLP's newmm engine.
    2. Detect section boundaries in the original text.
    3. Split tokens into chunks of 500–1000 tokens with 100-token overlap.
    4. Prefer to break at section boundaries when possible.
    5. Attach metadata (document_id, chunk_index, section_label, page_number) to each chunk.

    Args:
        text: The document text to chunk.
        document_id: Identifier for the source document.
        min_chunk_size: Minimum tokens per chunk (default 500).
        max_chunk_size: Maximum tokens per chunk (default 1000).
        overlap_size: Number of overlapping tokens between consecutive chunks (default 100).
        page_breaks: Optional list of character offsets indicating page boundaries.

    Returns:
        ChunkingResult with list of chunks and metadata.
    """
    if not text or not text.strip():
        return ChunkingResult(chunks=[], total_tokens=0, document_id=document_id)

    # Step 1: Tokenize the full text
    tokens = tokenize_thai(text)
    total_tokens = len(tokens)

    if total_tokens == 0:
        return ChunkingResult(chunks=[], total_tokens=0, document_id=document_id)

    # Step 2: Detect section boundaries
    sections = detect_sections(text)

    # Step 3: Map token indices to character offsets for section boundary alignment
    # Build a mapping of cumulative token text to find section boundaries in token space
    token_char_offsets = _build_token_offset_map(text, tokens)

    # Step 4: Find section boundary positions in token index space
    section_token_indices = _map_sections_to_token_indices(sections, token_char_offsets)

    # Step 5: Determine page breaks
    if page_breaks is None:
        page_breaks = find_page_breaks(text)

    # Step 6: Create chunks with overlap, preferring section boundaries
    chunks = _create_chunks(
        tokens=tokens,
        text=text,
        token_char_offsets=token_char_offsets,
        section_token_indices=section_token_indices,
        sections=sections,
        page_breaks=page_breaks,
        document_id=document_id,
        min_chunk_size=min_chunk_size,
        max_chunk_size=max_chunk_size,
        overlap_size=overlap_size,
    )

    return ChunkingResult(
        chunks=chunks,
        total_tokens=total_tokens,
        document_id=document_id,
    )


def _build_token_offset_map(text: str, tokens: list[str]) -> list[int]:
    """Build a mapping from token index to character offset in the original text.

    For each token, finds its starting character position in the text.
    This enables mapping between token-space and character-space for
    section boundary alignment.

    Args:
        text: The original text.
        tokens: List of tokens from tokenization.

    Returns:
        List of character offsets, one per token. offset[i] is the start
        position of tokens[i] in the original text.
    """
    offsets: list[int] = []
    search_start = 0

    for token in tokens:
        idx = text.find(token, search_start)
        if idx == -1:
            # Token not found from search_start, try from beginning
            # This can happen with whitespace-stripped tokens
            idx = text.find(token)
            if idx == -1:
                # Last resort: use current position
                idx = search_start
        offsets.append(idx)
        search_start = idx + len(token)

    return offsets


def _map_sections_to_token_indices(
    sections: list[tuple[int, str]],
    token_char_offsets: list[int],
) -> list[int]:
    """Map section character offsets to token indices.

    For each section boundary (char offset), find the closest token index.

    Args:
        sections: List of (char_offset, label) tuples.
        token_char_offsets: List of char offsets per token.

    Returns:
        Sorted list of token indices where section boundaries occur.
    """
    if not sections or not token_char_offsets:
        return []

    section_indices: list[int] = []
    for char_offset, _ in sections:
        # Binary search for the token index closest to this char offset
        token_idx = _find_closest_token_index(char_offset, token_char_offsets)
        section_indices.append(token_idx)

    return sorted(set(section_indices))


def _find_closest_token_index(char_offset: int, token_char_offsets: list[int]) -> int:
    """Find the token index whose character offset is closest to the given offset.

    Uses binary search for efficiency.

    Args:
        char_offset: Target character offset.
        token_char_offsets: Sorted list of token character offsets.

    Returns:
        Index of the closest token.
    """
    lo, hi = 0, len(token_char_offsets) - 1

    while lo < hi:
        mid = (lo + hi) // 2
        if token_char_offsets[mid] < char_offset:
            lo = mid + 1
        else:
            hi = mid

    # lo is now the first token at or after char_offset
    if lo > 0:
        # Check if the previous token is closer
        if abs(token_char_offsets[lo - 1] - char_offset) <= abs(
            token_char_offsets[lo] - char_offset
        ):
            return lo - 1
    return lo


def _get_section_label_at_token(
    token_idx: int,
    _section_token_indices: list[int],
    sections: list[tuple[int, str]],
    token_char_offsets: list[int],
) -> str | None:
    """Get the section label that applies at a given token index.

    Finds the most recent section header before or at the token index.

    Args:
        token_idx: The token index to look up.
        section_token_indices: Sorted list of token indices with section boundaries.
        sections: Original (char_offset, label) tuples.
        token_char_offsets: Token-to-char offset mapping.

    Returns:
        Section label string or None if before any section.
    """
    if not sections or not token_char_offsets:
        return None

    # Find the char offset of this token
    if token_idx >= len(token_char_offsets):
        token_idx = len(token_char_offsets) - 1
    char_offset = token_char_offsets[token_idx]

    # Find the latest section that starts at or before this char offset
    current_label = None
    for sec_offset, label in sections:
        if sec_offset <= char_offset:
            current_label = label
        else:
            break

    return current_label


def _create_chunks(
    tokens: list[str],
    text: str,
    token_char_offsets: list[int],
    section_token_indices: list[int],
    sections: list[tuple[int, str]],
    page_breaks: list[int],
    document_id: str,
    min_chunk_size: int,
    max_chunk_size: int,
    overlap_size: int,
) -> list[TextChunk]:
    """Create text chunks with overlap, preferring section boundaries.

    Algorithm:
    - Start at token 0 (or after overlap from previous chunk).
    - Accumulate tokens until reaching min_chunk_size.
    - Look for a section boundary between min_chunk_size and max_chunk_size.
    - If found, break at the section boundary.
    - If not found, break at max_chunk_size.
    - Apply overlap: next chunk starts overlap_size tokens before the end of current.

    Args:
        tokens: All tokens from the document.
        text: Original text.
        token_char_offsets: Character offset per token.
        section_token_indices: Token indices where sections start.
        sections: Section (char_offset, label) pairs.
        page_breaks: Character offsets of page breaks.
        document_id: Source document ID.
        min_chunk_size: Minimum tokens per chunk.
        max_chunk_size: Maximum tokens per chunk.
        overlap_size: Token overlap between consecutive chunks.

    Returns:
        List of TextChunk objects.
    """
    total_tokens = len(tokens)
    if total_tokens == 0:
        return []

    chunks: list[TextChunk] = []
    chunk_index = 0
    start = 0

    while start < total_tokens:
        # Determine the end position for this chunk
        end = _find_chunk_end(
            start=start,
            total_tokens=total_tokens,
            section_token_indices=section_token_indices,
            min_chunk_size=min_chunk_size,
            max_chunk_size=max_chunk_size,
        )

        # Extract chunk tokens and reconstruct text
        chunk_tokens = tokens[start:end]
        chunk_text = "".join(chunk_tokens)

        # Determine section label for this chunk
        section_label = _get_section_label_at_token(
            start, section_token_indices, sections, token_char_offsets
        )

        # Determine page number
        chunk_char_offset = token_char_offsets[start] if start < len(token_char_offsets) else 0
        page_number = _estimate_page_at_offset(chunk_char_offset, page_breaks)

        # Create chunk
        chunk = TextChunk(
            text=chunk_text,
            tokens=chunk_tokens,
            metadata=ChunkMetadata(
                document_id=document_id,
                chunk_index=chunk_index,
                section_label=section_label,
                page_number=page_number,
            ),
        )
        chunks.append(chunk)

        chunk_index += 1

        # Calculate next start with overlap
        next_start = end - overlap_size
        if next_start <= start:
            # Avoid infinite loop: always advance
            next_start = end

        # If we've consumed all tokens, stop
        if end >= total_tokens:
            break

        start = next_start

    return chunks


def _find_chunk_end(
    start: int,
    total_tokens: int,
    section_token_indices: list[int],
    min_chunk_size: int,
    max_chunk_size: int,
) -> int:
    """Find the optimal end position for a chunk starting at `start`.

    Prefers breaking at section boundaries between min and max chunk size.
    If no section boundary is found in that range, breaks at max_chunk_size.

    Args:
        start: Starting token index.
        total_tokens: Total number of tokens in the document.
        section_token_indices: Token indices where sections begin.
        min_chunk_size: Minimum chunk size in tokens.
        max_chunk_size: Maximum chunk size in tokens.

    Returns:
        End token index (exclusive).
    """
    # If remaining tokens fit within max_chunk_size, take them all
    remaining = total_tokens - start
    if remaining <= max_chunk_size:
        return total_tokens

    # Look for section boundaries between min and max
    earliest_break = start + min_chunk_size
    latest_break = start + max_chunk_size

    # Find the last section boundary in [earliest_break, latest_break)
    # Breaking at a later section boundary means larger chunks (closer to max)
    best_boundary = None
    for sec_idx in section_token_indices:
        if earliest_break <= sec_idx <= latest_break:
            best_boundary = sec_idx

    if best_boundary is not None:
        return best_boundary

    # No section boundary found; break at max_chunk_size
    return start + max_chunk_size
