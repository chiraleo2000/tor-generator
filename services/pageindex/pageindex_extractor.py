"""
pageindex_extractor.py
─────────────────────────────────────────────────────────────────────
Alternative extraction pipeline using VectifyAI/PageIndex library.

PageIndex builds a LLM-verified hierarchical tree from OCR text
(no chunking, no vector DB). This module:
  1. Reads PDF pages through our OCR layer
  2. Runs PageIndex on OCR page text → tree structure JSON
  3. Flattens the tree to records compatible with our KB format
  4. Enriches each record: details (page text), keywords, section_meta
  5. Runs doc-level classification (collection, ministry, agency …)
  6. Returns the same knowledge_base.json dict that app.py writes

Usage from app.py:
    from pageindex_extractor import extract_with_pageindex
    kb = await extract_with_pageindex(pdf_path, doc_id, cfg, progress_cb)
"""

import os, re, json, time, asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


# ── Helpers ───────────────────────────────────────────────────────────
def _configure_litellm_azure(cfg: dict) -> str:
    """
    Configure LiteLLM from the current app config.

    The settings screen persists Azure OpenAI values in config.json, so reading
    only .env at import time makes PageIndex fail even while the default engine
    works. LiteLLM reads Azure credentials from environment variables.
    """
    endpoint = (cfg.get("endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT", "")).strip().rstrip("/")
    api_key = (cfg.get("api_key") or os.getenv("AZURE_OPENAI_API_KEY", "")).strip()
    api_version = (cfg.get("api_version") or os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")).strip()
    deployment = (cfg.get("model") or os.getenv("AZURE_OPENAI_MODEL", "gpt-4o-mini")).strip()

    missing = []
    if not endpoint:
        missing.append("Azure endpoint")
    if not api_key:
        missing.append("Azure API key")
    if not deployment:
        missing.append("Azure deployment/model")
    if missing:
        raise ValueError("PageIndex config ไม่ครบ: " + ", ".join(missing))

    os.environ["AZURE_API_KEY"] = api_key
    os.environ["AZURE_API_BASE"] = endpoint
    os.environ["AZURE_API_VERSION"] = api_version

    # Some LiteLLM versions also check these OpenAI-style Azure aliases.
    os.environ["AZURE_OPENAI_API_KEY"] = api_key
    os.environ["AZURE_OPENAI_ENDPOINT"] = endpoint
    os.environ["AZURE_OPENAI_API_VERSION"] = api_version

    return f"azure/{deployment}"


def _require_pageindex_dependencies():
    missing = []
    for module_name, package_name in (
        ("litellm", "litellm"),
        ("PyPDF2", "PyPDF2"),
        ("pymupdf", "PyMuPDF"),
        ("yaml", "PyYAML"),
    ):
        try:
            __import__(module_name)
        except ModuleNotFoundError:
            missing.append(package_name)

    if missing:
        raise RuntimeError(
            "PageIndex dependency ยังไม่ครบ: "
            + ", ".join(missing)
            + " — รัน `pip install -r requirements.txt` แล้วเริ่ม server ใหม่"
        )


async def _emit_progress(progress_cb, pct: int, msg: str):
    if progress_cb:
        await progress_cb(pct, msg)
    print(f"[PageIndex] {pct}% — {msg}")


async def _run_pageindex_on_ocr_pages(pages: list[str], source_path: str, opt: object) -> dict:
    """Run PageIndex core on OCR text pages instead of letting it parse the PDF."""
    from pageindex.page_index import (
        process_no_toc,
        tree_parser,
        validate_and_truncate_physical_indices,
    )
    from pageindex.utils import (
        JsonLogger,
        add_node_text,
        add_preface_if_needed,
        count_tokens,
        format_structure,
        generate_doc_description,
        generate_summaries_for_structure,
        create_clean_structure_for_description,
        post_processing,
        remove_structure_text,
        write_node_id,
    )

    page_list = [(page_text or "", count_tokens(page_text or "", model=opt.model)) for page_text in pages]
    logger = JsonLogger(source_path)
    logger.info({"ocr_text_source": True, "total_page_number": len(page_list)})
    logger.info({"total_token": sum(page[1] for page in page_list)})

    try:
        structure = await tree_parser(page_list, opt, doc=source_path, logger=logger)
    except Exception as exc:
        if str(exc) != "Processing failed":
            raise

        logger.info("Verified PageIndex tree failed; falling back to OCR TOC without verifier")
        toc_with_page_number = process_no_toc(page_list, start_index=1, model=opt.model, logger=logger)
        toc_with_page_number = [item for item in toc_with_page_number if item.get("physical_index") is not None]
        toc_with_page_number = validate_and_truncate_physical_indices(
            toc_with_page_number,
            len(page_list),
            start_index=1,
            logger=logger,
        )
        toc_with_page_number = add_preface_if_needed(toc_with_page_number)
        for item in toc_with_page_number:
            item.setdefault("appear_start", "no")
        structure = post_processing(toc_with_page_number, len(page_list))

    if opt.if_add_node_id == "yes":
        write_node_id(structure)
    if opt.if_add_node_text == "yes":
        add_node_text(structure, page_list)
    if opt.if_add_node_summary == "yes":
        if opt.if_add_node_text == "no":
            add_node_text(structure, page_list)
        await generate_summaries_for_structure(structure, model=opt.model)
        if opt.if_add_node_text == "no":
            remove_structure_text(structure)
        if opt.if_add_doc_description == "yes":
            clean_structure = create_clean_structure_for_description(structure)
            doc_description = generate_doc_description(clean_structure, model=opt.model)
            structure = format_structure(
                structure,
                order=["title", "node_id", "start_index", "end_index", "summary", "text", "nodes"],
            )
            return {
                "doc_name": Path(source_path).stem,
                "doc_description": doc_description,
                "structure": structure,
            }

    structure = format_structure(
        structure,
        order=["title", "node_id", "start_index", "end_index", "summary", "text", "nodes"],
    )
    return {"doc_name": Path(source_path).stem, "structure": structure}


async def _read_pages(pdf_path: str, cfg: dict) -> list[str]:
    """Read PDF pages via Azure Document Intelligence (or local fallback)."""
    from ocr import read_pdf_pages
    return await read_pdf_pages(pdf_path, cfg)


def _extract_keywords(text: str, n: int = 8) -> list[str]:
    """
    Simple keyword extraction for Thai+EN text:
    Strip numbers/punctuation, return top-n distinct words by length.
    """
    # Remove page headers like "- 5 -", dots, parentheses
    text = re.sub(r'-\s*\d+\s*-', '', text)
    text = re.sub(r'[.…,;:()\[\]{}/\\|"\'\d]', ' ', text)
    # Split on whitespace
    words = [w.strip() for w in text.split() if len(w.strip()) >= 3]
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for w in words:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    # Prefer longer words (more meaningful in Thai)
    unique.sort(key=lambda w: -len(w))
    return unique[:n]


def _flatten_tree(nodes: list, pages: list[str],
                  parent_id: str = "", depth: int = 0) -> list[dict]:
    """
    Recursively flatten PageIndex tree → list of section records.
    section_id mirrors the positional index, e.g. "1", "1.2", "1.2.3".
    """
    records = []
    for i, node in enumerate(nodes, start=1):
        sid = f"{parent_id}.{i}" if parent_id else str(i)

        # Page text for this node (start_index/end_index are 1-based page numbers)
        start_pg = node.get("start_index", 1)
        end_pg   = node.get("end_index",   start_pg)
        page_texts = pages[start_pg - 1 : end_pg]
        raw_text   = "\n".join(t for t in page_texts if t.strip())

        # Trim details to 700 chars for BM25 friendliness
        details = re.sub(r'\s+', ' ', raw_text).strip()[:700]
        keywords = _extract_keywords(raw_text)
        summary  = node.get("summary") or node.get("title", "")

        records.append({
            "section_id": sid,
            "chapter_no": sid.split(".")[0],
            "chapter":    f"บทที่ {sid.split('.')[0]}",
            "title":      node.get("title", ""),
            "summary":    summary,
            "details":    details,
            "keywords":   keywords,
            "page_start": start_pg,
            "page_end":   end_pg,
            "node_id":    node.get("node_id", ""),
            "boost":      1.5 if depth == 0 else (1.0 if depth >= 2 else 1.2),
            "section_meta": {
                "legal_domain": None,
                "topic":   [],
                "use_case": [],
                "case_id": None,
            },
        })

        # Recurse into children
        if node.get("nodes"):
            records.extend(
                _flatten_tree(node["nodes"], pages, parent_id=sid, depth=depth + 1)
            )

    return records


def _build_page_index(records: list[dict]) -> dict:
    """Build page_index dict from flat records list."""
    page_index: dict = {}
    for rec in records:
        chapter_no = rec["chapter_no"]
        sid        = rec["section_id"]

        if chapter_no not in page_index:
            # Find chapter-level record
            ch_rec = next((r for r in records if r["section_id"] == chapter_no), rec)
            page_index[chapter_no] = {
                "id":       chapter_no,
                "title":    ch_rec["title"],
                "sections": {},
            }

        if "." in sid:  # only non-chapter sections
            page_index[chapter_no]["sections"][sid] = {
                "id":       sid,
                "title":    rec["title"],
                "children": [],
            }

    # Wire children
    for chapter_no, ch in page_index.items():
        for sid in list(ch["sections"].keys()):
            parts = sid.split(".")
            if len(parts) >= 3:
                parent_id = ".".join(parts[:-1])
                if parent_id in ch["sections"]:
                    if sid not in ch["sections"][parent_id]["children"]:
                        ch["sections"][parent_id]["children"].append(sid)

    return page_index


async def _classify_document(sample_text: str, cfg: dict) -> dict:
    """
    Return lightweight defaults.

    The app-level metadata_extractor now performs the richer document metadata
    pass after PageIndex has produced OCR-backed records. Keeping this function
    cheap avoids making two LLM metadata calls for the same document.
    """
    return {
        "collection":        "Compliance",
        "source_type":       "Regulation",
        "government_tier":   "ส่วนกลาง",
        "ministry":          None,
        "agency":            None,
        "related_agencies":  [],
        "legal_domain":      "Procurement",
        "topic":             [],
        "vendor_si":         [],
        "political_context": None,
        "validity":          "Current",
        "reliability_level": "Official",
        "confidentiality":   "Public",
        "use_case":          ["Compliance Screening"],
        "published_date":    None,
        "geography":         None,
    }


def _split_text_pages(text: str, max_chars: int = 3500) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    pages, buf = [], ""
    for para in paragraphs:
        if buf and len(buf) + len(para) + 2 > max_chars:
            pages.append(buf.strip())
            buf = para
        else:
            buf = f"{buf}\n\n{para}".strip() if buf else para
    if buf:
        pages.append(buf.strip())
    if not pages and text.strip():
        pages = [text.strip()[i:i + max_chars] for i in range(0, len(text.strip()), max_chars)]
    return pages


async def _build_kb_from_pages(
    pages: list[str],
    doc_id: str,
    cfg: dict,
    source_path: str,
    source_name: str,
    progress_cb=None,
    source_url: str | None = None,
    source_kind: str = "pdf",
) -> dict:
    async def emit(pct: int, msg: str):
        if progress_cb:
            await progress_cb(pct, msg)
        print(f"[PageIndex] {pct}% — {msg}")

    if not pages:
        raise ValueError("ไม่มี plain text สำหรับสร้าง PageIndex")

    # ── 2. Run PageIndex tree builder ─────────────────────────────────
    await emit(15, "PageIndex กำลังวิเคราะห์โครงสร้างจาก plain text …")

    _require_pageindex_dependencies()
    litellm_model = _configure_litellm_azure(cfg)
    await emit(18, "เตรียมโมเดลสำหรับ PageIndex …")

    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from pageindex.utils import ConfigLoader

    opt = ConfigLoader().load({
        "model":                litellm_model,
        "if_add_node_summary":  "yes",
        "if_add_doc_description": "no",
        "if_add_node_text":     "no",
        "if_add_node_id":       "yes",
        "toc_check_page_num":   20,
        "max_page_num_each_node": 10,
    })

    try:
        await emit(22, "PageIndex กำลังสร้าง tree จาก plain text …")
        pi_result = await _run_pageindex_on_ocr_pages(pages, source_path, opt)
    except Exception as e:
        raise RuntimeError(f"PageIndex failed: {e}") from e

    await emit(60, "PageIndex สร้าง tree structure จาก plain text สำเร็จ")

    # ── 3. Flatten tree → records ─────────────────────────────────────
    await emit(65, "แปลง tree → records …")
    structure = pi_result.get("structure", [])
    if not structure:
        raise RuntimeError(
            "PageIndex ไม่พบโครงสร้างจาก plain text นี้ "
            "ลองตรวจคุณภาพเนื้อหาที่ดึงมา หรือใช้ source อื่น"
        )

    records_raw = _flatten_tree(structure, pages)
    doc_name    = source_name or pi_result.get("doc_name") or Path(source_path).stem

    # ── 4. Classify document ──────────────────────────────────────────
    await emit(70, "จำแนกประเภทเอกสาร …")
    sample = "\n".join(p for p in pages[:6] if p.strip())
    doc_meta = await _classify_document(sample, cfg)
    if source_kind == "link":
        doc_meta["source_type"] = doc_meta.get("source_type") or "News"
        doc_meta["reliability_level"] = doc_meta.get("reliability_level") or "News"

    # ── 5. Build final records (add id + search_text) ─────────────────
    await emit(80, f"สร้าง {len(records_raw)} records …")
    prefix = doc_id.upper().replace("-", "")[:8]
    records = []
    for i, r in enumerate(records_raw, start=1):
        rec = {
            "id":           f"{prefix}-{i:04d}",
            "section_id":   r["section_id"],
            "chapter_no":   r["chapter_no"],
            "chapter":      r["chapter"],
            "title":        r["title"],
            "summary":      r["summary"],
            "details":      r["details"],
            "keywords":     r["keywords"],
            "section_meta": r["section_meta"],
            "boost":        r["boost"],
            "page_start":   r["page_start"],
            "page_end":     r["page_end"],
            "search_text":  f"{r['title']} {r['summary']} {r['details']} {' '.join(r['keywords'])}",
        }
        records.append(rec)

    # ── 6. Build page_index ───────────────────────────────────────────
    await emit(88, "สร้าง page_index …")
    page_index = _build_page_index(records)

    # ── 7. Assemble knowledge_base dict ──────────────────────────────
    await emit(95, "รวม knowledge_base …")
    knowledge_base = {
        "meta": {
            "doc_title":     doc_name,
            "source":        source_url or Path(source_path).name,
            "source_url":    source_url,
            "source_kind":   source_kind,
            "total_records": len(records),
            "doc_meta":      doc_meta,
            "extracted_by":  "pageindex",
        },
        "page_index": page_index,
        "records":    records,
    }

    await emit(100, f"เสร็จสิ้น — {len(records)} records, {len(page_index)} chapters")
    return knowledge_base


# ── Main entry points ─────────────────────────────────────────────────
async def extract_with_pageindex(
    pdf_path: str,
    doc_id:   str,
    cfg:      dict,
    progress_cb=None,
) -> dict:
    await _emit_progress(progress_cb, 5, "เริ่มโหลด PDF …")
    pages = await _read_pages(pdf_path, cfg)
    if not pages:
        raise ValueError(f"Cannot read PDF: {pdf_path}")
    await _emit_progress(progress_cb, 10, f"OCR สำเร็จ {len(pages)} หน้า")
    return await _build_kb_from_pages(
        pages=pages,
        doc_id=doc_id,
        cfg=cfg,
        source_path=pdf_path,
        source_name=Path(pdf_path).stem,
        progress_cb=progress_cb,
        source_kind="pdf",
    )


async def extract_text_with_pageindex(
    text: str,
    doc_id: str,
    cfg: dict,
    progress_cb=None,
    source_name: str = "Web source",
    source_url: str | None = None,
    source_path: str | None = None,
    source_kind: str = "link",
) -> dict:
    pages = _split_text_pages(text)
    await _emit_progress(progress_cb, 35, f"เตรียม plain text สำเร็จ {len(pages)} blocks")
    return await _build_kb_from_pages(
        pages=pages,
        doc_id=doc_id,
        cfg=cfg,
        source_path=source_path or source_name,
        source_name=source_name,
        progress_cb=progress_cb,
        source_url=source_url,
        source_kind=source_kind,
    )
