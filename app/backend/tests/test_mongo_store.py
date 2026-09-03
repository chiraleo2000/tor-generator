"""OriginalDocumentStore unit tests with a fake GridFS client."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.storage.mongo_store import OriginalDocumentStore, store_from_client


def _store() -> tuple[OriginalDocumentStore, MagicMock, MagicMock]:
    client = MagicMock()
    db = MagicMock()
    meta = MagicMock()
    fs = MagicMock()
    client.__getitem__.return_value = db
    db.__getitem__.return_value = meta
    with patch("gridfs.GridFS", return_value=fs):
        store = OriginalDocumentStore(client, database="tor_docs")
    store._fs = fs
    store._meta = meta
    return store, meta, fs


def test_store_from_client_none() -> None:
    assert store_from_client(None) is None


def test_put_file_returns_existing() -> None:
    store, meta, _fs = _store()
    meta.find_one.return_value = {"_id": "old"}
    doc = store.put_file(
        filename="a.pdf", content=b"x", content_type="application/pdf", scope="user"
    )
    assert doc["_id"] == "old"
    _fs.put.assert_not_called()


def test_put_file_inserts() -> None:
    store, meta, fs = _store()
    meta.find_one.return_value = None
    fs.put.return_value = "gid"
    doc = store.put_file(
        filename="a.pdf", content=b"hello", content_type="application/pdf", scope="baseline"
    )
    assert doc["bytes"] == 5
    meta.insert_one.assert_called_once()


def test_list_and_delete() -> None:
    store, meta, fs = _store()
    meta.find.return_value = [{"_id": 1}]
    assert store.list_meta(scope="baseline") == [{"_id": 1}]
    meta.find.side_effect = [[{"_id": "s"}], [{"_id": "m"}]]
    visible = store.list_visible(owner_id="u1")
    assert len(visible) == 2
    store.delete_file(None)
    fs.delete.assert_not_called()
    with patch("bson.ObjectId", return_value="oid"):
        store.delete_file("abc")
    fs.delete.assert_called()
    meta.delete_one.assert_called()


def test_wipe_baseline() -> None:
    store, meta, fs = _store()
    meta.find.return_value = [{"_id": "d1", "gridfs_id": "g1"}]
    with patch("bson.ObjectId", return_value="oid"):
        removed = store.wipe_baseline()
    assert removed == 1
    fs.delete.assert_called()


def test_ping() -> None:
    store, _meta, _fs = _store()
    store._client.admin.command.return_value = {"ok": 1}
    assert store.ping() is True


def test_get_bytes() -> None:
    store, _meta, fs = _store()
    fs.get.return_value = SimpleNamespace(read=lambda: b"data")
    with patch("bson.ObjectId", return_value="oid"):
        assert store.get_bytes("abc") == b"data"


def test_delete_and_wipe_tolerate_gridfs_errors() -> None:
    store, meta, fs = _store()
    fs.delete.side_effect = RuntimeError("missing")
    with patch("bson.ObjectId", return_value="oid"):
        store.delete_file("abc")
    meta.delete_one.assert_called()
    meta.find.return_value = [{"_id": "d1", "gridfs_id": "g1"}]
    with patch("bson.ObjectId", return_value="oid"):
        assert store.wipe_baseline() == 1


def test_list_meta_filters_owner() -> None:
    store, meta, _fs = _store()
    meta.find.return_value = []
    store.list_meta(owner_id="u1")
    meta.find.assert_called_with({"owner_id": "u1"})


def test_store_from_client_wraps_client() -> None:
    client = MagicMock()
    with patch("gridfs.GridFS"):
        store = store_from_client(client)
    assert isinstance(store, OriginalDocumentStore)


def test_store_requires_gridfs() -> None:
    client = MagicMock()
    with patch("gridfs.GridFS", side_effect=OSError("no gridfs")):
        with pytest.raises(RuntimeError, match="gridfs"):
            OriginalDocumentStore(client)


def test_wipe_baseline_skips_missing_grid_id() -> None:
    store, meta, fs = _store()
    meta.find.return_value = [{"_id": "d1"}]
    assert store.wipe_baseline() == 1
    fs.delete.assert_not_called()
    meta.delete_one.assert_called_with({"_id": "d1"})


def test_list_meta_scope_and_owner() -> None:
    store, meta, _fs = _store()
    meta.find.return_value = []
    store.list_meta(scope="user", owner_id="u1")
    meta.find.assert_called_with({"scope": "user", "owner_id": "u1"})
    store.list_meta()
    meta.find.assert_called_with({})
