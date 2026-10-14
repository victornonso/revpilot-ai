# Metric catalogue

Definitions used by the API and metric detail drawers. Reporting periods are
start-inclusive and end-exclusive. Financial amounts use GBP in the demo.

| ID | Display | Unit | Definition |
| --- | --- | --- | --- |
| invoiced | Invoiced revenue | GBP | Sum of invoice face amounts issued in the reporting period; not cash or recognised revenue. |
| cash | Cash collected | GBP | Sum of payments recorded in the reporting period. |
| mrr | MRR | GBP/month | Monthly subscription amounts active at the end of the reporting period. |
| arr | ARR | GBP/year | Twelve times end-of-period MRR; annualised run rate, not recognised revenue. |
| pipeline | Open pipeline | GBP | Open opportunities created before period end; a current-state view, not a historical snapshot. |
| weighted | Stage-weighted pipeline | GBP | Open amount times documented stage heuristic: 15%, 35%, 55%, 75%. Not a calibrated ML probability. |
| win_rate | Win rate | % | Won divided by Won plus Lost opportunities closed in the period. |
| sales_cycle | Sales cycle | days | Mean creation-to-close duration of won opportunities in the period. |
| active | Active customers | accounts | Distinct accounts with a subscription active at period end. |
| churn | Logo churn | % | Accounts active at period start with no active subscription at period end, divided by starting active accounts. |
| overdue | Overdue balance | GBP | Positive unpaid invoice balances with due date before period end; a current payment-state balance. |
| at_risk | Stalled pipeline | GBP | Open opportunities with more than 30 days in their present stage. |

## Implementation and permissions

SQL implementations: apps/api/analytics.py; base views: db/sql/schema.sql;
dbt definitions: analytics/dbt/models. Query access is scoped to the verified
organisation. Forced RLS applies to both base tables and security-invoker views.
Missing values remain unavailable, while genuine zeros are preserved. Financial
KPI arithmetic currently includes API composition of SQL totals; consolidating
all metric formulas into dbt-governed SQL remains acceptance work.

The period target is company-wide. Segment target attainment is unavailable
instead of comparing a segment against a company-wide target. Current pipeline
and unpaid-balance views are explicitly current-state views; they must not be
presented as historical snapshots. Monthly charts include partial current-month
coverage and should not be interpreted as complete-month growth comparisons.
