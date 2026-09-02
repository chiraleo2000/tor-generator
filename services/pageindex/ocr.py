"""
ocr.py
──────────────────────────────────────────────────────────────────────
Shared OCR layer using Azure Document Intelligence (prebuilt-read).

Falls back to fitz → pdfplumber if Azure creds are not configured.

Env vars expected (set in .env):
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
    AZURE_DOCUMENT_INTELLIGENCE_KEY

Usage:
    from ocr import read_pdf_pages
    pages: list[str] = await read_pdf_pages(pdf_path, cfg)
    # pages[i] = full text of page i+1 (0-indexed)
"""

import os
import asyncio
from pathlib import Path


# ── Azure Document Intelligence ─────────────────────────────────────

def _azure_doc_intel_pages(pdf_path: str, endpoint: str, key: str) -> list[str]:
    """Synchronous call — run in executor for async contexts."""
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.credentials import AzureKeyCredential

    client = DocumentIntelligenceClient(endpoint, AzureKeyCredential(key))
    with open(pdf_path, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-read", body=f)
    result = poller.result()

    pages: list[str] = []
    for page in result.pages:
        lines = [line.content for line in (page.lines or [])]
        pages.append("\n".join(lines))
    return pages


# ── Local fallbacks ──────────────────────────────────────────────────

def _fitz_pages(pdf_path: str) -> list[str]:
    import fitz
    doc = fitz.open(pdf_path)
    return [page.get_text() or "" for page in doc]


def _pdfplumber_pages(pdf_path: str) -> list[str]:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        return [p.extract_text() or "" for p in pdf.pages]


# ── Public API ───────────────────────────────────────────────────────

async def read_pdf_pages(pdf_path: str, cfg: dict) -> list[str]:
    """
    Return list[str] — one string per page (0-indexed).

    Priority:
      1. Azure Document Intelligence  (if endpoint + key present in cfg)
      2. fitz (PyMuPDF)
      3. pdfplumber
    """
    endpoint = cfg.get("doc_intel_endpoint") or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
    key      = cfg.get("doc_intel_key")      or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY", "")

    if endpoint and key:
        try:
            loop = asyncio.get_event_loop()
            pages = await loop.run_in_executor(
                None, _azure_doc_intel_pages, pdf_path, endpoint, key
            )
            print(f"[OCR] Azure Document Intelligence — {len(pages)} pages")
            return pages
        except Exception as e:
            print(f"[OCR] Azure DI failed ({e}), falling back to local OCR")

    # fitz
    try:
        pages = _fitz_pages(pdf_path)
        print(f"[OCR] fitz — {len(pages)} pages")
        return pages
    except Exception:
        pass

    # pdfplumber
    try:
        pages = _pdfplumber_pages(pdf_path)
        print(f"[OCR] pdfplumber — {len(pages)} pages")
        return pages
    except Exception as e:
        raise RuntimeError(f"All OCR methods failed for {pdf_path}: {e}")


def read_pdf_pages_sync(pdf_path: str, cfg: dict) -> list[str]:
    """Synchronous wrapper — use inside non-async contexts (e.g., extract_pages)."""
    return asyncio.run(read_pdf_pages(pdf_path, cfg))
