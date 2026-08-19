"""Property 10: KB chat history is bounded to 20 pairs."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.kb_chat_service import MAX_HISTORY, bound_history


@st.composite
def histories(draw):
    n = draw(st.integers(min_value=0, max_value=80))
    items = []
    for index in range(n):
        role = "user" if index % 2 == 0 else "assistant"
        items.append({"role": role, "content": f"m{index}"})
    return items


@pytest.mark.property
@settings(max_examples=40, deadline=None)
@given(histories())
def test_history_at_most_20_pairs(history: list[dict]):
    bounded = bound_history(history)
    assert len(bounded) <= MAX_HISTORY * 2
    if len(history) <= MAX_HISTORY * 2:
        assert bounded == history
