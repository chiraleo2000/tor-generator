"""Neo4j GraphRAG store for procurement TOR drafting."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

ALLOWED_LABELS = frozenset({"Document", "Law", "Article", "TorSlot", "Concept"})
ALLOWED_RELS = frozenset({"CONTAINED_IN", "CITES", "APPLIES_TO", "DEFINES", "SUPERSEDES"})


class GraphRAGStore:
    """Writes and expands a small legal graph used alongside pgvector."""

    def __init__(self, driver: Any) -> None:
        self._driver = driver

    async def ping(self) -> bool:
        await self._driver.verify_connectivity()
        return True

    async def wipe(self) -> None:
        async with self._driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")

    async def upsert_extraction(
        self,
        *,
        document_id: str,
        document_name: str,
        nodes: list[dict[str, Any]],
        rels: list[dict[str, Any]],
        owner_id: str | None = None,
        scope: str = "baseline",
    ) -> None:
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (d:Document {id: $id})
                SET d.name = $name, d.owner_id = $owner_id, d.scope = $scope
                """,
                id=document_id,
                name=document_name,
                owner_id=owner_id,
                scope=scope,
            )
            for node in nodes:
                label = str(node.get("label") or "Concept")
                if label not in ALLOWED_LABELS:
                    label = "Concept"
                name = str(node.get("name") or "").strip()
                if not name:
                    continue
                node_id = str(node.get("id") or f"{label}:{name}")
                query = (
                    f"MERGE (n:{label} {{id: $id}}) "
                    "SET n.name = $name, n.document_id = $document_id"
                )
                await session.run(
                    query,
                    id=node_id,
                    name=name,
                    document_id=document_id,
                )
                await session.run(
                    """
                    MATCH (d:Document {id: $doc_id}), (n {id: $node_id})
                    MERGE (n)-[:CONTAINED_IN]->(d)
                    """,
                    doc_id=document_id,
                    node_id=node_id,
                )
            for rel in rels:
                rel_type = str(rel.get("type") or "CITES")
                if rel_type not in ALLOWED_RELS:
                    rel_type = "CITES"
                src = str(rel.get("from") or "")
                dst = str(rel.get("to") or "")
                if not src or not dst:
                    continue
                query = (
                    "MATCH (a {id: $src}), (b {id: $dst}) "
                    f"MERGE (a)-[:{rel_type}]->(b)"
                )
                await session.run(query, src=src, dst=dst)

    async def delete_document(self, document_id: str) -> None:
        async with self._driver.session() as session:
            await session.run(
                """
                MATCH (n)
                WHERE n.document_id = $id OR (n:Document AND n.id = $id)
                DETACH DELETE n
                """,
                id=document_id,
            )

    async def expand(
        self,
        *,
        query_text: str,
        slot_key: str | None = None,
        limit: int = 8,
        search_scope: str = "both",
        owner_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return neighbouring graph nodes visible under the RAG ACL."""
        allow_global = search_scope in {"both", "global"}
        owner = owner_id if search_scope != "global" else None
        visibility = (
            "OPTIONAL MATCH (n)-[:CONTAINED_IN]->(d:Document) "
            "WITH n, d "
            "WHERE ($allow_global AND (d IS NULL OR d.owner_id IS NULL)) "
            "OR ($owner_id IS NOT NULL AND d.owner_id = $owner_id) "
        )
        results: list[dict[str, Any]] = []
        try:
            async with self._driver.session() as session:
                if slot_key:
                    cursor = await session.run(
                        """
                        MATCH (s:TorSlot)
                        WHERE s.id = $slot OR s.name CONTAINS $slot
                        OPTIONAL MATCH (n)-[r]-(s)
                        OPTIONAL MATCH (n)-[:CONTAINED_IN]->(d:Document)
                        WITH s, n, r, d
                        WHERE ($allow_global AND (d IS NULL OR d.owner_id IS NULL))
                           OR ($owner_id IS NOT NULL AND d.owner_id = $owner_id)
                        RETURN s.name AS slot, labels(n) AS labels, n.name AS name,
                               type(r) AS rel
                        LIMIT $limit
                        """,
                        slot=slot_key,
                        limit=limit,
                        allow_global=allow_global,
                        owner_id=owner,
                    )
                    results.extend([record.data() async for record in cursor])
                cursor = await session.run(
                    f"""
                    MATCH (n)
                    WHERE n.name CONTAINS $q
                    {visibility}
                    OPTIONAL MATCH (n)-[r]-(m)
                    RETURN labels(n) AS labels, n.name AS name, type(r) AS rel,
                           labels(m) AS other_labels, m.name AS other
                    LIMIT $limit
                    """,
                    q=query_text[:80],
                    limit=limit,
                    allow_global=allow_global,
                    owner_id=owner,
                )
                results.extend([record.data() async for record in cursor])
        except Exception:
            logger.exception("Neo4j expand failed; returning empty graph context")
            return []
        return results


def citations_from_graph(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    citations: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        name = row.get("name") or row.get("slot") or row.get("other")
        labels = row.get("labels") or row.get("other_labels") or []
        if not name:
            continue
        key = str(name)
        if key in seen:
            continue
        seen.add(key)
        kind = "document"
        if "Article" in labels:
            kind = "article"
        elif "TorSlot" in labels:
            kind = "slot"
        elif "Law" in labels:
            kind = "document"
        citations.append({"type": kind, "label": str(name)})
    return citations
