"""Thai formatting utilities for TOR document export.

Provides date conversion (Gregorian → Buddhist Era), numeral conversion
(Arabic ↔ Thai), and section numbering helpers for Thai government documents.
"""

from datetime import date, datetime
from typing import Union

# Thai digit mapping (U+0E50 – U+0E59)
_ARABIC_TO_THAI: dict[str, str] = {
    "0": "๐",
    "1": "๑",
    "2": "๒",
    "3": "๓",
    "4": "๔",
    "5": "๕",
    "6": "๖",
    "7": "๗",
    "8": "๘",
    "9": "๙",
}

_THAI_TO_ARABIC: dict[str, str] = {v: k for k, v in _ARABIC_TO_THAI.items()}

# Thai month names (full)
_THAI_MONTHS: list[str] = [
    "มกราคม",
    "กุมภาพันธ์",
    "มีนาคม",
    "เมษายน",
    "พฤษภาคม",
    "มิถุนายน",
    "กรกฎาคม",
    "สิงหาคม",
    "กันยายน",
    "ตุลาคม",
    "พฤศจิกายน",
    "ธันวาคม",
]

# Buddhist Era offset
_BE_OFFSET: int = 543


def gregorian_to_buddhist_era(year: int) -> int:
    """Convert a Gregorian (CE) year to Thai Buddhist Era (พ.ศ.) year.

    Args:
        year: Gregorian year (e.g. 2024)

    Returns:
        Buddhist Era year (e.g. 2567)
    """
    return year + _BE_OFFSET


def buddhist_era_to_gregorian(year: int) -> int:
    """Convert a Thai Buddhist Era (พ.ศ.) year to Gregorian (CE) year.

    Args:
        year: Buddhist Era year (e.g. 2567)

    Returns:
        Gregorian year (e.g. 2024)
    """
    return year - _BE_OFFSET


def format_thai_date(
    d: Union[date, datetime],
    use_thai_numerals: bool = False,
) -> str:
    """Format a date in Thai government format: วันที่ DD เดือน MMMM พ.ศ. YYYY.

    Args:
        d: A date or datetime object.
        use_thai_numerals: If True, use Thai numeral characters (๑, ๒, ๓, ...).

    Returns:
        Formatted date string, e.g. "วันที่ 15 สิงหาคม พ.ศ. 2567"
        or "วันที่ ๑๕ สิงหาคม พ.ศ. ๒๕๖๗" if use_thai_numerals=True.
    """
    day = d.day
    month_name = _THAI_MONTHS[d.month - 1]
    be_year = gregorian_to_buddhist_era(d.year)

    if use_thai_numerals:
        day_str = to_thai_numerals(str(day))
        year_str = to_thai_numerals(str(be_year))
    else:
        day_str = str(day)
        year_str = str(be_year)

    return f"วันที่ {day_str} {month_name} พ.ศ. {year_str}"


def to_thai_numerals(text: str) -> str:
    """Convert all Arabic digits in a string to Thai numerals.

    Args:
        text: Input string potentially containing Arabic digits.

    Returns:
        String with all Arabic digits replaced by Thai numeral equivalents.
    """
    return "".join(_ARABIC_TO_THAI.get(ch, ch) for ch in text)


def to_arabic_numerals(text: str) -> str:
    """Convert all Thai numerals in a string to Arabic digits.

    Args:
        text: Input string potentially containing Thai numerals.

    Returns:
        String with all Thai numerals replaced by Arabic digit equivalents.
    """
    return "".join(_THAI_TO_ARABIC.get(ch, ch) for ch in text)


def format_section_number(
    number: Union[int, str],
    use_thai_numerals: bool = False,
) -> str:
    """Format a section number with optional Thai numeral conversion.

    Supports hierarchical section numbers like "4.1" or single numbers like "1".

    Args:
        number: Section number (int or string like "4.1").
        use_thai_numerals: If True, convert digits to Thai numerals.

    Returns:
        Formatted section number string.
    """
    text = str(number)
    if use_thai_numerals:
        return to_thai_numerals(text)
    return text


def format_currency_thai(amount: int, use_thai_numerals: bool = False) -> str:
    """Format a budget/currency value in Thai style with comma separators.

    Args:
        amount: Integer amount in baht.
        use_thai_numerals: If True, use Thai numeral characters.

    Returns:
        Formatted currency string, e.g. "1,000,000 บาท" or "๑,๐๐๐,๐๐๐ บาท".
    """
    formatted = f"{amount:,}"
    if use_thai_numerals:
        formatted = to_thai_numerals(formatted)
    return f"{formatted} บาท"
