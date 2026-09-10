#!/usr/bin/env python3
"""Generate the frontend taxonomy mirror from app/domain/tor_taxonomy.py.

Run from the repo root after editing the Python taxonomy:

    python app/backend/scripts/gen_taxonomy_ts.py

Writes app/frontend/src/lib/tor-taxonomy.generated.ts. Never edit that file
by hand — the Python module is the single source of truth.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
APP_ROOT = BACKEND.parent
TAXONOMY = BACKEND / "app" / "domain" / "tor_taxonomy.py"
OUT = APP_ROOT / "frontend" / "src" / "lib" / "tor-taxonomy.generated.ts"


def load():
    spec = importlib.util.spec_from_file_location("tor_taxonomy", TAXONOMY)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {TAXONOMY}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def j(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def main() -> int:
    t = load()

    fields: dict[str, list[dict[str, object]]] = {}
    for section, rows in t.SECTION_FIELDS.items():
        out: list[dict[str, object]] = []
        for key, label in rows:
            kind, options, map_field = t.field_input(key)
            entry: dict[str, object] = {"key": key, "label": label, "type": kind}
            if options:
                entry["options"] = options
            if map_field:
                entry["mapField"] = map_field
            out.append(entry)
        fields[section] = out

    body = f"""/* AUTO-GENERATED — do not edit.
 * Source: app/backend/app/domain/tor_taxonomy.py
 * Regenerate: python app/backend/scripts/gen_taxonomy_ts.py
 */

export const SCHEMA_VERSION = {t.SCHEMA_VERSION};

export const PROCUREMENT_TYPES: Record<string, string> = {j(t.PROCUREMENT_TYPES)};

export const DEFAULT_PROCUREMENT_TYPE = {j(t.DEFAULT_PROCUREMENT_TYPE)};

export const CONTRACTOR_TERM: Record<string, string> = {j(t.CONTRACTOR_TERM)};

export const SECTION_LABELS: Record<string, string> = {j(t.SECTION_LABELS)};

export const SECTION_LABELS_EN: Record<string, string> = {j(t.SECTION_LABELS_EN)};

export const CORE_SECTION_ORDER: string[] = {j(t.CORE_SECTION_ORDER)};

export const CLOSING_SECTION = {j(t.CLOSING_SECTION)};

export const EXTRA_SECTIONS_BY_TYPE: Record<string, string[]> = {j(t.EXTRA_SECTIONS_BY_TYPE)};

export const SECTION_LABEL_OVERRIDES: Record<string, Record<string, string>> = {j(t.SECTION_LABEL_OVERRIDES)};

export const SCOPE_SUBSECTION_LABELS: Record<string, string> = {j(t.SCOPE_SUBSECTIONS)};

export const SCOPE_BY_TYPE: Record<string, string[]> = {j(t.SCOPE_BY_TYPE)};

export const SCOPE_REQUIRED_BY_TYPE: Record<string, string[]> = {j(t.SCOPE_REQUIRED_BY_TYPE)};

export const QUALIFICATION_SUBSECTION_LABELS: Record<string, string> = {j(t.QUALIFICATION_SUBSECTIONS)};

export const QUALIFICATION_BY_TYPE: Record<string, string[]> = {j(t.QUALIFICATION_BY_TYPE)};

export interface TaxonomyField {{
  key: string;
  label: string;
  type: "text" | "textarea" | "number" | "select";
  options?: string[];
  mapField?: string;
}}

export const SECTION_FIELDS: Record<string, TaxonomyField[]> = {j(fields)};

export const HITL_SECTIONS: string[] = {j(sorted(t.MANDATORY_HUMAN_REVIEW_SECTIONS))};

export const CRITICAL_SECTIONS_MIN_LENGTH: Record<string, number> = {j(t.CRITICAL_SECTIONS_MIN_LENGTH)};

export const MINIMUM_CONTENT_LENGTH = {t.MINIMUM_CONTENT_LENGTH};

export const WIZARD_STEP_COUNT = {t.WIZARD_STEP_COUNT};

export const STEP_SECTION_MAP: Record<number, string[]> = {j({str(k): v for k, v in t.STEP_SECTION_MAP.items()})};

export const STEP_LABELS: Record<number, string> = {j({str(k): v for k, v in t.STEP_LABELS.items()})};

export const SECTION_HINTS: Record<string, string> = {j(t.SECTION_HINTS)};

export const SUBSECTION_HINTS: Record<string, string> = {j({**t.SCOPE_HINTS, **t.QUALIFICATION_HINTS})};

export const LEGACY_SECTION_MAP: Record<string, [string, string | null] | null> = {j({k: (list(v) if v else None) for k, v in t.LEGACY_SECTION_MAP.items()})};

export const DOCUMENT_TITLE = {j(t.DOCUMENT_TITLE)};

export const DRAFT_DOCUMENT_TITLE = {j(t.DRAFT_DOCUMENT_TITLE)};
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(body, encoding="utf-8")
    print(f"wrote {OUT} ({len(body)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
