FROM python:3.12-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
RUN pip install --no-cache-dir uv==0.8.22
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
COPY README.md ./
RUN uv sync --locked --no-dev

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends blender ffmpeg fonts-dejavu-core tini \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app src ./src
COPY --chown=app:app assets ./assets
COPY --chown=app:app VERSION ./VERSION
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app alembic.ini ./
ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH=/app/src DATA_DIR=/data
USER app
ENTRYPOINT ["tini", "--", "media-bot"]
CMD ["bot"]
