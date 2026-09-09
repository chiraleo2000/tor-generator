#!/usr/bin/env bash
# Bootstrap PN stack on EC2 from app/infra/pn-ec2/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Missing .env — run: cp .env.example .env  then edit changeme_* values"
  exit 1
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

if [[ "${PN_S3_BUCKET:-changeme-pn-tor-kb}" == changeme-* ]]; then
  echo "WARN: PN_S3_BUCKET still looks like a placeholder"
fi
if [[ "${JWT_SECRET:-}" == changeme_* ]]; then
  echo "WARN: JWT_SECRET still placeholder"
fi
if [[ "${QUICK_MCP_AUTH_VALUE:-}" == changeme_* ]]; then
  echo "WARN: QUICK_MCP_AUTH_VALUE still placeholder"
fi

if [[ ! -f nginx/pn.conf ]]; then
  cp nginx/pn.conf.example nginx/pn.conf
  echo "Created nginx/pn.conf from example"
fi

mkdir -p nginx/certs
docker compose -f docker-compose.pn.yml --env-file .env up -d --build
echo "OK — compose up. Optional nginx: docker compose -f docker-compose.pn.yml --profile with-nginx --env-file .env up -d"
echo "MCP (host): http://127.0.0.1:${MCP_HOST_PORT:-8767}/mcp"
echo "After TLS: https://${PN_PUBLIC_HOST:-localhost}/mcp"
