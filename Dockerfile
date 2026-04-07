# ──────────────────────────────────────────────
# Stage 1: Build — install deps with UV
# ──────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:0.7-python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY src/ src/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# ──────────────────────────────────────────────
# Stage 2: Runtime — slim image for AgentCore
# ──────────────────────────────────────────────
FROM python:3.12-slim-bookworm

WORKDIR /app

RUN groupadd --gid 1000 agent && \
    useradd --uid 1000 --gid agent --no-create-home agent

COPY --from=builder --chown=agent:agent /app/.venv /app/.venv

COPY --chown=agent:agent prompts/ prompts/
COPY --chown=agent:agent data/faiss_index/ data/faiss_index/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

EXPOSE 8080

USER agent

CMD ["uvicorn", "ai_stock_agent.infrastructure.app:app", "--host", "0.0.0.0", "--port", "8080"]
