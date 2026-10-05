FROM docker:29-cli@sha256:b1805116a6a86cc591b5d5f60a910a0715cdcc9d18d866ad68b1457ead25c35c AS docker-cli
FROM python:3.12-slim-bookworm@sha256:54c85f3c47607a77f32adec749d3c81d1348bf25833671f512b26a9b6d778cb3 AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt /app/requirements.txt
COPY deploy/requirements.txt /app/deploy/requirements.txt
RUN pip install --no-cache-dir -r /app/deploy/requirements.txt

FROM base AS app
COPY backend /app/backend
COPY scripts/backup.py /app/scripts/backup.py
USER 10001:10001
ENV TRAINER_MODE=server TRAINER_DB=/data/trainer.sqlite3
# No Docker executable, socket, VM-management keys or runner server key in this image.
CMD ["python", "-m", "uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "1", "--no-access-log", "--no-proxy-headers"]

FROM base AS runner
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker
COPY backend/runner.py backend/runner_api.py backend/execution.py backend/schema.py /app/backend/
ENV TRAINER_MODE=local TRAINER_RUNTIME_MANIFEST=/config/runtimes.json
# This container alone mounts the runner VM's Docker socket. Never mount the app VM's socket.
CMD ["python", "-m", "uvicorn", "backend.runner_api:app", "--host", "0.0.0.0", "--port", "8443", "--workers", "1", "--no-access-log", "--no-proxy-headers", "--ssl-keyfile", "/tls/runner.key", "--ssl-certfile", "/tls/runner.crt", "--ssl-ca-certs", "/tls/client-ca.crt", "--ssl-cert-reqs", "2", "--timeout-graceful-shutdown", "90"]
