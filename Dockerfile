FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    MIMO_HOST=0.0.0.0 \
    MIMO_PORT=8000

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.9.8 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --locked --no-dev

EXPOSE 8000

CMD ["uv", "run", "--no-dev", "mimo-openai-proxy"]
