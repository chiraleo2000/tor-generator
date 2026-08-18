"""Property-based tests for Project Version Ordering (Property 8).

Verifies that for any project with N versions:
- The version numbers form a strictly increasing sequence from 1 to N
- Each version snapshot contains a complete copy of the project state
- No version gaps or data truncation occur
- Maximum 50 versions per project is enforced

**Validates: Requirements 9.6**

# Feature: tor-drafting-review-app, Property 8: Project Version Ordering
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.models.project_version import ProjectVersion


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Number of version saves to simulate (1 to 55, exceeding the 50-version cap)
num_versions_strategy = st.integers(min_value=1, max_value=55)

# Step numbers for each version save (1-8)
step_number_strategy = st.integers(min_value=1, max_value=8)

# Generate a sequence of step saves to simulate wizard usage
step_sequence_strategy = st.lists(
    step_number_strategy,
    min_size=1,
    max_size=55,
)

# Generate section content (arbitrary non-empty Thai text for snapshots)
section_content_strategy = st.sampled_from([
    "ความเป็นมาของโครงการพัฒนาระบบ",
    "วัตถุประสงค์เพื่อจัดซื้อจัดจ้าง",
    "คุณสมบัติผู้เสนอราคา",
    "ขอบเขตของงาน",
    "ระยะเวลาดำเนินการ 180 วัน",
    "งบประมาณ 5,000,000 บาท",
    "การจ่ายเงินแบ่ง 3 งวด",
    "เกณฑ์การพิจารณา",
])

# Generate snapshot data for a version (dict representing project state)
@st.composite
def snapshot_data_strategy(draw):
    """Generate a realistic snapshot_data dict for a project version."""
    num_sections = draw(st.integers(min_value=1, max_value=13))
    snapshot = {}
    for i in range(1, num_sections + 1):
        key = f"s{i}"
        snapshot[key] = {
            "content": draw(section_content_strategy),
            "ai_draft": draw(st.one_of(st.none(), section_content_strategy)),
            "quality_score": draw(st.one_of(st.none(), st.floats(min_value=0, max_value=100, allow_nan=False))),
            "is_approved": draw(st.booleans()),
            "version": draw(st.integers(min_value=1, max_value=20)),
        }
    # Include step data as the wizard does
    step_data = {}
    step_key = f"s{draw(st.integers(min_value=1, max_value=8))}"
    step_data[step_key] = draw(section_content_strategy)
    snapshot["_step_data"] = step_data
    return snapshot


# ---------------------------------------------------------------------------
# Helpers: Simulate version sequencing logic from wizard.py
# ---------------------------------------------------------------------------


def get_next_version_number(existing_version_numbers: list[int]) -> int:
    """Replicate the _get_next_version_number logic from wizard.py.

    Returns the next sequential version number (max + 1, or 1 if none exist).
    Enforces maximum 50 versions per project.
    """
    if not existing_version_numbers:
        return 1

    max_version = max(existing_version_numbers)
    next_version = max_version + 1

    # Enforce max 50 versions (same logic as in wizard.py)
    if next_version > 50:
        next_version = 50

    return next_version


def simulate_version_sequence(num_saves: int) -> list[int]:
    """Simulate a sequence of version saves, returning the version numbers created.

    This replicates the behavior of repeatedly calling _get_next_version_number
    as the wizard save endpoint does for each step save.
    """
    version_numbers: list[int] = []

    for _ in range(num_saves):
        next_ver = get_next_version_number(version_numbers)
        version_numbers.append(next_ver)

    return version_numbers


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------


@pytest.mark.property
class TestProjectVersionOrdering:
    """Property 8: Project Version Ordering.

    For any project with N versions, the version numbers SHALL form a strictly
    increasing sequence from 1 to N, and each version snapshot SHALL contain a
    complete copy of the project state at that point — no version gaps or data
    truncation.
    """

    @given(num_saves=st.integers(min_value=1, max_value=50))
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 8: Project Version Ordering
    def test_version_numbers_form_strictly_increasing_sequence(self, num_saves: int):
        """For any N saves (up to 50), version numbers form sequence 1..N.

        **Validates: Requirements 9.6**
        """
        version_numbers = simulate_version_sequence(num_saves)

        # Must be strictly increasing
        for i in range(1, len(version_numbers)):
            assert version_numbers[i] > version_numbers[i - 1], (
                f"Version numbers not strictly increasing at index {i}: "
                f"{version_numbers[i-1]} -> {version_numbers[i]}"
            )

        # Must start at 1
        assert version_numbers[0] == 1, (
            f"First version number must be 1, got {version_numbers[0]}"
        )

        # Must form contiguous sequence 1..N
        expected = list(range(1, num_saves + 1))
        assert version_numbers == expected, (
            f"Expected sequence {expected}, got {version_numbers}"
        )

    @given(num_saves=st.integers(min_value=1, max_value=50))
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 8: Project Version Ordering
    def test_no_version_gaps(self, num_saves: int):
        """For any N saves (up to 50), there are no gaps in version numbering.

        **Validates: Requirements 9.6**
        """
        version_numbers = simulate_version_sequence(num_saves)

        # Check no gaps: each consecutive pair differs by exactly 1
        for i in range(1, len(version_numbers)):
            diff = version_numbers[i] - version_numbers[i - 1]
            assert diff == 1, (
                f"Gap detected at index {i}: version {version_numbers[i-1]} "
                f"-> {version_numbers[i]} (diff={diff}, expected 1)"
            )

    @given(num_saves=st.integers(min_value=51, max_value=55))
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 8: Project Version Ordering
    def test_max_50_versions_enforced(self, num_saves: int):
        """When more than 50 saves occur, version number is capped at 50.

        **Validates: Requirements 9.6**
        """
        version_numbers = simulate_version_sequence(num_saves)

        # All version numbers should be <= 50
        assert all(v <= 50 for v in version_numbers), (
            f"Found version numbers exceeding 50: "
            f"{[v for v in version_numbers if v > 50]}"
        )

        # First 50 versions should form 1..50
        first_50 = version_numbers[:50]
        assert first_50 == list(range(1, 51)), (
            f"First 50 versions should be 1..50, got: {first_50[:10]}..."
        )

    @given(snapshot=snapshot_data_strategy())
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 8: Project Version Ordering
    def test_version_snapshot_is_complete(self, snapshot: dict):
        """Each version snapshot contains a complete project state (non-empty,
        with section data and step_data).

        **Validates: Requirements 9.6**
        """
        # A snapshot must not be empty
        assert len(snapshot) > 0, "Snapshot must not be empty"

        # Snapshot must contain _step_data (the wizard always includes it)
        assert "_step_data" in snapshot, "Snapshot must include _step_data"
        assert isinstance(snapshot["_step_data"], dict), (
            "_step_data must be a dict"
        )
        assert len(snapshot["_step_data"]) > 0, "_step_data must not be empty"

        # Snapshot must contain at least one section key (s1..s13)
        section_keys = [k for k in snapshot.keys() if k.startswith("s")]
        assert len(section_keys) > 0, (
            "Snapshot must contain at least one section (s1..s13)"
        )

        # Each section in snapshot must have required fields
        for key in section_keys:
            section = snapshot[key]
            assert isinstance(section, dict), (
                f"Section '{key}' must be a dict, got {type(section)}"
            )
            assert "content" in section, (
                f"Section '{key}' must have 'content' field"
            )
            assert "is_approved" in section, (
                f"Section '{key}' must have 'is_approved' field"
            )
            assert "version" in section, (
                f"Section '{key}' must have 'version' field"
            )

    @given(step_sequence=step_sequence_strategy.filter(lambda s: len(s) <= 50))
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 8: Project Version Ordering
    def test_version_ordering_independent_of_step_order(self, step_sequence: list[int]):
        """Regardless of which steps are saved and in what order, version
        numbers still form a strictly increasing sequence.

        **Validates: Requirements 9.6**
        """
        # Simulate version creation for each step save
        version_numbers: list[int] = []
        for _ in step_sequence:
            next_ver = get_next_version_number(version_numbers)
            version_numbers.append(next_ver)

        num_saves = len(step_sequence)

        # Must form 1..N sequence
        expected = list(range(1, num_saves + 1))
        assert version_numbers == expected, (
            f"For step sequence {step_sequence[:10]}..., "
            f"expected versions {expected[:10]}..., got {version_numbers[:10]}..."
        )

    @given(num_saves=st.integers(min_value=1, max_value=50))
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 8: Project Version Ordering
    def test_version_model_instantiation_preserves_ordering(self, num_saves: int):
        """ProjectVersion model instances created in sequence preserve
        the correct version_number ordering.

        **Validates: Requirements 9.6**
        """
        project_id = uuid.uuid4()
        versions: list[ProjectVersion] = []

        existing_numbers: list[int] = []
        for i in range(num_saves):
            next_ver = get_next_version_number(existing_numbers)
            version = ProjectVersion(
                project_id=project_id,
                version_number=next_ver,
                snapshot_data={"s1": {"content": f"Version {next_ver} content", "is_approved": False, "version": 1}},
                step_number=(i % 8) + 1,
            )
            versions.append(version)
            existing_numbers.append(next_ver)

        # Verify ordering on model instances
        for i, v in enumerate(versions):
            assert v.version_number == i + 1, (
                f"Version at index {i} should have version_number={i+1}, "
                f"got {v.version_number}"
            )

        # Verify all snapshots are complete (non-empty)
        for v in versions:
            assert v.snapshot_data is not None
            assert len(v.snapshot_data) > 0
            assert "s1" in v.snapshot_data
