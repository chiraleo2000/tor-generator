"""Build documents/exports/tor-pn-aws-dataset-vX.Y.Z.zip for EC2/S3 PN deploy."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_meta(path: Path, arc: str) -> dict:
    return {
        "arcname": arc,
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
        "rag_group": "procurement-th",
    }


def _collect_pdf_entries(
    raw_dir: Path, kb_dir: Path
) -> tuple[list[tuple[Path, str]], list[dict], list[Path]]:
    pdfs = sorted({*raw_dir.glob("*.pdf"), *raw_dir.glob("*.PDF")}, key=lambda p: p.name.lower())
    entries: list[tuple[Path, str]] = []
    files_meta: list[dict] = []
    for pdf in pdfs:
        arc = f"rag-pdfs/{pdf.name}"
        entries.append((pdf, arc))
        files_meta.append(_file_meta(pdf, arc))
        extract = kb_dir / f"{pdf.stem}_tor_extract.json"
        if extract.is_file():
            earc = f"rag-json-chunks/{extract.name}"
            entries.append((extract, earc))
            files_meta.append(_file_meta(extract, earc))
    return entries, files_meta, pdfs


def _collect_infra_entries(root: Path) -> list[tuple[Path, str]]:
    entries: list[tuple[Path, str]] = []
    quick_dir = root / "app" / "infra" / "quick"
    pn_ec2 = root / "app" / "infra" / "pn-ec2"
    for path in sorted(quick_dir.iterdir()):
        if path.is_file():
            entries.append((path, f"mcp-amazon-quick/{path.name}"))
    if (pn_ec2 / "rag-groups.yaml").is_file():
        entries.append((pn_ec2 / "rag-groups.yaml", "pn/rag-groups.yaml"))
    if (pn_ec2 / ".env.example").is_file():
        entries.append((pn_ec2 / ".env.example", "pn/env.example"))
    if (pn_ec2 / "README.md").is_file():
        entries.append((pn_ec2 / "README.md", "pn/README.md"))
    for doc_name in (
        "33-AWS-PN-CLOUD-MINIMUM-COST-PLAN.md",
        "34-AWS-PN-TOOLS-LIST.md",
        "35-AWS-PN-DEV-AND-DEPLOY.md",
        "32-AMAZON-QUICK.md",
    ):
        doc = root / "Discussions" / doc_name
        if doc.is_file():
            entries.append((doc, f"docs/{doc_name}"))
    mcp_server = root / "app" / "backend" / "app" / "mcp_retrieve_server.py"
    if mcp_server.is_file():
        entries.append((mcp_server, "mcp-pgvector/mcp_retrieve_server.py"))
    return entries


def _write_zip(
    zip_path: Path,
    *,
    manifest: dict,
    version: str,
    built: str,
    pdf_count: int,
    entries: list[tuple[Path, str]],
) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "DATASET_MANIFEST.json",
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )
        lines = [
            f"TOR PN AWS dataset v{version}",
            f"Built: {built}",
            f"PDFs: {pdf_count}",
            "Default rag_group: procurement-th",
            "Embed model: cohere.embed-v4:0 / chunk ~4096",
            "Deploy: app/infra/pn-ec2 (.env.example)",
            "",
        ]
        for src, arc in entries:
            lines.append(f"{src.stat().st_size}\t{arc}")
        zf.writestr("MANIFEST.txt", "\n".join(lines) + "\n")
        for src, arc in entries:
            zf.write(src, arcname=arc)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="0.5.0")
    args = parser.parse_args()
    version = args.version

    root = Path(__file__).resolve().parents[2]
    out_dir = root / "documents" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"tor-pn-aws-dataset-v{version}.zip"

    raw_dir = root / "documents" / "sources" / "การจัดซื้อจัดจ้าง" / "ข้อมูลดิบ"
    kb_dir = root / "documents" / "knowledge-base"
    entries, files_meta, pdfs = _collect_pdf_entries(raw_dir, kb_dir)
    entries.extend(_collect_infra_entries(root))

    built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = {
        "name": "tor-pn-aws-dataset",
        "version": version,
        "built_at_utc": built,
        "rag_group_default": "procurement-th",
        "chunk_target_tokens": 4096,
        "embedding_model": "cohere.embed-v4:0",
        "embedding_dimensions": 1024,
        "s3_sources_prefix": "rags/procurement-th/sources/",
        "deploy_folder": "app/infra/pn-ec2",
        "pdf_count": len(pdfs),
        "files": files_meta,
        "compose_hint": [
            "cd app/infra/pn-ec2 && cp .env.example .env",
            "set PN_DATASET_LOCAL_PATH to extracted rag-pdfs/",
            "bash scripts/sync-dataset-to-s3.sh",
            "docker compose -f docker-compose.pn.yml --env-file .env up -d --build",
        ],
    }
    _write_zip(
        zip_path,
        manifest=manifest,
        version=version,
        built=built,
        pdf_count=len(pdfs),
        entries=entries,
    )
    mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Wrote tor-pn-aws-dataset-v{version}.zip size_MB={mb:.1f}")


if __name__ == "__main__":
    main()
