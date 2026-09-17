#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ $# -gt 1 || ( $# -eq 1 && "$1" != '--setup' && "$1" != '--help' ) ]]; then
  echo '사용법: ./start.sh [--setup | --help]'
  exit 1
fi
if [[ "${1:-}" == '--help' ]]; then
  echo '사용법: ./start.sh [--setup]'
  echo '필수: Node.js 24+, npm, uv, Docker CLI와 실행 중인 Docker 엔진'
  echo '처음에는 .env.example을 .env로 복사하고 AI_API_KEY와 AI_MODEL을 설정하세요.'
  echo '의존성과 실행 이미지는 자동으로 준비합니다. --setup은 실행 이미지를 다시 빌드합니다.'
  exit 0
fi
for tool in node npm uv docker; do
  if ! command -v "$tool" >/dev/null; then
    echo "필수 도구가 없습니다: $tool. README.md의 처음 실행하기를 확인해주세요."
    exit 1
  fi
done
if ! node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 24 ? 0 : 1)'; then
  echo 'Node.js 24 이상이 필요합니다.'
  exit 1
fi
if [[ ! -f .env ]]; then
  echo '설정 파일이 없습니다. cp .env.example .env 후 AI_API_KEY와 AI_MODEL을 입력해주세요.'
  echo 'AI 키 없이 예제만 사용하려면 빈 설정 파일로 시작할 수 있습니다.'
  exit 1
fi
export UV_ENV_FILE="$PWD/.env"
# Refuse before app initialization, which marks interrupted jobs and cleans runner containers.
node <<'JS'
const server = require('node:net').createServer();
server.once('error', () => {
  console.error('127.0.0.1:8010 포트를 사용할 수 없습니다. 이미 실행 중인 서버가 있다면 먼저 종료해주세요.');
  process.exitCode = 1;
});
server.listen(8010, '127.0.0.1', () => server.close());
JS
if [[ ! -x .venv/bin/python ]]; then uv venv --python 3.12 .venv; fi
uv pip sync --python .venv/bin/python requirements.txt
if [[ -z "${DOCKER_CONTEXT:-}" ]] && docker context inspect colima-code-trainer >/dev/null 2>&1; then
  export DOCKER_CONTEXT=colima-code-trainer
  if command -v colima >/dev/null; then colima start code-trainer --activate=false; fi
fi
if ! docker version --format '{{.Server.Version}}' >/dev/null 2>&1; then
  if [[ "$(uname)" == 'Darwin' && -d /Applications/Docker.app && "${DOCKER_CONTEXT:-}" != colima-* ]]; then open -a Docker; fi
  echo 'Docker 엔진 연결을 기다립니다…'
  for attempt in {1..30}; do
    if docker version --format '{{.Server.Version}}' >/dev/null 2>&1; then break; fi
    if [[ "$attempt" == 30 ]]; then echo 'Docker 엔진에 연결하지 못했습니다. Docker Desktop 또는 Docker Engine을 시작하고 다시 실행해주세요.'; exit 1; fi
    sleep 2
  done
fi
runner_image=$(uv run --no-project .venv/bin/python -c 'from backend.runner import IMAGE; print(IMAGE)')
if [[ "${1:-}" == '--setup' ]] || ! docker image inspect "$runner_image" >/dev/null 2>&1; then
  echo '다섯 언어의 코드 실행 이미지를 준비합니다. 최초 빌드는 시간이 걸릴 수 있습니다.'
  if [[ "${DOCKER_CONTEXT:-}" == colima-code-trainer && -x /Applications/Docker.app/Contents/Resources/cli-plugins/docker-buildx ]]; then
    # Docker Desktop's credential helper can hang when its engine is broken.
    # These public images need no credentials; isolate only this build's CLI config.
    mkdir -p data/docker-cli/cli-plugins
    ln -sf /Applications/Docker.app/Contents/Resources/cli-plugins/docker-buildx data/docker-cli/cli-plugins/docker-buildx
    endpoint=$(docker context inspect colima-code-trainer --format '{{.Endpoints.docker.Host}}')
    docker --config "$PWD/data/docker-cli" --host "$endpoint" build -t "$runner_image" sandbox
  else
    docker build -t "$runner_image" sandbox
  fi
fi
# Install from the lockfile on every start so git pull cannot leave stale dependencies.
(cd frontend && npm ci)
(cd frontend && npm run build)
echo 'Code Trainer: http://127.0.0.1:8010'
exec uv run --no-project .venv/bin/python -m uvicorn backend.api:app --host 127.0.0.1 --port 8010 --no-access-log --workers 1
