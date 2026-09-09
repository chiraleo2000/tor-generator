"""Generate app/frontend/src/lib/tor-profiles.generated.ts from Section_Profile."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.domain.section_profile import profile_export  # noqa: E402

HEADER = """\
/** Generated from app/backend/app/domain/section_profile.py — do not edit by hand. */
/* eslint-disable */

export type ProfileStatus = "ok" | "none" | "missing";

export interface GeneratedSubsection {
  key: string;
  semantic_key: string;
  title: string;
  required: boolean;
  hint: string;
}

export interface GeneratedMainSection {
  key: string;
  semantic_key: string;
  title: string;
  required: boolean;
  hitl: boolean;
  hint: string;
}

export interface GeneratedProfile {
  label: string;
  main_sections: GeneratedMainSection[];
  scope_subsections: GeneratedSubsection[];
  fact_required: string[];
}

"""


def main() -> None:
    payload = profile_export()
    dest = BACKEND.parent / "frontend" / "src" / "lib" / "tor-profiles.generated.ts"
    body = HEADER + "export const SECTION_PROFILES = "
    body += json.dumps(payload, ensure_ascii=False, indent=2)
    body += " as const;\n"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(body, encoding="utf-8")
    json_dest = BACKEND / "app" / "domain" / "section_profiles.json"
    json_dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(dest)
    print(json_dest)


if __name__ == "__main__":
    main()
