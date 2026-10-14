# Data dictionary

| Domain | Records | Grain / purpose |
| --- | --- | --- |
| identity.organisation | Organisation UUID, name, demo flag | Tenant boundary |
| core.sales_rep | UUID, organisation, name, region | Commercial owner |
| core.account | UUID, organisation, segment, region, owner, acquisition time | Account |
| core.contact | UUID, organisation, account, name, synthetic email | Contact |
| core.opportunity | UUID, account, owner, stage, amount, currency, creation/close/stage dates, source, loss reason | Opportunity current state |
| core.opportunity_stage_history | UUID, opportunity, from/to stage, occurrence time | Recorded transition |
| core.activity | UUID, opportunity, type, occurrence time | Activity |
| finance.subscription | UUID, account, monthly amount, currency, start/end dates | Subscription |
| finance.invoice | UUID, account/subscription, amount, currency, issue/due dates | Invoice |
| finance.invoice_line | UUID, invoice, amount, description | Invoice line |
| finance.payment | UUID, invoice, amount, payment time | Payment |
| finance.credit_note | UUID, invoice, amount, issued time | Credit note; not demo-seeded |
| finance.revenue_entry | UUID, invoice, amount, recognition time, accounting source | Authoritative accounting entry; not demo-seeded |
| planning.revenue_target | Organisation, month, amount, currency | Monthly company target |
| ml.* | Typed tenant/UUID/state/version/time plus structured JSONB payload | Features, models, predictions, evaluations |
| automation.* | Tenant/UUID/state/version/time/idempotency key plus payload | Rules, proposals, approvals, executions, audit |
| integration.*, raw.* | Tenant identity, state, time, payload | Provider/import provenance |
| ai.* | Tenant identity, state, time, payload | Conversations, messages, tools, evidence |
| ops.* | Tenant identity, state, time, payload | Actual jobs and quality checks |
| reporting.* | Tenant identity, state, version, time, payload | Snapshot reports, saved-view/schedule storage |

Financial values use NUMERIC(18,2), with GBP as the synthetic-company currency.
Canonical datetimes use timestamptz. UI presentation uses Europe/London; CSV/API
preserve canonical machine-readable timestamps. Nonnegative amounts and primary
relationships are checked by PostgreSQL constraints. Runtime schema details are
defined in db/sql/schema.sql and Alembic revisions.
