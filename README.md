# RevPilot AI

**From revenue intelligence to intelligent action.**

A revenue operations workspace connecting PostgreSQL analytics, predictive
benchmarks, governed investigations and approval-controlled workflows. Nine
screens share a responsive design system and real backend services.

The local demonstration uses **Northstar Cloud**, a deterministic synthetic B2B
company. Its results are demonstration evidence, not actual company performance.

## Development

Python 3.12+, Node.js 24, PostgreSQL 18 and Temporal are required. Docker Compose
definitions are included; native Windows verification uses an isolated PostgreSQL
cluster and the official Temporal development server. See
[deployment](docs/deployment.md) and [implementation status](docs/implementation-status.md).

```powershell
uv sync --frozen
uv run python tools/bootstrap_database.py
uv run alembic upgrade head
uv run python -m demo.generator.seed
uv run python -m tools.build_marts
uv run python -m services.intelligence.train
uv run uvicorn apps.api.main:app --host 127.0.0.1 --port 8010
```

In another terminal:

```powershell
cd apps/web
npm ci
npm run dev
```

Local workspace: `http://127.0.0.1:3010/overview`. API docs:
`http://127.0.0.1:8010/docs`. Application and migration credentials are separate;
the bootstrap writes them only to ignored `.env`. Never commit runtime data.

## Product

- Overview: invoicing, collections, recurring revenue and pipeline context.
- Pipeline: stage progression, ageing, searchable opportunities and detail history.
- Forecasting: registered models, measured backtests and saved sensitivity scenarios.
- Customers: account directory, recurring revenue and Customer 360.
- Analyst: metric catalogue and bounded, evidence-linked provider orchestration.
- Automations: rule simulation, stored definitions, exact-payload approvals and Temporal execution.
- Recovery: documented exposure/age prioritisation and follow-up proposals.
- Reports: persisted analytical snapshots with actual CSV and PDF downloads.
- Operations: real ingestion, import, quality and model-training records.

LLM and external provider credentials are optional. Unconfigured services show
explicit states. No fake AI answers or external delivery confirmations are used.

## Verification

```powershell
uv run pytest -q
uv run python -m tools.build_marts
cd apps/web
npm run build
npm run typecheck
```

[Interface specification](docs/interface-specification.md) defines the design
gate. [Frontend verification](docs/frontend-verification.md) records actual
browser checks and screenshots at 1440, 768 and 390 pixels. The full master brief
remains the acceptance target; the status document identifies unfinished work.
