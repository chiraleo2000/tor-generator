"""Fan-out canonical prompts to backend, documents/prompts, skill packs, and Amazon Quick.

Source of truth: documents/prompts/canonical/
Idempotent: running twice writes the same bytes.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def _repo_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / "docker-compose.yml").is_file():
            return parent
    return start.parent if start.name == "backend" else start


REPO = _repo_root(BACKEND)
CANONICAL = REPO / "documents" / "prompts" / "canonical"
CORE_MD = CANONICAL / "system_prompt.core.md"
RULES_JSON = CANONICAL / "rules.json"
SECTION_DIR = CANONICAL / "section_prompts"
GENERATED_PY = BACKEND / "app" / "domain" / "generated_prompts.py"
BEGIN = "<!-- GENERATED:BEGIN -->"
END = "<!-- GENERATED:END -->"
QUICK_VERSION = "0.8.3"

SKILL_MD_PATHS = [
    REPO / "skills" / "Draft-TORs-Skills" / "claude" / "tor-procurement" / "SKILL.md",
    REPO / "skills" / "Draft-TORs-Skills" / "chatgpt" / "tor-procurement" / "SKILL.md",
    REPO / "skills" / "Draft-TORs-Skills" / "hermes-agent" / "tor-procurement" / "SKILL.md",
    REPO / "skills" / "check-TORs-Skills" / "claude" / "tor-review" / "SKILL.md",
    REPO / "skills" / "check-TORs-Skills" / "chatgpt" / "tor-review" / "SKILL.md",
    REPO / "skills" / "check-TORs-Skills" / "hermes-agent" / "tor-review" / "SKILL.md",
    REPO / "app" / "infra" / "quick" / "agents-skills" / "skills" / "tor-draft-compose" / "SKILL.md",
    REPO / "app" / "infra" / "quick" / "agents-skills" / "skills" / "tor-draft-intake" / "SKILL.md",
    REPO / "app" / "infra" / "quick" / "agents-skills" / "skills" / "tor-review-compliance" / "SKILL.md",
    REPO / "app" / "infra" / "quick" / "agents-skills" / "skills" / "tor-kb-retrieve" / "SKILL.md",
]

DOC_PROMPT_PATHS = [
    REPO / "documents" / "prompts" / "chatgpt_system_prompt.md",
    REPO / "documents" / "prompts" / "claude_project_instructions.md",
    REPO / "documents" / "prompts" / "tor_writing_guide.md",
]


def load_core() -> str:
    return CORE_MD.read_text(encoding="utf-8").strip() + "\n"


def load_rules() -> dict:
    return json.loads(RULES_JSON.read_text(encoding="utf-8"))


def load_section_snippets() -> dict[str, str]:
    snippets: dict[str, str] = {}
    if not SECTION_DIR.is_dir():
        return snippets
    for path in sorted(SECTION_DIR.rglob("*.md")):
        rel = path.relative_to(SECTION_DIR).as_posix()
        snippets[rel[:-3]] = path.read_text(encoding="utf-8").strip()
    return snippets


def py_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_generated_py(core: str, rules: dict, snippets: dict[str, str]) -> str:
    return (
        "# GENERATED from documents/prompts/canonical/ — do not edit by hand.\n"
        "# Re-run: python -m app.scripts.generate_prompts  (from app/backend)\n"
        "from __future__ import annotations\n\n"
        f"CORE_SYSTEM_PROMPT = {py_string(core)}\n\n"
        f"CANONICAL_RULES = {json.dumps(rules, ensure_ascii=False, indent=2)}\n\n"
        f"SECTION_SNIPPETS = {json.dumps(snippets, ensure_ascii=False, indent=2)}\n"
    )


def upsert_block(path: Path, body: str) -> None:
    chunk = f"{BEGIN}\n{body.rstrip()}\n{END}\n"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if BEGIN in text and END in text:
        pre = text.split(BEGIN, 1)[0]
        post = text.split(END, 1)[1]
        if post.startswith("\n"):
            post = post[1:]
        path.write_text(pre + chunk + post, encoding="utf-8")
        return
    prefix = text.rstrip() + "\n\n" if text.strip() else ""
    path.write_text(prefix + chunk, encoding="utf-8")


def skill_block(core: str, rules: dict) -> str:
    banned = ", ".join(rules.get("banned_english") or [])
    return (
        "## กฎกลางจากแหล่งความจริงเดียว (ไม่ผูกผู้ให้บริการโมเดล)\n\n"
        + core.strip()
        + "\n\n"
        f"- ข้อเท็จจริงบังคับก่อนร่าง: {', '.join(rules.get('fact_required') or [])}\n"
        f"- HITL: {', '.join(rules.get('hitl') or [])}\n"
        f"- ห้ามคำอังกฤษ: {banned}\n"
    )


def write_utf8(path: Path, text: str) -> None:
    data = text.encode("utf-8")
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    path.write_bytes(data)


def bump_quick_version(path: Path) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8-sig")
    updated = re.sub(r'"version":\s*"0\.\d+\.\d+"', f'"version": "{QUICK_VERSION}"', text)
    updated = re.sub(r'"app_version":\s*"0\.\d+\.\d+"', f'"app_version": "{QUICK_VERSION}"', updated)
    updated = re.sub(r"v0\.\d+\.\d+", f"v{QUICK_VERSION}", updated)
    write_utf8(path, updated)


def write_quick_json(core: str) -> None:
    root = REPO / "app" / "infra" / "quick" / "agents-skills"
    for path in [
        root / "manifest.json",
        root / "agents" / "tor-draft-agent.json",
        root / "agents" / "tor-review-agent.json",
        *sorted((root / "skills").glob("*/skill.json")),
        root / "references" / "compliance-rules.json",
    ]:
        bump_quick_version(path)
    draft = root / "agents" / "tor-draft-agent.json"
    if draft.is_file():
        payload = json.loads(draft.read_text(encoding="utf-8-sig"))
        prompt = str(payload.get("prompt") or "")
        marker = "## กฎจากแหล่งความจริงเดียว"
        block = marker + "\n" + core.strip() + "\n"
        if marker in prompt:
            pre = prompt.split(marker, 1)[0]
            rest = prompt.split(marker, 1)[1]
            if "\n## " in rest:
                rest = rest.split("\n## ", 1)[1]
                prompt = pre + block + "\n## " + rest
            else:
                prompt = pre + block
        else:
            prompt = prompt.rstrip() + "\n\n" + block
        payload["prompt"] = prompt
        payload.setdefault("metadata", {})["app_version"] = QUICK_VERSION
        draft.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    structure = root / "references" / "tor-structure.json"
    if structure.is_file():
        data = json.loads(structure.read_text(encoding="utf-8-sig"))
        data["version"] = QUICK_VERSION
        data["note"] = (
            "Gold headings follow Section_Profile per procurement type; "
            "not a single 13-section skeleton. Same Docker image local/cloud."
        )
        structure.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    core = load_core()
    rules = load_rules()
    snippets = load_section_snippets()
    GENERATED_PY.parent.mkdir(parents=True, exist_ok=True)
    GENERATED_PY.write_text(render_generated_py(core, rules, snippets), encoding="utf-8")
    block = skill_block(core, rules)
    for path in DOC_PROMPT_PATHS + SKILL_MD_PATHS:
        if path.exists() or path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            upsert_block(path, block)
            if "agents-skills" in str(path):
                bumped = path.read_text(encoding="utf-8")
                bumped = re.sub(
                    r'version:\s*"0\.\d+\.\d+"',
                    f'version: "{QUICK_VERSION}"',
                    bumped,
                )
                bumped = re.sub(r"v0\.\d+\.\d+", f"v{QUICK_VERSION}", bumped)
                path.write_text(bumped, encoding="utf-8")
    write_quick_json(core)
    print(f"wrote {GENERATED_PY.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
