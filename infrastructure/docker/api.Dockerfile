FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY apps ./apps
COPY services ./services
COPY demo ./demo
COPY db ./db
COPY analytics ./analytics
COPY tools ./tools
COPY alembic.ini ./
RUN useradd --create-home --uid 10001 revpilot && mkdir -p /app/.local && chown -R revpilot:revpilot /app
USER revpilot
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8010
CMD ["uvicorn","apps.api.main:app","--host","0.0.0.0","--port","8010"]
