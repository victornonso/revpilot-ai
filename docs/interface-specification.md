# RevPilot interface specification

Design gate established before frontend implementation. Screens use a shared
information hierarchy, not nine separate dashboard templates. References in the
supplied ZIP guide scope; the application layout, components and charts are original.

## Identity and tokens

Porcelain canvas #F6F7F4, white analytical surfaces, graphite text #101820,
muted text #596674, borders #DCE2E7. Blue #2F6FED marks selection and primary
actions; jade #087D67 indicates favourable movement, amber #9C630B indicates
attention, red #BA3843 indicates failure. Labels accompany semantic colours.
Dark mode: canvas #101820, surface #18232E, text #EDF1F5, muted #A7B5C2,
border #344250. Contrast and focus must be checked in the running application.

Typography: locally served Geist sans and Geist Mono. Page titles 30/36px,
section titles 16/24px, body 14/21px, compact table text 12/18px, metadata
11/16px. Financial values use tabular numerals and two decimal places. IDs and
counts use integers. Dates use explicit UK time with GMT/BST; machine exports
retain canonical UTC timestamps. Spacing scale: 4, 8, 12, 16, 24, 32, 48px.
Borders 1px, radii 6px for controls and 10px for panels. Shadows only for overlays.

## Responsive shell

1440px: fixed 224px graphite rail, 64px top bar, 32px content padding;
remaining width belongs to analytics. 768px: rail becomes 64px icon navigation
with accessible names; content padding 24px, two-column metrics and full-width
charts. 390px: rail becomes a labelled modal navigation drawer; 56px top bar,
16px content padding, two-column compact metrics, one-column charts. Global
filters wrap; search occupies its own row. Tables scroll inside labelled focusable
regions, never widening the viewport. Detail drawers become full-screen on mobile.

Navigation preserves reporting period, segment and query parameters between
screens. Page URL is shareable. Global search searches actual accounts and
opportunities. Organisation selector distinguishes synthetic demonstration from
authenticated organisations. Theme selection persists locally. Notifications show
actual operational records. User/settings actions expose configured state.

## Shared interaction and state contract

Buttons: default, hover, focus, disabled, pending and failure. Primary actions
are blue; destructive actions require an explicit confirmation dialog. Forms
validate before submission and display server errors beside relevant controls.
Loading skeletons reserve layout; empty results explain the current filters and
offer reset; failed queries offer retry; stale results retain their content with
the last successful refresh and a refresh action. No fabricated fallback metrics.
Drawers trap focus, close on Escape and restore focus. Charts have labelled units,
legends and accessible tables. All substantive chart values come from API results.
Reduced motion disables nonessential transitions. Exports explain financial basis.

## Screen specifications

Each screen below has a distinct primary task. Desktop order is also the reading
order on narrow screens. At 768px all 2:1 chart splits become a single column;
the 390px layout keeps the principal action beside or immediately below the title.

### 01 / Overview

Header: Executive intelligence, date range, refresh time, Export report.
Ten compact metric cells in two desktop rows of five; tablet/mobile two per row.
Row one: 2:1 revenue-versus-target chart and revenue-by-segment breakdown.
Row two: equal-width pipeline contribution, regional revenue and retention trend.
Bottom: forecast-versus-target and evidence-linked attention list. Revenue basis
is explicitly invoiced revenue; cash, bookings and recognised revenue remain distinct.
Metric selection opens definition, SQL provenance, unit and comparison context.
Segment chart selection filters the workspace; attention links to recovery.

### 02 / Pipeline

Six metrics, then 2:1 stage funnel and stage ageing. Second row: deal movement,
rep leaderboard and risk scatter. Full-width opportunity table below; filters
include search, stage and owner. Sort, page and filter are backend operations.
Primary action: inspect selected opportunity. Drawer includes actual stage events,
activities, probability provenance and risk factors; create follow-up links to
an approval-controlled proposal. Empty stage history is explicit, never inferred.

### 03 / Forecasting

Six metrics. 2:1 historical/forecast line with interval band and scenario controls.
Second row: target gap, segment contributions and rolling-origin error chart.
Model diagnostics table below. Primary action: recalculate scenario; secondary:
save named scenario. Controls cover win rate, slippage, deal size, churn, expansion
and new business. Values are recalculated by API, not client arithmetic.
Mobile scenario form appears before the resulting chart. Untrained models show
a configuration state, not illustrative prediction curves.

### 04 / Customers

Eight metrics. Cohort heatmap spans two-thirds beside customer health distribution.
Second row: churn trend, concentration and customer value distribution.
Full-width searchable customer table; click an account to open Customer 360.
Drawer joins opportunities, subscriptions, invoices, payments and engagement;
predictions include model/version/date. Primary action: review intervention.
Heatmaps retain cohort labels with internal horizontal scrolling at 390px.

### 05 / Analyst

Desktop three panes: 200px investigations, flexible conversation, 280px evidence.
Tablet conversation plus collapsible evidence; mobile conversation with separate
History/Evidence tabs. Header labels provider configuration and data mode.
Composer remains reachable without covering evidence. Suggested investigations
are buttons that populate the question. Responses separate findings, interpretation,
uncertainty and recommendations. Primary: investigate; secondary: propose action.
No configured provider means an honest setup state and still-available metric
catalogue. Tool calls and evidence are stored server-side. Never fake responses.

### 06 / Automations

Four operational counters. Template library in a three-column desktop grid,
two columns tablet, one column mobile. Editor has trigger, AND/OR conditions,
action, approval policy and cooldown in that order; a side preview shows the
exact executable JSON. Primary: simulate; secondary: save/activate. Execution
table and approval centre follow. Approvals inspect exact payload/version;
editing invalidates approval. Pending/approved/executed are distinct states.

### 07 / Recovery

Five metrics. Exposure-by-segment chart beside prioritisation explanation.
Priority queue occupies the main width; right rail holds selected intervention
and evidence. On mobile selection opens a full-screen drawer. Primary: assign
and propose follow-up; secondary: record an outcome. Priority uses documented
exposure, risk, urgency and actionability, with no guaranteed-recovery language.
All action status changes require confirmed backend persistence.

### 08 / Reports

Header: Reports & briefings, Create report. Library rows show actual report
version, period, author, generated time and download actions. Builder arranges
metric/dimension selection left and report outline right; tablet/mobile stack.
Primary: generate; secondary: save analytical view. CSV/PDF use backend data.
Scheduled delivery form shows recipients, cadence and configured transport.
Unconfigured email is explicit; no silent external distribution.

### 09 / Operations

Integration status strip (demo, imports, HubSpot, Stripe); metrics summarize real
jobs and quality checks. Full-width ingestion history, then paired data-quality
and freshness panels. Model registry and scoring health follow, then workflow
executions/audit. Primary: import data; secondary: inspect sync. Import wizard:
upload, entity, mapping, preview/errors, confirmation, committed result. Tabs
never obscure failures. Disconnected connectors show configuration, not success.

## Verification gate

Capture actual application screenshots for nine routes at 1440×1000, 768×1024
and 390×844: 27 screenshots, stored under docs/screenshots after review. Verify
navigation, filters, tables, sorting, detail drawers, keyboard focus, chart sizing,
responsive overflow and all application states. Record defects and corrections
in docs/frontend-verification.md. A screenshot of a static reference is not evidence
that a screen works. Frontend completion requires real backend interactions and
passing responsive verification; planned capabilities remain marked incomplete.
