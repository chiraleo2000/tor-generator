"""
Shared document metadata extraction for Knowledge RAG.

The operational meta.json stays small and UI-friendly. This module writes a
richer document_meta.json beside each source and returns the same object for
knowledge_base.json.meta.doc_meta.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx


SCHEMA_VERSION = 1


_EVIDENCE_DEFAULTS = {
    "claim": None,
    "source_field": None,
    "section_id": None,
    "page": None,
    "quote": None,
    "url": None,
}


_DOC_DEFAULTS = {
    "document_title": None,
    "document_type": None,
    "collection": "Compliance",
    "source_type": "Regulation",
    "government_tier": "ส่วนกลาง",
    "ministry": None,
    "agency": None,
    "department": None,
    "related_agencies": [],
    "legal_domain": "Procurement",
    "topic": [],
    "project_type": None,
    "vendor_si": [],
    "relationship_type": [],
    "risk_flags": [],
    "political_context": None,
    "fact_vs_analysis": "Fact",
    "validity": "Current",
    "reliability_level": "Official",
    "confidentiality": "Public",
    "use_case": ["Compliance Screening"],
    "published_date": None,
    "effective_date": None,
    "last_reviewed": None,
    "owner": None,
    "document_no": None,
    "version": None,
    "summary": None,
    "keywords": [],
    "geography": None,
}


_NESTED_DEFAULTS = {
    "issuer": {
        "agency": None,
        "ministry": None,
        "department": None,
        "signer_name": None,
        "signer_position": None,
        "contact_phone": None,
        "contact_email": None,
    },
    "procurement": {
        "egp_related": None,
        "egp_project_id": None,
        "procurement_method": None,
        "procurement_status": None,
        "project_name": None,
        "budget_year": None,
        "budget_amount": None,
        "median_price": None,
        "award_date": None,
        "awarded_vendor": None,
        "contract_amount": None,
        "contract_type": None,
        "work_category": None,
        "vendor_names": [],
        "vendor_registration_class": None,
        "submission_rules": [],
        "exception_agencies": [],
    },
    "case_refs": {
        "court": None,
        "case_no": None,
        "case_type": None,
        "ruling_keywords": [],
    },
}


def _safe_json(raw: str) -> dict:
    raw = (raw or "").strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {}
    return json.loads(match.group())


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v not in (None, "")]
    if value == "":
        return []
    return [value]


def _merge_dict(base: dict, incoming: dict) -> dict:
    merged = dict(base)
    for key, value in (incoming or {}).items():
        if value is None:
            continue
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _file_hash(path: Path, max_bytes: int = 20_000_000) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    remaining = max_bytes
    with path.open("rb") as f:
        while remaining > 0:
            chunk = f.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            h.update(chunk)
            remaining -= len(chunk)
    return h.hexdigest()


def _pdf_page_count(path: Path) -> int | None:
    if not path.exists() or path.suffix.lower() != ".pdf":
        return None
    try:
        from PyPDF2 import PdfReader

        return len(PdfReader(str(path)).pages)
    except Exception:
        return None


def build_source_metadata(
    *,
    doc_id: str,
    source_kind: str,
    source_origin: str,
    source_path: str | Path | None = None,
    original_filename: str | None = None,
    source_url: str | None = None,
    extra: dict | None = None,
) -> dict:
    path = Path(source_path) if source_path else None
    stat = path.stat() if path and path.exists() and path.is_file() else None
    parsed = urlparse(source_url or "")
    mime_type = None
    if original_filename:
        mime_type = mimetypes.guess_type(original_filename)[0]
    if not mime_type and path:
        mime_type = mimetypes.guess_type(str(path))[0]

    source = {
        "doc_id": doc_id,
        "source_kind": source_kind,
        "source_origin": source_origin,
        "original_filename": original_filename,
        "source_url": source_url,
        "source_domain": parsed.netloc or None,
        "file_size_bytes": stat.st_size if stat else None,
        "mime_type": mime_type,
        "page_count": _pdf_page_count(path) if path else None,
        "file_hash_sha256": _file_hash(path) if path and stat else None,
        "language": "th",
        "received_at": time.time(),
    }
    if extra:
        source.update({k: v for k, v in extra.items() if v is not None})
    return source


def empty_document_metadata(source: dict) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "source": source,
        "document": json.loads(json.dumps(_DOC_DEFAULTS, ensure_ascii=False)),
        **{k: json.loads(json.dumps(v, ensure_ascii=False)) for k, v in _NESTED_DEFAULTS.items()},
        "legal_refs": [],
        "evidence_refs": [],
        "quality": {
            "ocr_quality": None,
            "extraction_quality": None,
            "notes": [],
        },
        "extraction": {
            "metadata_extracted_at": None,
            "metadata_extracted_by": None,
        },
    }


def normalize_document_metadata(data: dict, source: dict) -> dict:
    data = data or {}
    document = _merge_dict(_DOC_DEFAULTS, data.get("document") or data)
    for key in (
        "related_agencies",
        "topic",
        "vendor_si",
        "relationship_type",
        "risk_flags",
        "use_case",
        "keywords",
    ):
        document[key] = _as_list(document.get(key))

    nested = {
        name: _merge_dict(default, data.get(name) or {})
        for name, default in _NESTED_DEFAULTS.items()
    }
    for key in ("vendor_names", "submission_rules", "exception_agencies"):
        nested["procurement"][key] = _as_list(nested["procurement"].get(key))
    nested["case_refs"]["ruling_keywords"] = _as_list(nested["case_refs"].get("ruling_keywords"))

    if nested["issuer"].get("agency") and not document.get("agency"):
        document["agency"] = nested["issuer"]["agency"]
    if nested["issuer"].get("ministry") and not document.get("ministry"):
        document["ministry"] = nested["issuer"]["ministry"]
    if nested["issuer"].get("department") and not document.get("department"):
        document["department"] = nested["issuer"]["department"]

    legal_refs = data.get("legal_refs") or []
    if not isinstance(legal_refs, list):
        legal_refs = []

    evidence_refs = data.get("evidence_refs") or []
    if not isinstance(evidence_refs, list):
        evidence_refs = []
    evidence_refs = [
        _merge_dict(_EVIDENCE_DEFAULTS, ref)
        for ref in evidence_refs
        if isinstance(ref, dict)
    ]

    quality = _merge_dict(
        {"ocr_quality": None, "extraction_quality": None, "notes": []},
        data.get("quality") or {},
    )
    quality["notes"] = _as_list(quality.get("notes"))

    extraction = _merge_dict(
        {"metadata_extracted_at": time.time(), "metadata_extracted_by": "azure_openai"},
        data.get("extraction") or {},
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "source": source,
        "document": document,
        **nested,
        "legal_refs": legal_refs,
        "evidence_refs": evidence_refs,
        "quality": quality,
        "extraction": extraction,
    }


def flatten_for_kb(metadata: dict) -> dict:
    """Compatibility shape used by old RAG/search code, with rich fields kept."""
    doc = dict((metadata or {}).get("document") or {})
    source = (metadata or {}).get("source") or {}
    issuer = (metadata or {}).get("issuer") or {}
    procurement = (metadata or {}).get("procurement") or {}
    case_refs = (metadata or {}).get("case_refs") or {}

    doc.update(
        {
            "source_kind": source.get("source_kind"),
            "source_origin": source.get("source_origin"),
            "page_count": source.get("page_count"),
            "file_size_bytes": source.get("file_size_bytes"),
            "source_domain": source.get("source_domain"),
            "issuer": issuer,
            "procurement": procurement,
            "legal_refs": (metadata or {}).get("legal_refs") or [],
            "evidence_refs": (metadata or {}).get("evidence_refs") or [],
            "case_refs": case_refs,
            "quality": (metadata or {}).get("quality") or {},
        }
    )
    return doc


def summarize_for_meta(metadata: dict) -> dict:
    doc = (metadata or {}).get("document") or {}
    source = (metadata or {}).get("source") or {}
    issuer = (metadata or {}).get("issuer") or {}
    procurement = (metadata or {}).get("procurement") or {}
    return {
        "document_title": doc.get("document_title"),
        "document_type": doc.get("document_type"),
        "document_no": doc.get("document_no"),
        "published_date": doc.get("published_date"),
        "effective_date": doc.get("effective_date"),
        "agency": doc.get("agency") or issuer.get("agency"),
        "ministry": doc.get("ministry") or issuer.get("ministry"),
        "related_agencies": doc.get("related_agencies") or [],
        "legal_domain": doc.get("legal_domain"),
        "collection": doc.get("collection"),
        "source_type": doc.get("source_type"),
        "project_type": doc.get("project_type"),
        "relationship_type": doc.get("relationship_type") or [],
        "risk_flags": doc.get("risk_flags") or [],
        "last_reviewed": doc.get("last_reviewed"),
        "procurement_method": procurement.get("procurement_method"),
        "procurement_status": procurement.get("procurement_status"),
        "work_category": procurement.get("work_category"),
        "page_count": source.get("page_count"),
        "file_size_bytes": source.get("file_size_bytes"),
        "source_domain": source.get("source_domain"),
        "metadata_schema_version": SCHEMA_VERSION,
    }


async def extract_document_metadata(
    text: str,
    cfg: dict,
    source: dict,
    *,
    fallback_title: str | None = None,
) -> dict:
    sample = re.sub(r"\s+", " ", text or "").strip()[:7000]
    defaults = empty_document_metadata(source)
    if fallback_title:
        defaults["document"]["document_title"] = fallback_title
    if not sample:
        return defaults

    prompt = f"""วิเคราะห์ metadata กลางของเอกสาร/ข่าวนี้สำหรับระบบ Knowledge RAG ภาครัฐไทย
ตอบเป็น JSON object เดียว ไม่มี markdown และใช้ null เมื่อไม่พบข้อมูล

Schema ที่ต้องตอบ:
{{
  "document": {{
    "document_title": "...",
    "document_type": "ประกาศ | หนังสือเวียน | คู่มือ | TOR | ข่าว | คำวินิจฉัย | กฎหมาย | ตารางแนบ | อื่นๆ",
    "collection": "Strategy | Agency | News | Bidding | Procurement | Vendor | Political | Relationship | Compliance | Legal | Risk",
    "source_type": "Official Plan | Law | Regulation | Circular | News | TOR | Award Notice | Court Case | Internal Analysis",
    "government_tier": "ส่วนกลาง | ภูมิภาค | ท้องถิ่น",
    "ministry": null,
    "agency": null,
    "department": null,
    "related_agencies": [],
    "legal_domain": "Procurement | PDPA | Cybersecurity | Cloud | Digital Government | Contract | Labor | Finance | null",
    "topic": [],
    "project_type": "e-Service | Data Platform | Call Center | OSS | e-Document | AI Assistant | อื่นๆ | null",
    "vendor_si": [],
    "relationship_type": ["Awarded Contract | MOU | Seminar | Advisor | Past Project | News Mention"],
    "risk_flags": ["locked_spec | appeal | complaint | legal_dispute | delivery_risk | privacy_risk | cybersecurity_risk"],
    "political_context": null,
    "fact_vs_analysis": "Fact | Analysis | Mixed",
    "validity": "Current | Historical | Superseded",
    "reliability_level": "Official | Verified | News | Secondary | Internal Analysis",
    "confidentiality": "Public | Internal | Restricted",
    "use_case": ["Compliance Screening"],
    "published_date": "YYYY-MM-DD หรือ null",
    "effective_date": "YYYY-MM-DD หรือ null",
    "last_reviewed": "YYYY-MM-DD หรือ null",
    "owner": null,
    "document_no": null,
    "version": null,
    "summary": "สรุปสั้น 2-4 ประโยค",
    "keywords": [],
    "geography": null
  }},
  "issuer": {{
    "agency": null,
    "ministry": null,
    "department": null,
    "signer_name": null,
    "signer_position": null,
    "contact_phone": null,
    "contact_email": null
  }},
  "procurement": {{
    "egp_related": null,
    "egp_project_id": null,
    "procurement_method": null,
    "procurement_status": "TOR | announced | awarded | cancelled | appeal | contract_signed | null",
    "project_name": null,
    "budget_year": null,
    "budget_amount": null,
    "median_price": null,
    "award_date": "YYYY-MM-DD หรือ null",
    "awarded_vendor": null,
    "contract_amount": null,
    "contract_type": null,
    "work_category": null,
    "vendor_names": [],
    "vendor_registration_class": null,
    "submission_rules": [],
    "exception_agencies": []
  }},
  "legal_refs": [{{"law_name": "...", "year": null, "section": null}}],
  "case_refs": {{
    "court": null,
    "case_no": null,
    "case_type": null,
    "ruling_keywords": []
  }},
  "evidence_refs": [
    {{
      "claim": "ข้อเท็จจริง/ความเสี่ยง/ความสัมพันธ์ที่พบ",
      "source_field": "project_type | relationship_type | risk_flags | procurement | legal_refs | vendor_si",
      "section_id": null,
      "page": null,
      "quote": "ข้อความหลักฐานสั้นๆ จากเอกสาร ถ้ามี",
      "url": null
    }}
  ],
  "quality": {{
    "ocr_quality": "good | fair | poor | unknown",
    "extraction_quality": "good | fair | poor | unknown",
    "notes": []
  }}
}}

แนวทางวิเคราะห์:
- ให้แยกข้อเท็จจริงจากบทวิเคราะห์ ถ้าเป็นข้อมูลจากเอกสารโดยตรงใช้ fact_vs_analysis="Fact"; ถ้าเป็นข้อสังเกต/ตีความใช้ "Analysis"; ถ้าปนกันใช้ "Mixed"
- relationship_type และ risk_flags ต้องอิงจากข้อมูลเปิดเผยในเอกสารเท่านั้น ห้ามเดาหรือใช้ข่าวลือ
- ถ้าพบข้อมูลจัดซื้อจัดจ้าง ให้ดึงเลขโครงการ e-GP, สถานะโครงการ, ปีงบประมาณ, ผู้ชนะ, วงเงินสัญญา, ราคากลาง และวิธีจัดซื้อเท่าที่พบ
- ถ้าพบ vendor/SI footprint ให้ใส่ชื่อ vendor ใน document.vendor_si และ procurement.vendor_names พร้อม evidence_refs
- ถ้าพบ red flag เช่น อุทธรณ์ ร้องเรียน ล็อกสเปก คดี ความเสี่ยงส่งมอบ PDPA หรือ cybersecurity ให้ใส่ risk_flags พร้อม evidence_refs
- evidence_refs ควรเป็นหลักฐานสั้นๆ เพื่อ trace กลับไปยังข้อความ/หน้า/URL ได้ ไม่ต้องสร้างถ้าไม่มีหลักฐาน

เนื้อหาตัวอย่าง:
{sample}
"""

    try:
        ep = (cfg.get("endpoint") or "").rstrip("/")
        model = cfg.get("model", "gpt-4o-mini")
        api_ver = cfg.get("api_version", "2024-08-01-preview")
        url = f"{ep}/openai/deployments/{model}/chat/completions?api-version={api_ver}"
        headers = {"api-key": cfg.get("api_key", ""), "Content-Type": "application/json"}
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "คุณเป็นผู้เชี่ยวชาญเอกสารราชการไทย จัดซื้อจัดจ้าง กฎหมาย ข่าวภาครัฐ และ market intelligence ตอบ JSON เท่านั้น",
                },
                {"role": "user", "content": prompt},
            ],
            "max_completion_tokens": 3000,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]
        parsed = _safe_json(raw)
        metadata = normalize_document_metadata(parsed, source)
        if fallback_title and not metadata["document"].get("document_title"):
            metadata["document"]["document_title"] = fallback_title
        return metadata
    except Exception as exc:
        fallback = defaults
        fallback["quality"]["notes"].append(f"metadata extraction fallback: {exc}")
        fallback["extraction"]["metadata_extracted_at"] = time.time()
        fallback["extraction"]["metadata_extracted_by"] = "fallback"
        return fallback


def save_document_metadata(doc_dir: Path, metadata: dict) -> None:
    (doc_dir / "document_meta.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
