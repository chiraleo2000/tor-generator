"""GraphRAG store helpers with a fake Neo4j driver."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.rag.graph_store import GraphRAGStore, citations_from_graph


class _FakeSession:
    def __init__(self) -> None:
        self.runs: list[tuple] = []

    async def run(self, query, **kwargs):
        self.runs.append((query, kwargs))

        class _Cursor:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise StopAsyncIteration

        return _Cursor()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False


@pytest.mark.asyncio
async def test_ping_and_wipe() -> None:
    driver = MagicMock()
    driver.verify_connectivity = AsyncMock()
    session = _FakeSession()
    driver.session.return_value = session
    store = GraphRAGStore(driver)
    assert await store.ping() is True
    await store.wipe()
    assert session.runs


@pytest.mark.asyncio
async def test_upsert_and_delete() -> None:
    driver = MagicMock()
    session = _FakeSession()
    driver.session.return_value = session
    store = GraphRAGStore(driver)
    await store.upsert_extraction(
        document_id="d1",
        document_name="ก",
        nodes=[{"label": "Law", "name": "พ.ร.บ.", "id": "law-1"}],
        rels=[{"type": "CITES", "from": "a", "to": "b"}],
    )
    await store.delete_document("d1")
    assert any("DETACH DELETE" in query for query, _ in session.runs)


@pytest.mark.asyncio
async def test_expand_mine_without_owner() -> None:
    store = GraphRAGStore(MagicMock())
    assert await store.expand(query_text="q", search_scope="mine") == []


@pytest.mark.asyncio
async def test_expand_fail_open() -> None:
    driver = MagicMock()
    driver.session.side_effect = RuntimeError("down")
    store = GraphRAGStore(driver)
    assert await store.expand(query_text="วงเงิน", search_scope="both") == []


def test_citations_from_graph_dedupes() -> None:
    rows = [
        {"name": "ข้อ 85", "labels": ["Article"]},
        {"name": "ข้อ 85", "labels": ["Article"]},
        {"slot": "s6", "labels": ["TorSlot"]},
        {"other": "กฎหมาย", "other_labels": ["Law"]},
        {},
    ]
    citations = citations_from_graph(rows)
    labels = [item["label"] for item in citations]
    assert labels == ["ข้อ 85", "s6", "กฎหมาย"]
    assert citations[0]["type"] == "article"
    assert citations[1]["type"] == "slot"


class _Record:
    def __init__(self, data: dict) -> None:
        self._data = data

    def data(self) -> dict:
        return self._data


class _Cursor:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = [_Record(row) for row in rows]
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._rows):
            raise StopAsyncIteration
        row = self._rows[self._index]
        self._index += 1
        return row


class _ExpandSession:
    def __init__(self) -> None:
        self.runs: list[tuple] = []

    async def run(self, query, **kwargs):
        self.runs.append((query, kwargs))
        return _Cursor(
            [
                {"name": "ข้อ 29", "labels": ["Article"]},
                {"slot": "s6", "labels": ["TorSlot"]},
            ]
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False


@pytest.mark.asyncio
async def test_expand_with_slot_returns_rows() -> None:
    driver = MagicMock()
    driver.session.return_value = _ExpandSession()
    store = GraphRAGStore(driver)
    rows = await store.expand(
        query_text="วงเงิน",
        slot_key="s6",
        search_scope="both",
        owner_id="u1",
    )
    assert rows
    assert rows[0]["name"] == "ข้อ 29"


@pytest.mark.asyncio
async def test_upsert_skips_blank_and_unknown_labels() -> None:
    driver = MagicMock()
    session = _FakeSession()
    driver.session.return_value = session
    store = GraphRAGStore(driver)
    await store.upsert_extraction(
        document_id="d1",
        document_name="ก",
        nodes=[
            {"label": "UnknownKind", "name": "แนวคิด", "id": "c1"},
            {"label": "Law", "name": "   "},
        ],
        rels=[{"type": "NOPE", "from": "", "to": "b"}, {"type": "CITES", "from": "a", "to": "b"}],
    )
    assert session.runs


@pytest.mark.asyncio
async def test_expand_connect_fail_open_without_driver() -> None:
    store = GraphRAGStore(None)
    assert await store.expand(query_text="วงเงิน", search_scope="both") == []


@pytest.mark.asyncio
async def test_expand_query_only_without_slot() -> None:
    driver = MagicMock()
    driver.session.return_value = _ExpandSession()
    store = GraphRAGStore(driver)
    rows = await store.expand(query_text="วงเงิน", search_scope="global")
    assert rows
    assert rows[0]["name"] == "ข้อ 29"


def test_citations_from_graph_law_type() -> None:
    citations = citations_from_graph([{"name": "พ.ร.บ. 2560", "labels": ["Law"]}])
    assert citations == [{"type": "document", "label": "พ.ร.บ. 2560"}]
