"""Download the mandatory KB PDF tree from S3 for cloud seed jobs.

Usage (ECS one-shot / SSM, task role must read the kb-source bucket):

  export KB_SOURCE_BUCKET=tor-prod-kb-source
  export KB_LOCAL_DIR=/tmp/kb
  python -m app.storage.s3_kb_sync
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path


def download_prefix(bucket: str, prefix: str, dest: Path, client=None) -> int:
    """Copy s3://bucket/prefix objects into dest, preserving relative keys."""
    s3 = client
    if s3 is None:
        import boto3

        s3 = boto3.client("s3")
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents") or []:
            key = obj["Key"]
            if key.endswith("/"):
                continue
            relative = key[len(prefix) :].lstrip("/") if key.startswith(prefix) else key
            if not relative:
                continue
            out = dest / relative
            out.parent.mkdir(parents=True, exist_ok=True)
            s3.download_file(bucket, key, str(out))
            count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync KB PDFs from S3 then seed")
    parser.add_argument("--bucket", default=os.environ.get("KB_SOURCE_BUCKET", ""))
    parser.add_argument("--prefix", default=os.environ.get("KB_SOURCE_PREFIX", "sources/"))
    parser.add_argument("--dest", default=os.environ.get("KB_LOCAL_DIR", "/tmp/kb"))
    parser.add_argument("--sync-only", action="store_true", help="Do not run seed_raw_docs")
    args = parser.parse_args(argv)
    if not args.bucket:
        parser.error("set KB_SOURCE_BUCKET or pass --bucket")

    dest = Path(args.dest)
    n = download_prefix(args.bucket, args.prefix, dest)
    print(f"downloaded {n} objects to {dest}")
    os.environ["KB_SOURCES_ROOT"] = str(dest)
    if args.sync_only:
        return 0

    from app.seed_raw_docs import wipe_and_seed

    asyncio.run(wipe_and_seed())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
