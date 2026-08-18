"""Property-based tests for Thai Date Format Consistency (Property 14).

Verifies that for any date value, exported dates are always displayed in
Thai Buddhist Era (พ.ศ.) format — the difference between the displayed year
and the Gregorian year is always exactly 543.

**Validates: Requirements 8.3, 4.7**

# Feature: tor-drafting-review-app, Property 14: Thai Date Format Consistency
"""

import re
from datetime import date

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.export.thai_formatting import (
    format_thai_date,
    gregorian_to_buddhist_era,
    to_arabic_numerals,
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Date strategy: cover a wide range of valid dates (years 1–9999)
date_strategy = st.dates(
    min_value=date(1, 1, 1),
    max_value=date(9999, 12, 31),
)

# Year strategy for testing gregorian_to_buddhist_era directly
year_strategy = st.integers(min_value=1, max_value=9999)


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------


@pytest.mark.property
class TestThaiDateFormatConsistency:
    """Property 14: Thai Date Format Consistency.

    For any date value in the system, exported documents SHALL display that
    date in Thai Buddhist Era (พ.ศ.) format — the difference between the
    displayed year and the Gregorian year SHALL always be exactly 543.
    """

    @given(year=year_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 14: Thai Date Format Consistency
    def test_gregorian_to_buddhist_era_adds_543(self, year: int):
        """For any Gregorian year, Buddhist Era year = Gregorian + 543.

        **Validates: Requirements 8.3, 4.7**
        """
        be_year = gregorian_to_buddhist_era(year)
        assert be_year == year + 543

    @given(d=date_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 14: Thai Date Format Consistency
    def test_format_thai_date_year_is_gregorian_plus_543(self, d: date):
        """For any date, format_thai_date produces a year that is exactly
        the Gregorian year + 543 (Buddhist Era offset).

        **Validates: Requirements 8.3, 4.7**
        """
        result = format_thai_date(d, use_thai_numerals=False)

        # Extract the year from "พ.ศ. YYYY" portion
        match = re.search(r"พ\.ศ\.\s+(\d+)", result)
        assert match is not None, f"Expected พ.ศ. followed by year in: {result}"

        displayed_year = int(match.group(1))
        assert displayed_year == d.year + 543

    @given(d=date_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 14: Thai Date Format Consistency
    def test_format_thai_date_thai_numerals_year_is_gregorian_plus_543(self, d: date):
        """For any date with Thai numerals, the converted year still equals
        Gregorian year + 543.

        **Validates: Requirements 8.3, 4.7**
        """
        result = format_thai_date(d, use_thai_numerals=True)

        # Convert Thai numerals back to Arabic to extract the year
        result_arabic = to_arabic_numerals(result)

        match = re.search(r"พ\.ศ\.\s+(\d+)", result_arabic)
        assert match is not None, f"Expected พ.ศ. followed by year in: {result_arabic}"

        displayed_year = int(match.group(1))
        assert displayed_year == d.year + 543

    @given(d=date_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 14: Thai Date Format Consistency
    def test_format_thai_date_contains_buddhist_era_marker(self, d: date):
        """For any date, the formatted output always contains the พ.ศ. marker,
        confirming the date is in Buddhist Era format.

        **Validates: Requirements 8.3, 4.7**
        """
        result = format_thai_date(d, use_thai_numerals=False)
        assert "พ.ศ." in result

    @given(year=year_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 14: Thai Date Format Consistency
    def test_buddhist_era_offset_is_exactly_543(self, year: int):
        """For any year, the difference between Buddhist Era and Gregorian
        year is always exactly 543 — never more, never less.

        **Validates: Requirements 8.3, 4.7**
        """
        be_year = gregorian_to_buddhist_era(year)
        assert be_year - year == 543
