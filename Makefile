.PHONY: bootstrap api web worker test marts models
bootstrap:
	uv sync --frozen
	uv run python tools/bootstrap_database.py
	uv run alembic upgrade head
	uv run python -m demo.generator.seed
	uv run python -m tools.build_marts
	uv run python -m services.intelligence.train
api:
	uv run uvicorn apps.api.main:app --host 127.0.0.1 --port 8010
web:
	cd apps/web && npm run dev
worker:
	uv run python -m apps.worker.main
test:
	uv run pytest -q
marts:
	uv run python -m tools.build_marts
models:
	uv run python -m services.intelligence.train
