# -*- coding: utf-8 -*-
"""Live review / analyze / draft against real TOR documents. No mocks."""
from __future__ import annotations

import json
import os
import subprocess
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:4000/api/v1"
REPO = Path(r"d:\แนวปฏิบัติ_กฎระเบียบ_การจัดซื้อจัดจ้าง")
OUT = REPO / "Discussions" / "test-evidence" / "real-run"
EMAIL = os.environ.get("E2E_EMAIL", "officer@example.go.th")
PASSWORD = os.environ.get("E2E_PASSWORD", "Passw0rd!")
TOKEN = ""
TIMEOUT_EXTRACT = 900
TIMEOUT_REVIEW = 1800
TIMEOUT_ANALYZE = 1200
TIMEOUT_INTAKE = 1800
TIMEOUT_DRAFT = 3600
JSON_MEDIA = "application/json"
DRAFT_RUN_JSON = "draft-run.json"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def save(name: str, payload: Any) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    if isinstance(payload, (dict, list)):
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        path.write_text(str(payload), encoding="utf-8")
    return path


def unwrap(body: dict[str, Any]) -> Any:
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


def http_json(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    data = None
    headers = {"Accept": JSON_MEDIA}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = JSON_MEDIA
    req = Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {path}: {err_body[:2000]}") from exc
    except URLError as exc:
        raise RuntimeError(f"URL error {path}: {exc}") from exc


def read_sse(path: str, payload: dict[str, Any] | None = None, timeout: int = 1800) -> list[str]:
    headers = {
        "Accept": "text/event-stream",
        "Authorization": f"Bearer {TOKEN}",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = JSON_MEDIA
    req = Request(BASE + path, data=data, headers=headers, method="POST")
    events: list[str] = []
    with urlopen(req, timeout=timeout) as resp:
        buf = ""
        deadline = time.time() + timeout
        while time.time() < deadline:
            chunk = resp.read(4096)
            if not chunk:
                break
            buf += chunk.decode("utf-8", errors="replace")
            while "\n\n" in buf:
                frame, buf = buf.split("\n\n", 1)
                if frame.strip():
                    events.append(frame[:4000])
                if "event: done" in frame or "event: error" in frame:
                    return events
    return events


def http_multipart(
    path: str,
    files: list[tuple[str, Path]],
    timeout: int = 600,
    field: str = "file",
) -> dict[str, Any]:
    boundary = f"----RealRun{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for _name, file_path in files:
        fname = file_path.name
        mime = "application/pdf"
        if fname.lower().endswith(".docx"):
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif fname.lower().endswith(".xlsx"):
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif fname.lower().endswith(".txt"):
            mime = "text/plain"
        header = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{field}"; filename="{fname}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8")
        chunks.append(header)
        chunks.append(file_path.read_bytes())
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("ascii"))
    body = b"".join(chunks)
    headers = {
        "Accept": JSON_MEDIA,
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Authorization": f"Bearer {TOKEN}",
    }
    req = Request(BASE + path, data=body, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {path}: {err_body[:2000]}") from exc


def find_named(roots: list[Path], needle: str) -> Path | None:
    needle_l = needle.lower()
    for root in roots:
        if not root.exists():
            continue
        try:
            for item in root.iterdir():
                if item.is_file() and needle_l in item.name.lower():
                    return item
        except OSError:
            continue
    # one-level extra: repo children that are files only
    return None


def _matched_doc_slugs(item: Path) -> list[str]:
    if not item.is_file():
        return []
    name = item.name
    lower = name.lower()
    slugs: list[str] = []
    if "สกก" in name or ("edit" in lower and lower.endswith(".docx")):
        slugs.append("skk")
    if "Amazon Quick" in name and lower.endswith(".pdf"):
        slugs.append("amazon")
    if "local" in lower and "แรงงานเกษตร" in name and lower.endswith(".pdf"):
        slugs.append("local")
    return slugs


def discover_docs() -> dict[str, Path]:
    roots = [REPO, REPO.parent, Path("d:/"), Path.home() / "Desktop", Path.home() / "Downloads"]
    found: dict[str, Path] = {}
    for item in REPO.iterdir():
        for slug in _matched_doc_slugs(item):
            found[slug] = item
    if "skk" not in found:
        alt = find_named(roots, "สกก")
        if alt:
            found["skk"] = alt
    return found


def login() -> str:
    global TOKEN
    body = http_json(
        "POST",
        "/auth/login",
        {"email": EMAIL, "password": PASSWORD},
        timeout=30,
    )
    data = unwrap(body)
    token = data.get("token") if isinstance(data, dict) else None
    if not token:
        raise RuntimeError("login returned no token")
    TOKEN = token
    user = data.get("user") if isinstance(data, dict) else {}
    save(
        "00-login.json",
        {
            "ok": True,
            "email": (user or {}).get("email"),
            "role": (user or {}).get("role"),
            "user_id": (user or {}).get("id"),
        },
    )
    return TOKEN


def postgres_text(job_id: str) -> str:
    sql = f"SELECT COALESCE(extracted_text,'') FROM review_jobs WHERE id = '{job_id}'"
    cmd = [
        "docker",
        "exec",
        "tor-app-postgres-1",
        "sh",
        "-c",
        f'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -A -c "{sql}"',
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(f"psql failed: {(proc.stderr or proc.stdout)[:500]}")
    return proc.stdout


def summarize_findings(findings: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    out = []
    for item in findings[:limit]:
        out.append(
            {
                "severity": item.get("severity") or item.get("finding_kind"),
                "kind": item.get("finding_kind") or item.get("kind"),
                "rule": item.get("rule_violated") or item.get("rule"),
                "section": item.get("affected_section") or item.get("section_key"),
                "message": (item.get("message") or item.get("reason") or "")[:400],
                "correction": (item.get("recommended_correction") or item.get("suggested_text") or "")[:400],
                "legal_basis": (item.get("legal_basis") or "")[:300],
                "risk_type": item.get("risk_type"),
            }
        )
    return out


def summarize_part(part: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(part, dict):
        return {}
    findings = part.get("findings") or []
    return {
        "score": part.get("score") or part.get("quality_score"),
        "label": part.get("label") or part.get("title"),
        "summary": (part.get("summary") or part.get("verdict") or "")[:800],
        "finding_count": len(findings),
        "top_findings": [
            {
                "section": f.get("section_key") or f.get("affected_section"),
                "reason": (f.get("reason") or f.get("message") or "")[:400],
                "suggested": (f.get("suggested_text") or "")[:400],
                "legal_basis": (f.get("legal_basis") or "")[:300],
                "risk_type": f.get("risk_type"),
            }
            for f in findings[:8]
        ],
    }


def _full_extract_text(slug: str, path: Path, result: dict[str, Any]) -> tuple[str, Any]:
    log(f"{slug}: extract {path.name} ({result['bytes']} bytes)")
    t_ex = time.time()
    extracted = unwrap(http_multipart("/review/extract", [("file", path)], timeout=TIMEOUT_EXTRACT))
    job_id = extracted.get("id")
    preview = extracted.get("extracted_text") or ""
    result["extract"] = {
        "ok": True,
        "id": job_id,
        "status": extracted.get("status"),
        "preview_chars": len(preview),
        "preview_head": preview[:1200],
        "seconds": round(time.time() - t_ex, 1),
    }
    save(f"{slug}-extract.json", result["extract"])
    full_text = _prefer_db_text(job_id, preview, result)
    result["extract"]["full_chars"] = len(full_text)
    save(f"{slug}-extracted.txt", full_text[:200000])
    return full_text, job_id


def _prefer_db_text(job_id: Any, preview: str, result: dict[str, Any]) -> str:
    if not job_id:
        return preview
    try:
        db_text = postgres_text(str(job_id))
        if db_text and len(db_text) > len(preview):
            return db_text
    except Exception as exc:
        result["extract"]["db_text_error"] = str(exc)[:300]
    return preview


def _review_part_block(review: dict[str, Any]) -> tuple[dict[str, Any], Any]:
    part_scores = review.get("part_scores")
    if not isinstance(part_scores, dict):
        return {}, None
    scores = {
        key: summarize_part(part_scores.get(key))
        for key in ("legal", "lock_in", "project")
    }
    return scores, part_scores.get("summary")


def _record_review(slug: str, job_id: Any, result: dict[str, Any]) -> None:
    log(f"{slug}: review job {job_id}")
    t_rv = time.time()
    review = unwrap(http_json("POST", "/review/run", {"id": job_id}, timeout=TIMEOUT_REVIEW))
    findings = review.get("findings") or []
    part_scores, part_summary = _review_part_block(review)
    result["review"] = {
        "ok": True,
        "id": review.get("id") or job_id,
        "quality_score": review.get("quality_score"),
        "status": review.get("status"),
        "overall_assessment": (review.get("overall_assessment") or "")[:2000],
        "finding_count": len(findings),
        "top_findings": summarize_findings(findings),
        "part_scores": part_scores,
        "part_summary": part_summary,
        "seconds": round(time.time() - t_rv, 1),
    }
    save(f"{slug}-review.json", review)
    save(f"{slug}-review-summary.json", result["review"])
    log(f"{slug}: review done score={result['review']['quality_score']} findings={len(findings)}")


def _suggestion_brief(suggestion: dict[str, Any]) -> dict[str, Any]:
    return {
        "part": suggestion.get("part") or suggestion.get("part_label"),
        "reason": (suggestion.get("reason") or "")[:400],
        "suggested": (suggestion.get("suggested_text") or "")[:400],
        "legal_basis": (suggestion.get("legal_basis") or "")[:300],
    }


def _recommendation_briefs(recs: list[Any]) -> list[dict[str, Any]]:
    brief: list[dict[str, Any]] = []
    for rec in recs[:10]:
        suggestions = rec.get("suggestions") or []
        brief.append(
            {
                "section": rec.get("section_key"),
                "label": rec.get("section_label"),
                "source_count": rec.get("source_count"),
                "source_note": rec.get("source_count_note"),
                "suggestions": [_suggestion_brief(item) for item in suggestions[:4]],
            }
        )
    return brief


def _record_analyze(slug: str, full_text: str, result: dict[str, Any]) -> None:
    log(f"{slug}: analyze")
    t_an = time.time()
    analyze = unwrap(
        http_json("POST", "/analyze", {"text": full_text[:199000]}, timeout=TIMEOUT_ANALYZE)
    )
    recs = analyze.get("recommendations") or []
    result["analyze"] = {
        "ok": True,
        "summary": (analyze.get("summary") or "")[:2000],
        "legal": summarize_part(analyze.get("legal")),
        "lock_in": summarize_part(analyze.get("lock_in")),
        "project": summarize_part(analyze.get("project")),
        "recommendations": _recommendation_briefs(recs),
        "prefer_legal_corpus_note": analyze.get("prefer_legal_corpus_note"),
        "seconds": round(time.time() - t_an, 1),
    }
    save(f"{slug}-analyze.json", analyze)
    save(f"{slug}-analyze-summary.json", result["analyze"])
    log(f"{slug}: analyze done")


def run_review_analyze(slug: str, path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "slug": slug,
        "filename": path.name,
        "bytes": path.stat().st_size,
        "path": str(path),
    }
    t0 = time.time()
    try:
        full_text, job_id = _full_extract_text(slug, path, result)
        _record_review(slug, job_id, result)
        _record_analyze(slug, full_text, result)
    except Exception as exc:
        result["error"] = str(exc)[:2000]
        result["traceback"] = traceback.format_exc()[-2000:]
        log(f"{slug}: FAILED {exc}")
    result["total_seconds"] = round(time.time() - t0, 1)
    save(f"{slug}-run.json", result)
    return result


def draft_source_files() -> list[Path]:
    folder = REPO / "โครงการจัดจ้างพัฒนาระบบฐานข้อมูลงานติดตามและประเมินผลด้านเศรษฐกิจการเกษตร"
    wanted = [
        "bidding noltice.pdf",
        "annoudoc_0701500006_68109289987.pdf",
        "doc_0701500006_68109289987.pdf",
        "Document Part1.pdf",
        "Document Part2.pdf",
        "Attach_TOR_1.pdf",
        "definition_1.pdf",
        "definition_2.pdf",
        "action_plan.xlsx",
    ]
    files: list[Path] = []
    for name in wanted:
        path = folder / name
        if path.exists():
            files.append(path)
    return files


def fill_missing_facts(project_id: str, coverage: dict[str, Any], pack_text: str) -> list[str]:
    """Answer remaining fact slots from announcement text via intake chat."""
    filled: list[str] = []
    table = coverage.get("coverage") if isinstance(coverage, dict) else coverage
    rows = table if isinstance(table, list) else []
    missing = [
        row.get("key") or row.get("slot_key")
        for row in rows
        if isinstance(row, dict)
        and row.get("status") not in {"filled", "ok"}
        and (row.get("required") or row.get("fact") or row.get("kind") == "fact")
    ]
    if not missing:
        # try structured coverage
        missing = []
    try:
        unwrap(http_json("POST", f"/projects/{project_id}/intake/open-qa", {}, timeout=120))
    except Exception as exc:
        log(f"draft: open-qa skipped {exc}")
        return filled
    for _ in range(12):
        nxt = unwrap(http_json("GET", f"/projects/{project_id}/intake/qa-next", timeout=60))
        slot = nxt.get("current_slot")
        if not slot or nxt.get("all_fact_filled"):
            break
        label = nxt.get("slot_label") or slot
        question = nxt.get("question") or ""
        snippet = pack_text[:3500]
        answer = (
            f"จากเอกสารประกาศจัดจ้างและร่าง TOR ของโครงการ"
            f"พัฒนาระบบฐานข้อมูลงานติดตามและประเมินผลด้านเศรษฐกิจการเกษตร: {label}. "
            f"{question}\n\nข้อความจากเอกสาร:\n{snippet}"
        )
        try:
            read_sse(
                f"/projects/{project_id}/intake/chat",
                {"content": answer, "search_scope": "project", "attach_legal_reference": False},
                timeout=600,
            )
            filled.append(str(slot))
            log(f"draft: filled slot {slot}")
        except Exception as exc:
            log(f"draft: chat fill {slot} failed {exc}")
            break
    return filled


def _create_draft_project(result: dict[str, Any]) -> Any:
    log("draft: create project")
    created = unwrap(
        http_json(
            "POST",
            "/projects",
            {
                "name": "จ้างพัฒนาระบบฐานข้อมูลงานติดตามและประเมินผลด้านเศรษฐกิจการเกษตร",
                "ministry": "สำนักงานเศรษฐกิจการเกษตร",
                "budget": 15000000,
                "project_type": "hire_develop",
            },
            timeout=60,
        )
    )
    project_id = created.get("id")
    result["project_id"] = project_id
    result["project"] = {
        "name": created.get("name"),
        "ministry": created.get("ministry"),
        "budget": created.get("budget"),
        "project_type": created.get("project_type"),
    }
    save("draft-project.json", created)
    return project_id


def _upload_draft_files(project_id: Any, files: list[Path], result: dict[str, Any]) -> None:
    uploaded: list[str] = []
    for path in files:
        log(f"draft: upload {path.name} ({path.stat().st_size} bytes)")
        try:
            up = unwrap(
                http_multipart(
                    f"/projects/{project_id}/intake/upload",
                    [("files", path)],
                    timeout=TIMEOUT_EXTRACT,
                    field="files",
                )
            )
            uploaded.extend(up.get("files") or [path.name])
        except Exception as exc:
            log(f"draft: upload failed {path.name}: {exc}")
            result.setdefault("upload_errors", []).append(
                {"file": path.name, "error": str(exc)[:500]}
            )
    result["uploaded"] = uploaded


def _slot_summaries(slot_map: dict[str, Any]) -> tuple[list[str], dict[str, str]]:
    filled = [
        key
        for key, val in slot_map.items()
        if isinstance(val, dict) and val.get("status") == "filled"
    ]
    preview = {
        key: (val.get("content") or "")[:400]
        for key, val in slot_map.items()
        if isinstance(val, dict) and (val.get("content") or "").strip()
    }
    return filled, preview


def _coverage_pack_text(cov: dict[str, Any]) -> str:
    pack_bits: list[str] = []
    for key, val in (cov.get("slot_map") or {}).items():
        if isinstance(val, dict) and val.get("content"):
            pack_bits.append(f"{key}: {val['content']}")
    return "\n".join(pack_bits)[:20000]


def _analyze_draft_intake(project_id: str, result: dict[str, Any]) -> tuple[dict[str, Any], str]:
    log("draft: intake analyze (LLM)")
    t_an = time.time()
    analyzed = unwrap(
        http_json("POST", f"/projects/{project_id}/intake/analyze", {}, timeout=TIMEOUT_INTAKE)
    )
    result["intake_analyze_seconds"] = round(time.time() - t_an, 1)
    result["coverage"] = analyzed.get("coverage")
    result["analyzed"] = analyzed.get("analyzed")
    result["gap_questions"] = analyzed.get("gap_questions")
    slot_map = analyzed.get("slot_map") or {}
    filled, preview = _slot_summaries(slot_map)
    result["filled_slots"] = filled
    result["slot_preview"] = preview
    save("draft-intake-analyze.json", analyzed)
    try:
        refs = unwrap(
            http_json("POST", f"/projects/{project_id}/intake/fill-references", {}, timeout=600)
        )
        result["fill_references"] = refs.get("filled_keys")
    except Exception as exc:
        result["fill_references_error"] = str(exc)[:500]
    cov = unwrap(http_json("GET", f"/projects/{project_id}/intake/coverage", timeout=60))
    result["coverage_after_refs"] = cov.get("coverage")
    return cov, _coverage_pack_text(cov)


def _post_confirm_ready(project_id: str) -> None:
    http_json(
        "POST",
        f"/projects/{project_id}/intake/confirm-ready",
        {"confirm": True},
        timeout=60,
    )


def _confirm_draft_ready(
    project_id: str,
    cov: dict[str, Any],
    pack_text: str,
    result: dict[str, Any],
) -> bool:
    try:
        _post_confirm_ready(project_id)
        result["confirm_ready"] = True
    except Exception as exc:
        result["confirm_ready"] = False
        result["confirm_ready_error"] = str(exc)[:800]
        log(f"draft: confirm-ready failed, trying fact fill: {exc}")
        result["chat_filled_slots"] = fill_missing_facts(project_id, cov, pack_text)
        try:
            _post_confirm_ready(project_id)
            result["confirm_ready"] = True
            result["confirm_ready_error"] = None
        except Exception as exc2:
            result["confirm_ready_error"] = str(exc2)[:800]
    return bool(result.get("confirm_ready"))


def _open_draft(project_id: str, result: dict[str, Any]) -> None:
    try:
        http_json("POST", f"/projects/{project_id}/intake/open-draft", {}, timeout=60)
    except Exception as exc:
        result["open_draft_error"] = str(exc)[:400]


def _poll_draft_status(project_id: str) -> dict[str, Any]:
    status: dict[str, Any] = {}
    for _ in range(40):
        try:
            status = unwrap(http_json("GET", f"/projects/{project_id}/draft-chat/status", timeout=60))
            log(
                f"draft: status {status.get('drafted_count')}/{status.get('total')} "
                f"job={status.get('job_status')} all={status.get('all_drafted')}"
            )
            if status.get("all_drafted") or status.get("job_status") in {"done", "failed", "error"}:
                break
        except Exception as exc:
            log(f"draft: status poll {exc}")
        time.sleep(30)
    return status


def _compose_draft(project_id: str, result: dict[str, Any]) -> None:
    log("draft: start compose SSE")
    t_dr = time.time()
    events: list[str] = []
    try:
        events = read_sse(
            f"/projects/{project_id}/draft-chat/start",
            {},
            timeout=TIMEOUT_DRAFT,
        )
    except Exception as exc:
        result["draft_stream_error"] = str(exc)[:800]
        log(f"draft: stream ended/errored {exc}")
    result["draft_stream_seconds"] = round(time.time() - t_dr, 1)
    result["sse_event_count"] = len(events)
    save("draft-sse-head.txt", "\n\n".join(events[:40]))
    status = _poll_draft_status(project_id)
    result["draft_status"] = status
    save("draft-status.json", status)


def _one_section_piece(sec: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    summaries: list[dict[str, Any]] = []
    parts: list[str] = []
    key = sec.get("key") or sec.get("section_key")
    title = sec.get("title") or ""
    content = sec.get("content") or ""
    summaries.append(
        {
            "key": key,
            "title": title,
            "filled": sec.get("filled"),
            "chars": len(content),
            "head": content[:500],
        }
    )
    if content:
        parts.append(f"# {key} {title}\n\n{content}\n")
    for sub in sec.get("subs") or []:
        sub_content = sub.get("content") or ""
        summaries.append(
            {
                "key": sub.get("key") or sub.get("sub_key"),
                "title": sub.get("title"),
                "filled": sub.get("filled"),
                "chars": len(sub_content),
                "head": sub_content[:400],
            }
        )
        if sub_content:
            parts.append(f"## {sub.get('key')} {sub.get('title')}\n\n{sub_content}\n")
    return summaries, parts


def _save_draft_sections(project_id: str, result: dict[str, Any]) -> None:
    sections = unwrap(http_json("GET", f"/projects/{project_id}/sections", timeout=60))
    save("draft-sections.json", sections)
    summaries: list[dict[str, Any]] = []
    parts: list[str] = []
    for sec in sections.get("sections") or []:
        rows, chunks = _one_section_piece(sec)
        summaries.extend(rows)
        parts.extend(chunks)
    result["sections"] = summaries
    draft_path = save("draft-tor.md", "\n".join(parts))
    result["draft_md"] = str(draft_path)
    result["ok"] = bool(parts)


def _abort_draft(result: dict[str, Any], message: str, started: float) -> dict[str, Any]:
    result["error"] = message
    result["seconds"] = round(time.time() - started, 1)
    save(DRAFT_RUN_JSON, result)
    return result


def run_draft() -> dict[str, Any]:
    result: dict[str, Any] = {"ok": False}
    t0 = time.time()
    files = draft_source_files()
    result["source_files"] = [{"name": p.name, "bytes": p.stat().st_size} for p in files]
    if not files:
        result["error"] = "no draft source files"
        save(DRAFT_RUN_JSON, result)
        return result
    try:
        project_id = _create_draft_project(result)
        _upload_draft_files(project_id, files, result)
        cov, pack_text = _analyze_draft_intake(project_id, result)
        if not _confirm_draft_ready(project_id, cov, pack_text, result):
            return _abort_draft(result, "cannot confirm-ready; skip compose", t0)
        _open_draft(project_id, result)
        _compose_draft(project_id, result)
        _save_draft_sections(project_id, result)
        result["seconds"] = round(time.time() - t0, 1)
    except Exception as exc:
        result["error"] = str(exc)[:2000]
        result["traceback"] = traceback.format_exc()[-2000:]
        result["seconds"] = round(time.time() - t0, 1)
        log(f"draft: FAILED {exc}")
    save(DRAFT_RUN_JSON, result)
    return result


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {"started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    docs = discover_docs()
    manifest["discovered"] = {k: {"path": str(v), "bytes": v.stat().st_size, "name": v.name} for k, v in docs.items()}
    draft_files = draft_source_files()
    manifest["draft_sources"] = [{"path": str(p), "bytes": p.stat().st_size, "name": p.name} for p in draft_files]
    save("00-discovered.json", manifest)
    log(f"discovered docs={list(docs)} draft_files={len(draft_files)}")

    login()
    log("logged in")

    jobs = []
    if "skk" in docs:
        jobs.append(("skk", docs["skk"]))
    if "amazon" in docs:
        jobs.append(("amazon-quick", docs["amazon"]))
    if "local" in docs:
        jobs.append(("local", docs["local"]))

    runs: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        draft_fut = pool.submit(run_draft)
        futs = {pool.submit(run_review_analyze, slug, path): slug for slug, path in jobs}
        futs[draft_fut] = "draft"
        for fut in as_completed(futs):
            slug = futs[fut]
            try:
                runs[slug] = fut.result()
            except Exception as exc:
                runs[slug] = {"error": str(exc), "traceback": traceback.format_exc()[-1500:]}
            save("00-progress.json", {k: {"ok": not v.get("error"), "keys": list(v)} for k, v in runs.items()})

    manifest["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    manifest["runs"] = {k: {kk: vv for kk, vv in v.items() if kk != "traceback"} for k, v in runs.items()}
    save("00-manifest.json", manifest)
    log("all done")


if __name__ == "__main__":
    main()
