# aad-python — one image, many commands (`python -m runtime <service>`).
# Non-root, no secrets baked in. Compose mounts data/ and sets a read-only root fs.
FROM python:3.11-slim-bookworm

RUN useradd --system --uid 10001 --create-home --home-dir /app aad \
    && mkdir -p /app/data/state /tmp \
    && chown -R aad:aad /app /tmp

WORKDIR /app
COPY --chown=aad:aad packages/contracts packages/contracts
COPY --chown=aad:aad packages/events packages/events
COPY --chown=aad:aad packages/runtime packages/runtime
COPY --chown=aad:aad scripts/ci/install.sh scripts/ci/install.sh
COPY --chown=aad:aad requirements requirements

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir \
        -e packages/contracts -e packages/events -e packages/runtime \
    && rm -rf /root/.cache /home/aad/.cache

USER aad
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 AAD_STATE_DIR=/app/data/state
# Replay default: no credentials. Live-data profile is a later ticket on the user box.
CMD ["python", "-m", "runtime", "engine", "--role", "all", "--mode", "replay"]
