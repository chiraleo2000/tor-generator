"""MongoDB GridFS originals for baseline and per-user documents."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.config import get_settings

logger = logging.getLogger(__name__)

COLLECTION = "source_documents"
BUCKET = "originals"


class OriginalDocumentStore:
    """Sync GridFS helper wrapping a pymongo MongoClient."""

    def __init__(self, client: Any, database: str | None = None) -> None:
        settings = get_settings()
        self._client = client
        self._db = client[database or settings.mongo_db]
        self._meta = self._db[COLLECTION]
        try:
            import gridfs

            self._fs = gridfs.GridFS(self._db, collection=BUCKET)
        except Exception as exc:  # pragma: no cover - import failure
            raise RuntimeError("pymongo/gridfs is required") from exc

    def ping(self) -> bool:
        self._client.admin.command("ping")
        return True

    def put_file(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str,
        scope: str,
        owner_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        digest = hashlib.sha256(content).hexdigest()
        existing = self._meta.find_one({"sha256": digest, "scope": scope, "owner_id": owner_id})
        if existing:
            return existing
        grid_id = self._fs.put(
            content,
            filename=filename,
            content_type=content_type,
            sha256=digest,
        )
        doc = {
            "_id": str(uuid4()),
            "filename": filename,
            "content_type": content_type,
            "scope": scope,
            "owner_id": owner_id,
            "project_id": project_id,
            "gridfs_id": str(grid_id),
            "sha256": digest,
            "bytes": len(content),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "status": "stored",
        }
        self._meta.insert_one(doc)
        return doc

    def get_bytes(self, gridfs_id: str) -> bytes:
        from bson import ObjectId

        grid_file = self._fs.get(ObjectId(gridfs_id))
        return grid_file.read()

    def list_meta(self, *, scope: str | None = None, owner_id: str | None = None) -> list[dict]:
        query: dict[str, Any] = {}
        if scope:
            query["scope"] = scope
        if owner_id is not None:
            query["owner_id"] = owner_id
        return list(self._meta.find(query))

    def wipe_baseline(self) -> int:
        docs = list(self._meta.find({"scope": "baseline"}))
        removed = 0
        from bson import ObjectId

        for doc in docs:
            grid_id = doc.get("gridfs_id")
            if grid_id:
                try:
                    self._fs.delete(ObjectId(grid_id))
                except Exception:
                    logger.warning("GridFS delete missed %s", grid_id)
            self._meta.delete_one({"_id": doc["_id"]})
            removed += 1
        return removed


def store_from_client(client: Any | None) -> OriginalDocumentStore | None:
    if client is None:
        return None
    return OriginalDocumentStore(client)
