#!/bin/bash
# Pair with mcr.microsoft.com/playwright:v1.62.1-jammy (package-lock Playwright 1.62.1).
set -euo pipefail
cd /repo/app/frontend
need_ci=0
if [ ! -d node_modules/@playwright/test ]; then
  need_ci=1
elif ! node -e "require('@playwright/test')" >/dev/null 2>&1; then
  # Host Windows node_modules is not loadable in this Linux image.
  need_ci=1
fi
if [ "$need_ci" = 1 ]; then
  npm ci --ignore-scripts
fi
export E2E="${E2E:-1}"
export HEADED="${HEADED:-1}"
export CI="${CI:-1}"
export HOME="${HOME:-/tmp}"
export DISPLAY="${DISPLAY:-:99}"
# xvfb-run's wait-for-USR1 hangs in this image; start Xvfb ourselves.
if [ "${HEADED}" = "1" ] && [ -z "${SKIP_XVFB:-}" ]; then
  Xvfb "$DISPLAY" -screen 0 1440x900x24 -nolisten tcp >/tmp/xvfb.log 2>&1 &
  sleep 0.4
fi
exec npx playwright test "$@"
