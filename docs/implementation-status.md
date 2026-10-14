# Implementation status / 14 October 2026

The complete master specification remains the acceptance target. This is an
implemented local system under active development, not a completed production release.

| Area | Status | Evidence |
| --- | --- | --- |
| Repository, Python/Next.js monorepo | Implemented | Private GitHub repository; local source |
| Original nine-screen design | Implemented | interface-specification.md |
| PostgreSQL 18, migrations and app RLS | Tested | Isolated database, two revisions, security tests |
| Deterministic demo history | Tested | 2,500 accounts; 6,000 contacts; 8,000 opportunities; 45,000 activities; 1,800 subscriptions; 15,000 invoices; 12,574 payments |
| SQL/dbt analytical foundation | Tested | Four views; five dbt tests; not all required KPI families implemented |
| Nine routed frontend screens | Implemented | All nine query actual FastAPI services |
| Desktop/tablet/mobile review | Tested | 27 screenshots; layout defects identified and corrected; final refresh in progress |
| Pipeline and customer detail | Tested | Actual facts, stage history, activities and invoices |
| Rules, proposals and exact-payload approvals | Tested | Simulation, version/hash checks and replay rejection |
| Temporal internal task execution | Tested | Actual persisted native Temporal execution |
| Eight distinct automation adapters | In progress | UI concepts exist; executable builder currently covers opportunity stage age/value |
| CSV/Excel imports | In progress | Account preview/mapping/transactional loading tested; other entities missing |
| HubSpot/Stripe connectors | In progress | Paginated HTTP clients and webhook signature tests; no live canonical sync |
| Deal/churn model benchmarks | Tested | Time-ordered selection, real measured held-out metrics, registered model artefacts |
| Invoiced-revenue forecast/anomaly screening | Tested | Rolling-origin comparison and stored future predictions |
| Complete production ML services | In progress | Bookings/recurring forecasts, live scoring, drift, lift and rollback remain |
| MLflow tracking | Tested | Local tracking runs, evaluation reports and artefacts |
| AI analytical tool loop | Implemented | Ten governed tools, audit/evidence persistence, bounded provider rounds |
| Gemini connection | Awaiting credentials | Local free-tier configuration prepared; no key configured |
| Live provider answer quality | Unverified | No fabricated responses used |
| OIDC bearer authentication / memberships | Implemented | JWT verification and database membership; browser login still missing |
| Full tenant governance | In progress | Typed operational relationship constraints, per-owner policies and retention remain |
| CSV/PDF report generation | Tested | Actual persisted metric snapshots and downloads |
| Saved views / scheduled report delivery | In progress | Storage exists; builder/scheduler/transport integration unfinished |
| Docker definitions | Prepared | Compose configuration validates; local Docker engine unavailable |
| CI / reproducible browser suite | Prepared | GitHub Actions and 39 Playwright cases; remote run pending |
| Hosting and portfolio case study | Not started | No paid services authorised; no RevPilot deployment claimed |

## Remaining acceptance work

- Complete the missing charts and governed KPI families: NRR/GRR, cohort heatmaps,
  historical pipeline snapshots, stage-conversion/risk scatter, customer health/value.
- Add full entity imports, encrypted provider credentials, incremental canonical
  loading, associations, reconciliation, webhook ingestion and deletion handling.
- Finish typed operational schemas and organisation-scoped foreign keys throughout.
- Wire browser OIDC login, organisation selection, role/owner policies and sessions.
- Add real live batch scoring and feature snapshots, distinct recurring/bookings
  forecasts, explanation/capacity evaluation, drift monitoring and rollback.
- Complete eight distinct automation triggers, versions/edits, cancellation,
  per-tenant worker dispatch, external adapters and measured intervention outcomes.
- Connect an authorised LLM key, verify actual provider tool calling and expand
  structured-answer/adversarial testing; respect the selected provider's terms.
- Complete analytical-view saving, scheduled report generation/delivery and audit.
- Verify complete Docker startup, CI browser results, backups and monitoring.
- Deploy only once application acceptance and suitable infrastructure are verified.

Local services: web 3010; API 8010; PostgreSQL 5544; Temporal 7233. Runtime state
and secrets remain in ignored .local, .env and .env.llm. No paid billing enabled.
