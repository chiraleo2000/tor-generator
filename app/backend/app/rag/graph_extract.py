"""Ask Gemma to extract a small legal graph as JSON."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.providers.base import LLMProvider
from app.providers.structured_invoke import invoke_with_schema
from app.schemas.llm_structured import GraphExtractResult, json_schema_for

logger = logging.getLogger(__name__)

GRAPH_PROMPT = """คุณเป็นผู้เชี่ยวชาญกฎหมายจัดซื้อจัดจ้างภาครัฐไทย
อ่านข้อความด้านล่างแล้วตอบเป็น JSON เท่านั้น ไม่มีคำอธิบายอื่น

รูปแบบ:
{
  "nodes": [
    {"id": "Law:พรบ2560", "label": "Law", "name": "พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560"},
    {"id": "Article:65", "label": "Article", "name": "มาตรา 65"},
    {"id": "TorSlot:s8", "label": "TorSlot", "name": "s8"},
    {"id": "Concept:ค่าปรับ", "label": "Concept", "name": "ค่าปรับ"}
  ],
  "rels": [
    {"from": "Article:65", "to": "Law:พรบ2560", "type": "CONTAINED_IN"},
    {"from": "Concept:ค่าปรับ", "to": "TorSlot:s10", "type": "APPLIES_TO"},
    {"from": "Article:65", "to": "TorSlot:s11", "type": "CITES"}
  ]
}

label ได้เฉพาะ: Document, Law, Article, TorSlot, Concept
type ของความสัมพันธ์ได้เฉพาะ: CONTAINED_IN, CITES, APPLIES_TO, DEFINES, SUPERSEDES
TorSlot ใช้รหัส s1..s13 หรือ s4.1..s4.14 เท่านั้น
ถ้าไม่มั่นใจให้ละความสัมพันธ์นั้น
"""


def parse_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("LLM did not return JSON")
    blob = text[start : end + 1]
    return json.loads(blob)


async def extract_graph_from_text(
    llm: LLMProvider,
    text: str,
    *,
    document_name: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    excerpt = text[:12000]
    try:
        payload = await invoke_with_schema(
            llm,
            [
                {"role": "system", "content": GRAPH_PROMPT},
                {
                    "role": "user",
                    "content": f"เอกสาร: {document_name}\n\n{excerpt}",
                },
            ],
            json_schema_for(GraphExtractResult),
            "graph_extract",
            temperature=0.1,
            max_tokens=2048,
        )
    except ValueError:
        logger.warning("Graph JSON parse failed for %s", document_name)
        return [], []
    nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
    rels = payload.get("rels") if isinstance(payload.get("rels"), list) else []
    return nodes, rels


def parse_json_lenient(text: str) -> dict[str, Any]:
    fence_start = text.find("```")
    if fence_start < 0:
        return parse_json_object(text)
    after_open = fence_start + 3
    if text.startswith("json", after_open):
        after_open += 4
    fence_end = text.find("```", after_open)
    blob = text[after_open:] if fence_end < 0 else text[after_open:fence_end]
    return parse_json_object(blob)
