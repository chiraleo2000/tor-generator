"""
Document relation graph extraction.

The graph engine is Hyper-Extract. The app normalizes Hyper-Extract output
into a stable UI schema and persists it as graph.json.
"""

import time
from typing import Any


def _record_text(kb: dict, max_chars: int = 12000) -> str:
    parts = []
    meta = kb.get("meta", {})
    if meta.get("doc_title"):
        parts.append(f"Document: {meta['doc_title']}")

    for rec in kb.get("records", [])[:45]:
        block = "\n".join(
            filter(
                None,
                [
                    f"[{rec.get('section_id', '')}] {rec.get('title', '')}",
                    (rec.get("summary", "") or "")[:350],
                    (rec.get("details", "") or "")[:450],
                    "Keywords: " + ", ".join(rec.get("keywords") or []),
                ],
            )
        )
        parts.append(block)
        if sum(len(p) for p in parts) >= max_chars:
            break
    return "\n\n---\n\n".join(parts)[:max_chars]


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if value:
        return [value]
    return []


def _to_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(warnings=False)
        except TypeError:
            return value.model_dump()
    return dict(value)


def _graph_payload_from(value: Any) -> dict | None:
    candidates = [value]
    for attr in ("parsed", "data"):
        nested = getattr(value, attr, None)
        if nested is not None:
            candidates.append(nested)
            parsed = getattr(nested, "parsed", None)
            if parsed is not None:
                candidates.append(parsed)

    for candidate in candidates:
        if hasattr(candidate, "nodes") and hasattr(candidate, "edges"):
            return {
                "entities": [_to_dict(n) for n in candidate.nodes],
                "relations": [_to_dict(e) for e in candidate.edges],
            }
        if isinstance(candidate, dict) and (
            candidate.get("nodes")
            or candidate.get("edges")
            or candidate.get("entities")
            or candidate.get("relations")
        ):
            return candidate
    return None


def _normalize_graph(raw: dict, source: str, doc_id: str) -> dict:
    raw_nodes = _as_list(raw.get("nodes") or raw.get("entities"))
    raw_edges = _as_list(raw.get("edges") or raw.get("relations"))

    nodes = []
    seen = set()
    for item in raw_nodes:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("id") or item.get("label") or "").strip()
        if not name:
            continue
        node_id = name
        if node_id in seen:
            continue
        seen.add(node_id)
        node_type = str(item.get("type") or item.get("category") or "Entity").strip() or "Entity"
        group = str(item.get("group") or node_type).strip() or "Entity"
        nodes.append(
            {
                "id": node_id,
                "name": name,
                "type": node_type,
                "group": group,
                "description": str(item.get("description") or item.get("summary") or "").strip(),
                "size": int(item.get("size") or 1),
            }
        )

    node_ids = {n["id"] for n in nodes}
    edges = []
    edge_seen = set()
    for item in raw_edges:
        if not isinstance(item, dict):
            continue
        src = str(item.get("source") or item.get("from") or "").strip()
        tgt = str(item.get("target") or item.get("to") or "").strip()
        label = str(item.get("type") or item.get("label") or item.get("relation") or "related_to").strip()
        if not src or not tgt or src == tgt:
            continue
        for node_id in (src, tgt):
            if node_id not in node_ids:
                node_ids.add(node_id)
                nodes.append(
                    {
                        "id": node_id,
                        "name": node_id,
                        "type": "Entity",
                        "group": "Entity",
                        "description": "",
                        "size": 1,
                    }
                )
        edge_id = f"{src}|{label}|{tgt}"
        if edge_id in edge_seen:
            continue
        edge_seen.add(edge_id)
        edges.append(
            {
                "id": edge_id,
                "source": src,
                "target": tgt,
                "label": label,
                "type": label,
                "description": str(item.get("description") or "").strip(),
                "weight": float(item.get("weight") or 1),
            }
        )

    groups = {}
    for node in nodes:
        groups.setdefault(node["group"], 0)
        groups[node["group"]] += 1

    return {
        "doc_id": doc_id,
        "generated_at": time.time(),
        "engine": source,
        "nodes": nodes,
        "edges": edges,
        "groups": [{"id": k, "label": k, "count": v} for k, v in sorted(groups.items())],
    }


def _run_hyperextract(text: str, cfg: dict) -> dict:
    from hyperextract import Template
    from langchain_core.embeddings import Embeddings
    from langchain_openai import AzureChatOpenAI

    class ZeroEmbeddings(Embeddings):
        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return [[0.0] * 8 for _ in texts]

        def embed_query(self, text: str) -> list[float]:
            return [0.0] * 8

    llm = AzureChatOpenAI(
        azure_endpoint=cfg.get("endpoint", "").rstrip("/"),
        azure_deployment=cfg.get("model", "gpt-4o-mini"),
        openai_api_version=cfg.get("api_version", "2024-08-01-preview"),
        api_key=cfg.get("api_key", ""),
        temperature=0,
    )

    template = Template.create(
        "general/graph",
        language="en",
        llm_client=llm,
        embedder=ZeroEmbeddings(),
        extraction_mode="one_stage",
        max_workers=2,
        chunk_size=12000,
        chunk_overlap=0,
    )

    result = template.parse(text)
    payload = _graph_payload_from(result)
    if payload is not None:
        return payload
    raise RuntimeError("Hyper-Extract returned unsupported graph data")


def build_relation_graph(kb: dict, cfg: dict, doc_id: str) -> dict:
    text = _record_text(kb)
    raw = _run_hyperextract(text, cfg)
    return _normalize_graph(raw, "hyperextract", doc_id)
