#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ $# -eq 1 && "$1" == '--help' ]]; then
  echo '사용법: cd backend && ./dev.sh'
  echo '루트 .env의 AI 설정 사용, API :8011, DB/로그: data/dev/, 실행 VM: code-trainer-dev'
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
# Reject a second server before initialization can interrupt existing jobs.
.venv/bin/python - <<'PY'
import socket
with socket.socket() as server:
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(('127.0.0.1', 8011))
    except OSError:
        raise SystemExit('127.0.0.1:8011 포트를 사용할 수 없습니다. 기존 개발 API 서버를 확인해주세요.')
PY
for tool in docker colima; do
  if ! command -v "$tool" >/dev/null; then
    echo "개발용 코드 실행 환경에 $tool 설치가 필요합니다." >&2
    exit 1
  fi
done
export COLIMA_HOME="$HOME/.colima"
export DOCKER_HOST="unix://$COLIMA_HOME/code-trainer-dev/docker.sock"
export DOCKER_CONFIG="$PWD/data/dev/docker-cli"
unset DOCKER_CONTEXT DOCKER_TLS_VERIFY DOCKER_CERT_PATH
mkdir -p "$DOCKER_CONFIG"
if ! docker info >/dev/null 2>&1; then
  colima start code-trainer-dev --runtime docker --cpus 2 --memory 2 --disk 12 \
    --activate=false --mount none --ssh-agent=false --network-address=false
fi
if ! docker image inspect code-trainer-runner:dev >/dev/null 2>&1; then
  # Public image builds must not depend on the production Docker credential helper.
  if [[ -x /Applications/Docker.app/Contents/Resources/cli-plugins/docker-buildx ]]; then
    mkdir -p "$DOCKER_CONFIG/cli-plugins"
    ln -sf /Applications/Docker.app/Contents/Resources/cli-plugins/docker-buildx "$DOCKER_CONFIG/cli-plugins/docker-buildx"
  fi
  docker build -t code-trainer-runner:dev sandbox
fi
# Apply isolation after dotenv loading while retaining the existing AI settings.
exec uv run --no-project env -u DOCKER_CONTEXT -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH \
  DOCKER_HOST="$DOCKER_HOST" DOCKER_CONFIG="$DOCKER_CONFIG" \
  TRAINER_MODE=local TRAINER_RUNNER_URL= TRAINER_IMAGE=code-trainer-runner:dev \
  TRAINER_DB="$PWD/data/dev/trainer.sqlite3" \
  .venv/bin/python -m uvicorn backend.api:app \
  --host 127.0.0.1 --port 8011 --no-access-log --reload --reload-dir backend
