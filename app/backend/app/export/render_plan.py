"""Render plan types for TOR export (Req 3, 4, 6, 8)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NumberingScheme(str, Enum):
    NUMBERED_CONSECUTIVE = "numbered_consecutive"
    NONE = "none"


def coerce_numbering_scheme(value: object) -> NumberingScheme:
    """Invalid values fall back to consecutive numbering (Req 3.6)."""
    if isinstance(value, NumberingScheme):
        return value
    try:
        return NumberingScheme(str(value).strip())
    except ValueError:
        return NumberingScheme.NUMBERED_CONSECUTIVE


@dataclass(frozen=True)
class RenderSubsection:
    number: str
    label: str
    content: str


@dataclass(frozen=True)
class RenderSection:
    semantic_key: str
    storage_key: str
    number: str
    label: str
    content: str
    subsections: tuple[RenderSubsection, ...]


@dataclass(frozen=True)
class AppendixItem:
    title: str
    content: str


@dataclass(frozen=True)
class RenderAppendix:
    number: str
    title: str
    content: str


@dataclass(frozen=True)
class ArchiveRecord:
    legacy_key: str
    sub_key: str | None
    content: str


@dataclass(frozen=True)
class RenderPlan:
    body: tuple[RenderSection, ...]
    appendices: tuple[RenderAppendix, ...]
    archived: tuple[ArchiveRecord, ...]
