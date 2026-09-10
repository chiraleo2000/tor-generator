# -*- coding: utf-8 -*-
"""Measure formatting metrics (page size, margins, font sizes, line spacing)
from sample TOR PDFs so the design can use concrete numbers."""
import sys, json, statistics
from pathlib import Path
sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
import pymupdf  # fitz

SAMPLE_DIR = Path(r"d:\แนวปฏิบัติ_กฎระเบียบ_การจัดซื้อจัดจ้าง\documents\ตัวอย่าง TOR")
PT_PER_CM = 28.3465

def most_common_round(vals, ndigits=1):
    if not vals: return None
    from collections import Counter
    c = Counter(round(v, ndigits) for v in vals)
    return c.most_common(1)[0]

def analyze(pdf_path, max_pages=6):
    doc = pymupdf.open(pdf_path)
    page_w = page_h = None
    left_edges, right_edges, top_edges, bottom_edges = [], [], [], []
    font_sizes = []
    fonts = {}
    line_gaps = []
    n = min(len(doc), max_pages)
    for pi in range(n):
        page = doc[pi]
        r = page.rect
        page_w, page_h = round(r.width,1), round(r.height,1)
        d = page.get_text("dict")
        prev_y = None
        for block in d.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                bbox = line["bbox"]
                left_edges.append(bbox[0]); right_edges.append(bbox[2])
                top_edges.append(bbox[1]); bottom_edges.append(bbox[3])
                if prev_y is not None:
                    gap = bbox[1] - prev_y
                    if 0 < gap < 60:
                        line_gaps.append(gap)
                prev_y = bbox[1]
                for span in line.get("spans", []):
                    sz = round(span["size"],1)
                    font_sizes.append(sz)
                    fn = span.get("font","?")
                    fonts[fn] = fonts.get(fn,0)+1
    doc.close()
    def cm(pt): return round(pt/PT_PER_CM,2) if pt is not None else None
    left = min(left_edges) if left_edges else None
    right = (page_w - (max(right_edges)/1)) if right_edges and page_w else None
    top = min(top_edges) if top_edges else None
    bottom = (page_h - max(bottom_edges)) if bottom_edges and page_h else None
    body_size = most_common_round(font_sizes)
    med_gap = round(statistics.median(line_gaps),1) if line_gaps else None
    return {
        "file": Path(pdf_path).name,
        "pages": n,
        "page_w_cm": cm(page_w*PT_PER_CM/PT_PER_CM) if page_w else None,
        "page_size_pt": [page_w, page_h],
        "margin_left_cm": cm(left),
        "margin_right_cm": cm(right),
        "margin_top_cm": cm(top),
        "margin_bottom_cm": cm(bottom),
        "body_font_size_pt": body_size[0] if body_size else None,
        "font_size_distribution": sorted(set(font_sizes)),
        "top_fonts": sorted(fonts.items(), key=lambda x:-x[1])[:4],
        "median_line_gap_pt": med_gap,
    }

results = []
for pdf in sorted(SAMPLE_DIR.glob("*.pdf")):
    try:
        results.append(analyze(str(pdf)))
        print("OK:", pdf.name)
    except Exception as e:
        print("ERR:", pdf.name, e)
out = Path(r"d:\แนวปฏิบัติ_กฎระเบียบ_การจัดซื้อจัดจ้าง\documents\research\analysis\_sample_tor_formatting_metrics.json")
out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nWROTE:", out)
