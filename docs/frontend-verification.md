# Frontend verification

Actual Next.js application inspected through the browser's Playwright controls.
Screenshots are captures of working screens and configuration states, not the
provided static prototype. All analytical charts query PostgreSQL-backed APIs.

## Responsive capture matrix

Nine routes at 1440x1000, 768x1024 and 390x844: 27 full-page screenshots in
screenshots/. Desktop navigation becomes an icon rail on tablet and a modal
navigation drawer on mobile. Tables scroll inside their own labelled regions.

Across all routes the observed document width did not exceed viewport width.
Initial mobile review found wrapped currency values; compact headline amounts
and exact-value drawers correct that issue. Forecast controls were clipped by
intrinsic grid sizing; min-width:0 containment fixes the panel. Model diagnostics
were too wide; structured model summaries replace the oversized JSON table.
A text-encoding issue in arrow/separator glyphs was also corrected.

## Executed checks

- All nine API workspaces return 200 with tenant-scoped, synthetic-data metadata.
- 27 browser route/layout captures; no page-level overflow or displayed request
  errors in the inspected normal states.
- Mobile financial metrics have no horizontal overflow after the compact-value fix.
- Actual opportunity detail opens persisted stage history and activity records.
- Backend verification: 23 tests passed, including financial reconciliation,
  tenant denial, changed-payload approval, replay rejection, imports and exports.
- Four dbt views and five data tests passed.
- Final production build and TypeScript checks passed.

Additional final-state recapture and interaction checks are recorded as they run.
The nine-screen foundation is not a claim that every feature in the complete
product specification has been implemented. See implementation-status.md.

## Reproducible suite

apps/web/tests/e2e/workspace.spec.ts defines 13 cases over desktop/tablet/mobile
profiles (39 cases). It exercises route loading, actual backend data, filters,
metric drawers, pipeline detail/pagination, rule simulation and invalid-period
recovery. GitHub Actions starts PostgreSQL, seeds data, builds dbt, trains models,
starts API/web, runs the suite and preserves its browser evidence.
