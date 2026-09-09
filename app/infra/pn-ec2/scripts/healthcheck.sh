#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
set -a
# shellcheck disable=SC1091
[[ -f .env ]] && source .env
set +a
PORT="${MCP_HOST_PORT:-8767}"
echo "MCP health:"
curl -sf "http://127.0.0.1:${PORT}/health" | head -c 500 || true
echo
echo "Backend (via compose network not required — host port if published):"
curl -sf "http://127.0.0.1:${BACKEND_PORT:-4000}/api/v1/health" | head -c 500 || echo "(backend port not published — check via nginx)"
echo
curl -sf -X POST "http://127.0.0.1:${PORT}/mcp" \
  -H "Content-Type: application/json" \
  -H "${QUICK_MCP_AUTH_HEADER:-Authorization}: ${QUICK_MCP_AUTH_VALUE:-}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | head -c 800 || true
echo
