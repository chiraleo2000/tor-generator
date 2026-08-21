"""ACL, Mongo isolation, graph owner tags, and local LLM routing."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.rag.acl import document_is_visible
from app.rag.graph_store import GraphRAGStore
from app.storage.mongo_store import OriginalDocumentStore
from tests.test_provider_factory import make_settings

USER_A = uuid4()
USER_B = uuid4()


def test_document_is_visible_global_and_owner_only():
    assert document_is_visible(document_owner_id=None, viewer_id=USER_A) is True
    assert document_is_visible(document_owner_id=USER_A, viewer_id=USER_A) is True
    assert document_is_visible(document_owner_id=USER_A, viewer_id=USER_B) is False
    assert document_is_visible(
        document_owner_id=USER_A, viewer_id=USER_B, search_scope="both"
    ) is False
    assert document_is_visible(
        document_owner_id=None, viewer_id=USER_A, search_scope="global"
    ) is True
    assert document_is_visible(
        document_owner_id=USER_A, viewer_id=USER_A, search_scope="global"
    ) is False
    assert document_is_visible(
        document_owner_id=USER_A, viewer_id=USER_A, search_scope="mine"
    ) is True
    assert document_is_visible(
        document_owner_id=None, viewer_id=USER_A, search_scope="mine"
    ) is False


def test_hybrid_post_filter_drops_other_owner_hits():
    from app.providers.base import SearchResult
    from app.rag.hybrid import _chunk_from_hit

    foreign = SearchResult(
        id="1",
        text="ของคนอื่น",
        score=0.9,
        metadata={"owner_id": str(USER_B), "source_document": "secret.pdf"},
    )
    mine = SearchResult(
        id="2",
        text="ของฉัน",
        score=0.8,
        metadata={"owner_id": str(USER_A), "source_document": "mine.pdf"},
    )
    shared = SearchResult(
        id="3",
        text="กฎหมายกลาง",
        score=0.7,
        metadata={"owner_id": None, "source_document": "law.pdf"},
    )
    assert _chunk_from_hit(foreign, user_id=USER_A, search_scope="both") is None
    assert _chunk_from_hit(mine, user_id=USER_A, search_scope="mine") is not None
    assert _chunk_from_hit(shared, user_id=USER_A, search_scope="mine") is None
    assert _chunk_from_hit(shared, user_id=USER_A, search_scope="both") is not None


def test_mine_scope_returns_only_user_docs():
    assert document_is_visible(
        document_owner_id=USER_A, viewer_id=USER_A, search_scope="mine"
    ) is True
    assert document_is_visible(
        document_owner_id=None, viewer_id=USER_A, search_scope="mine"
    ) is False


def test_mine_scope_excludes_other_users():
    assert document_is_visible(
        document_owner_id=USER_A, viewer_id=USER_B, search_scope="mine"
    ) is False


def test_both_scope_includes_baseline_and_user():
    assert document_is_visible(
        document_owner_id=None, viewer_id=USER_A, search_scope="both"
    ) is True
    assert document_is_visible(
        document_owner_id=USER_A, viewer_id=USER_A, search_scope="both"
    ) is True
    assert document_is_visible(
        document_owner_id=USER_B, viewer_id=USER_A, search_scope="both"
    ) is False


def test_global_scope_excludes_user_docs():
    assert document_is_visible(
        document_owner_id=None, viewer_id=USER_A, search_scope="global"
    ) is True
    assert document_is_visible(
        document_owner_id=USER_A, viewer_id=USER_A, search_scope="global"
    ) is False


def test_officer_a_sees_own_private_file_officer_b_does_not():
    assert document_is_visible(
        document_owner_id=USER_A, viewer_id=USER_A, search_scope="mine"
    ) is True
    assert document_is_visible(
        document_owner_id=USER_A, viewer_id=USER_A, search_scope="both"
    ) is True
    assert document_is_visible(
        document_owner_id=USER_A, viewer_id=USER_B, search_scope="mine"
    ) is False
    assert document_is_visible(
        document_owner_id=USER_A, viewer_id=USER_B, search_scope="both"
    ) is False


@pytest.mark.asyncio
async def test_graph_expand_mine_without_owner_is_empty():
    driver = _FakeDriver()
    store = GraphRAGStore(driver)
    rows = await store.expand(query_text="งวดจ่าย", search_scope="mine", owner_id=None)
    assert rows == []
    assert driver.session_obj.calls == []


class _FakeCursor:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def __aiter__(self):
        async def _gen():
            for row in self._rows:
                yield _FakeRecord(row)

        return _gen()


class _FakeRecord:
    def __init__(self, data: dict):
        self._data = data

    def data(self) -> dict:
        return self._data


class _FakeSession:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def run(self, query: str, **kwargs):
        self.calls.append((query, kwargs))
        return _FakeCursor([])

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


class _FakeDriver:
    def __init__(self):
        self.session_obj = _FakeSession()

    def session(self):
        return self.session_obj


@pytest.mark.asyncio
async def test_graph_upsert_stores_owner_id():
    driver = _FakeDriver()
    store = GraphRAGStore(driver)
    await store.upsert_extraction(
        document_id="doc-1",
        document_name="mine.pdf",
        nodes=[],
        rels=[],
        owner_id=str(USER_A),
        scope="user",
    )
    _query, params = driver.session_obj.calls[0]
    assert params["owner_id"] == str(USER_A)
    assert params["scope"] == "user"


@pytest.mark.asyncio
async def test_graph_expand_passes_owner_filter():
    driver = _FakeDriver()
    store = GraphRAGStore(driver)
    await store.expand(
        query_text="งวดจ่าย",
        search_scope="mine",
        owner_id=str(USER_A),
    )
    _query, params = driver.session_obj.calls[-1]
    assert params["allow_global"] is False
    assert params["owner_id"] == str(USER_A)


@pytest.mark.asyncio
async def test_graph_expand_global_drops_owner():
    driver = _FakeDriver()
    store = GraphRAGStore(driver)
    await store.expand(query_text="พัสดุ", search_scope="global", owner_id=str(USER_A))
    _query, params = driver.session_obj.calls[-1]
    assert params["allow_global"] is True
    assert params["owner_id"] is None


def test_mongo_list_visible_excludes_other_owners():
    rows = [
        {"_id": "1", "owner_id": None, "filename": "law.pdf"},
        {"_id": "2", "owner_id": str(USER_A), "filename": "mine.pdf"},
        {"_id": "3", "owner_id": str(USER_B), "filename": "secret.pdf"},
    ]

    class _Coll:
        def find(self, query):
            if "owner_id" not in query:
                return list(rows)
            owner = query.get("owner_id")
            return [row for row in rows if row.get("owner_id") == owner]

    store = OriginalDocumentStore.__new__(OriginalDocumentStore)
    store._meta = _Coll()
    visible = store.list_visible(owner_id=str(USER_A))
    names = {row["filename"] for row in visible}
    assert "law.pdf" in names
    assert "mine.pdf" in names
    assert "secret.pdf" not in names


def test_local_llm_and_embedding_hosts_are_independent():
    from app.providers.factory import ProviderFactory
    from app.providers.llm.lm_studio_provider import LMStudioLocalProvider

    cases = (
        ("lm_studio", "1234"),
        ("ollama", "11434"),
        ("llama_cpp", "8080"),
    )
    for provider, port in cases:
        settings = make_settings(deployment_mode="on_prem", llm_provider=provider)
        llm = ProviderFactory(settings=settings).get_llm()
        embedding = ProviderFactory(settings=settings).get_embedding()
        assert isinstance(llm, LMStudioLocalProvider)
        assert port in llm._base_url
        assert "1234" in embedding._base_url
