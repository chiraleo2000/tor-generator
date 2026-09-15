#!/usr/bin/env bash
# Update the app already running on this EC2.
# Does not edit .env, does not ingest the knowledge base, does not print secrets.
#
# Usage (on the EC2, as the user who owns the repo):
#   bash app/infra/pn-ec2/scripts/deploy.sh              # origin/main
#   bash app/infra/pn-ec2/scripts/deploy.sh <git-sha>
#
# Auto path: GitHub Actions calls /usr/local/bin/tor-pn-deploy via SSM.
# See app/infra/pn-ec2/ci/github-ec2-deploy.yml.example
set -euo pipefail

APP_ROOT="${PN_APP_ROOT:-${HOME}/tor-app}"
TARGET="${1:-}"
LOCK_FILE="${APP_ROOT}/.deploy.lock"

if [[ -n "$TARGET" && ! "$TARGET" =~ ^[0-9a-fA-F]{7,40}$ ]]; then
  echo "Refuse: target must be a git SHA, got: ${TARGET}"
  exit 2
fi

if [[ ! -d "${APP_ROOT}/.git" ]]; then
  echo "Refuse: ${APP_ROOT} is not a git checkout. Clone once by hand first."
  exit 2
fi
if [[ ! -f "${APP_ROOT}/app/infra/pn-ec2/.env" ]]; then
  echo "Refuse: missing ${APP_ROOT}/app/infra/pn-ec2/.env"
  exit 2
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "Another deploy is already running on this machine."
  exit 2
fi

cd "$APP_ROOT"
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "Refuse: tracked files were edited on the server. Commit elsewhere or reset by hand."
  exit 2
fi

PREV="$(git rev-parse HEAD)"
echo "Current ${PREV}"
git fetch --prune origin

if [[ -n "$TARGET" ]]; then
  git checkout --detach "$TARGET"
else
  git checkout --detach origin/main
fi
NEW="$(git rev-parse HEAD)"
echo "Deploying ${NEW}"

COMPOSE_DIR="${APP_ROOT}/app/infra/pn-ec2"
cd "$COMPOSE_DIR"
PROFILE=()
if [[ -f nginx/pn.conf ]]; then
  PROFILE=(--profile with-nginx)
fi

compose_up() {
  docker compose -f docker-compose.pn.yml "${PROFILE[@]}" --env-file .env up -d --build
}

wait_healthy() {
  local i
  for i in $(seq 1 36); do
    if docker compose -f docker-compose.pn.yml --env-file .env exec -T backend \
      python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:4000/api/v1/health', timeout=10).read()"; then
      echo
      echo "Healthy at ${NEW}"
      return 0
    fi
    echo "Waiting for API health (${i}/36)..."
    sleep 10
  done
  return 1
}

if ! compose_up || ! wait_healthy; then
  echo "Deploy failed. Rolling back to ${PREV}"
  git -C "$APP_ROOT" checkout --detach "$PREV"
  compose_up || echo "Rollback compose failed — check docker logs before the next attempt."
  exit 1
fi
