#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
set -a
[ -f .env ] && . ./.env
set +a
python3 -m uvicorn app.main:app --reload --host "${APP_HOST:-127.0.0.1}" --port "${APP_PORT:-8000}"
