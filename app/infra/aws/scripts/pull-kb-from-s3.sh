#!/usr/bin/env bash
# One-shot: copy mandatory KB PDFs from S3, then ingest with Titan embeddings.
# Run from an ECS Exec / SSM session inside the VPC (or a Fargate one-shot task).
set -euo pipefail

BUCKET="${KB_SOURCE_BUCKET:?set KB_SOURCE_BUCKET}"
DEST="${KB_LOCAL_DIR:-/tmp/kb}"
PREFIX="${KB_SOURCE_PREFIX:-sources/}"

mkdir -p "$DEST"
aws s3 sync "s3://${BUCKET}/${PREFIX}" "$DEST" --sse aws:kms
# Keep the documents/sources layout (handbook PDF + การจัดซื้อจัดจ้าง/ข้อมูลดิบ)
export KB_SOURCES_ROOT="$DEST"
cd /app
python -m app.seed_raw_docs
