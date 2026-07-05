#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/stuckydev/changelogger.git}"
INSTALL_DIR="${INSTALL_DIR:-${HOME}/changelogger}"
PORT="${PORT:-47173}"

if docker compose version >/dev/null 2>&1; then
  DC=(docker compose)
elif docker-compose version >/dev/null 2>&1; then
  DC=(docker-compose)
else
  echo "error: docker compose is not installed" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "error: docker daemon is not reachable for ${USER}" >&2
  exit 1
fi

if [[ ! -d "${INSTALL_DIR}/.git" ]]; then
  git clone "${REPO_URL}" "${INSTALL_DIR}"
else
  git -C "${INSTALL_DIR}" pull --ff-only
fi

cd "${INSTALL_DIR}"

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

mkdir -p data

UID_VAL="$(id -u)"
GID_VAL="$(id -g)"
if grep -q '^UID=' .env; then
  sed -i "s/^UID=.*/UID=${UID_VAL}/" .env
else
  echo "UID=${UID_VAL}" >> .env
fi
if grep -q '^GID=' .env; then
  sed -i "s/^GID=.*/GID=${GID_VAL}/" .env
else
  echo "GID=${GID_VAL}" >> .env
fi

"${DC[@]}" build
"${DC[@]}" up -d
"${DC[@]}" ps

echo "waiting for health check..."
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    echo "changelogger is up: http://$(hostname -I | awk '{print $1}'):${PORT}"
    exit 0
  fi
  sleep 2
done

echo "error: service did not become healthy on port ${PORT}" >&2
"${DC[@]}" logs --tail=50 changelogger || true
exit 1
