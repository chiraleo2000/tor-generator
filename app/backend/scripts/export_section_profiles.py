"""Export Section_Profile JSON for the frontend mirror and Quick pack."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.domain.section_profile import profile_export  # noqa: E402


def main() -> None:
    payload = profile_export()
    dest = BACKEND / "app" / "domain" / "section_profiles.json"
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(dest)


if __name__ == "__main__":
    main()
