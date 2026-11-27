FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/
WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY engine ./engine
COPY api ./api

RUN uv sync --frozen --no-dev --package layersight-api

EXPOSE 8000
CMD ["uv", "run", "--no-dev", "--package", "layersight-api", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
