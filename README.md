# RevPilot AI

**From revenue intelligence to intelligent action.**

A revenue operations workspace connecting PostgreSQL analytics, predictive
benchmarks, governed investigations and approval-controlled workflows. Nine
screens share a responsive design system and real backend services.

The local demonstration uses **Northstar Cloud**, a deterministic synthetic B2B
company. Its results are demonstration evidence, not actual company performance.

Built and maintained by [Victor Okeke](https://victorokeke.co.uk/).

## Problem and architecture

Revenue teams need consistent definitions across pipeline, invoicing, collections
and recurring revenue before they can decide what action to take. RevPilot
connects those analytical views to evidence-linked investigations and explicit
approval workflows.

Validated imports and deterministic demonstration records → PostgreSQL 18 →
SQL/dbt analytical views and registered Python models → FastAPI → Next.js.
Analytical tools support the AI analyst; exact-payload proposals connect approved
actions to Temporal workflows.

## Engineering decisions

| Decision | Purpose | Implementation |
|---|---|---|
| Calculate metrics on the server | Keep reporting definitions consistent across screens | PostgreSQL facts and API analytics provide the shared calculation path |
| Scope data access by organisation | Separate tenant records at the database boundary | Transaction-local organisation context, forced row-level security and membership checks |
| Bound model access to analytical tools | Make numerical claims traceable and limit execution scope | Validated tools, persisted evidence IDs and bounded provider rounds rather than arbitrary SQL |
| Persist investigation state | Make provider capacity and transport failures recoverable | Stored run outcomes, retry windows and bounded request handling |
| Approve exact action payloads | Connect approval to the action actually executed | Payload/version checks, replay rejection and durable Temporal execution |
| Evaluate models in time order | Measure performance against later observations | Recorded backtests, registered artefacts and held-out benchmark results |

Gemini is supported through server-side provider configuration. Provider keys
remain outside the frontend. Unconfigured, rate-limited and unavailable providers
have explicit response states; an unavailable answer is not replaced with a
manufactured analytical result.

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

LLM and external provider credentials are optional for exploring the core
workspace. Internal approval flows and external delivery are separate boundaries;
an approved proposal is not evidence that an external message was delivered.

## Verification

```powershell
uv run pytest -q
uv run python -m tools.build_marts
cd apps/web
npm run build
npm run typecheck
```

[Frontend verification](docs/frontend-verification.md) records browser checks
and screenshots at 1440, 768 and 390 pixels. The
[interface specification](docs/interface-specification.md) documents navigation,
component states and responsive behaviour.

## Deployment scope and next stage

RevPilot is an implemented local workspace under active development. Its
demonstration data, provider-backed investigations and internal workflow
execution are separate from a production commercial integration.

The next stage covers browser OIDC login, complete canonical connector sync,
additional automation adapters, live model scoring and production operational
controls. Hosted deployment depends on validating those boundaries and suitable
persistent API, database and Temporal infrastructure. See
[architecture](docs/architecture.md), [deployment](docs/deployment.md) and the
[implementation record](docs/implementation-status.md) for the verified scope.
