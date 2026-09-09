#!/usr/bin/env bash
# Sync local dataset tree to S3 using values from app/infra/pn-ec2/.env
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ ! -f .env ]]; then
  echo "Missing .env"
  exit 1
fi
set -a
# shellcheck disable=SC1091
source .env
set +a

BUCKET="${PN_S3_BUCKET:?set PN_S3_BUCKET in .env}"
PREFIX="${PN_S3_SOURCES_PREFIX:-rags/procurement-th/sources/}"
LOCAL="${PN_DATASET_LOCAL_PATH:-}"
REGION="${AWS_REGION:-ap-southeast-1}"

if [[ -z "$LOCAL" || ! -d "$LOCAL" ]]; then
  echo "Set PN_DATASET_LOCAL_PATH to a folder of PDFs (or extracted dataset rag-pdfs/)"
  exit 1
fi

echo "Sync $LOCAL -> s3://$BUCKET/$PREFIX (region=$REGION)"
aws s3 sync "$LOCAL" "s3://${BUCKET}/${PREFIX}" --region "$REGION"
echo "Done. Verify with: aws s3 ls s3://${BUCKET}/${PREFIX}"
