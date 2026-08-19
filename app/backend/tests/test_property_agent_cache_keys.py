"""Property 6: cache key determinism."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.session_cache import (
    clamp_ttl_seconds,
    content_hash,
    draft_key,
    extraction_key,
    slotmap_key,
)


@pytest.mark.property
@settings(max_examples=40, deadline=None)
@given(st.binary(min_size=0, max_size=4096))
def test_content_hash_is_deterministic(data: bytes):
    copy = bytes(data)
    assert content_hash(data) == content_hash(copy)


@pytest.mark.property
@settings(max_examples=40, deadline=None)
@given(st.binary(min_size=1, max_size=2048), st.text(min_size=1, max_size=40))
def test_hash_ignores_filename(data: bytes, _name: str):
    assert content_hash(data) == content_hash(bytes(data))


@pytest.mark.property
@settings(max_examples=20, deadline=None)
@given(st.uuids(), st.text(min_size=8, max_size=64, alphabet="0123456789abcdef"))
def test_extraction_key_format(project_id, digest: str):
    key = extraction_key(project_id, digest)
    assert key.startswith("agent:extract:")
    assert digest in key
    assert str(project_id) in key


@pytest.mark.property
@settings(max_examples=20, deadline=None)
@given(st.uuids())
def test_slotmap_key_format(project_id):
    assert slotmap_key(project_id) == f"agent:slotmap:{project_id}"


@pytest.mark.property
@settings(max_examples=20, deadline=None)
@given(st.uuids(), st.sampled_from(["s1", "s4.1", "s13"]))
def test_draft_key_format(project_id, section_key: str):
    assert draft_key(project_id, section_key) == f"agent:draft:{project_id}:{section_key}"


@pytest.mark.property
@settings(max_examples=30, deadline=None)
@given(st.integers())
def test_ttl_clamped_1_to_168_hours(hours: int):
    seconds = clamp_ttl_seconds(hours)
    assert 3600 <= seconds <= 168 * 3600
