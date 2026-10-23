#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ $# -eq 1 && "$1" == '--help' ]]; then
  echo '사용법: cd backend && ./dev.sh'
  echo '루트 .env와 .venv 사용, API :8010, 코드 변경 시 재시작, 기본 DB: data/dev.sqlite3'
  exit 0
fi
if [[ $# -ne 0 ]]; then
  echo '사용법: ./dev.sh [--help]' >&2
  exit 1
fi
if ! command -v uv >/dev/null || [[ ! -x .venv/bin/python ]]; then
  echo 'uv와 루트 .venv가 필요합니다. 루트에서 uv venv --python 3.12 .venv && uv pip sync --python .venv/bin/python requirements.txt 를 실행하세요.' >&2
  exit 1
fi
if [[ ! -f .env ]]; then
  echo '루트에서 cp .env.example .env 후 설정을 입력해주세요.' >&2
  exit 1
fi
export UV_ENV_FILE="$PWD/.env"
export TRAINER_DB="${TRAINER_DB:-$PWD/data/dev.sqlite3}"
if [[ -z "${DOCKER_CONTEXT:-}" ]] && command -v docker >/dev/null && docker context inspect colima-code-trainer >/dev/null 2>&1; then
  export DOCKER_CONTEXT=colima-code-trainer
fi
# Reject a second server before initialization can interrupt existing jobs.
.venv/bin/python - <<'PY'
import socket
with socket.socket() as server:
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(('127.0.0.1', 8010))
    except OSError:
        raise SystemExit('127.0.0.1:8010 포트를 사용할 수 없습니다. 기존 API 서버를 먼저 종료해주세요.')
PY
exec uv run --no-project .venv/bin/python -m uvicorn backend.api:app \
  --host 127.0.0.1 --port 8010 --no-access-log --reload --reload-dir backend
