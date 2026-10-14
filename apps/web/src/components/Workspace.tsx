"use client";
import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import {
  QueryClient,
  QueryClientProvider,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  Bell,
  BookOpen,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Command,
  Database,
  Layers3,
  Menu,
  MessageSquare,
  MoreHorizontal,
  Moon,
  Plus,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Sun,
  Target,
  TrendingUp,
  Users,
  Workflow,
  X,
  Zap,
} from "lucide-react";
import {
  api,
  Data,
  Metric,
  Row,
  numeric,
  metricDisplay,
  timestamp,
  display,
} from "@/lib/api";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import Table from "./Table";
const Chart = dynamic(() => import("./Chart"), {
  ssr: false,
  loading: () => <div className="skeleton chart" />,
});
const nav = [
  ["overview", "Overview", BarChart3],
  ["pipeline", "Sales pipeline", Layers3],
  ["forecasting", "Revenue forecasting", TrendingUp],
  ["customers", "Customer intelligence", Users],
  ["analyst", "AI analyst", MessageSquare],
  ["automations", "Automation studio", Workflow],
  ["recovery", "Revenue recovery", Target],
  ["reports", "Reports & briefings", BookOpen],
  ["operations", "Data operations", Database],
] as const;
const copy: Record<string, [string, string]> = {
  overview: [
    "Your revenue, in perspective.",
    "A clear view of performance. A connected path to the next decision.",
  ],
  pipeline: [
    "Every deal has a story.",
    "Follow progression, understand friction and focus on the opportunities that matter.",
  ],
  forecasting: [
    "See the quarter ahead.",
    "Separate a defensible forecast from an optimistic assumption.",
  ],
  customers: [
    "Know the value. Keep the relationship.",
    "Connect recurring revenue, account history and opportunities for growth.",
  ],
  analyst: [
    "A better question. A clearer answer.",
    "Investigate revenue with governed metrics and traceable evidence.",
  ],
  automations: [
    "Make the next move repeatable.",
    "Turn clear conditions into deliberate, approval-controlled action.",
  ],
  recovery: [
    "Focus where it can make a difference.",
    "Prioritise commercial exposure and keep every intervention accountable.",
  ],
  reports: [
    "Clarity, ready to share.",
    "Turn a reporting period into a versioned, reproducible briefing.",
  ],
  operations: [
    "Trust starts at the source.",
    "Inspect the data, models and workflows behind every commercial decision.",
  ],
};
const templates = [
  ["Stalled opportunity follow-up", "Days in stage exceed a threshold."],
  ["High-value deal risk alert", "Large opportunities need closer review."],
  ["Revenue target variance", "Surface a material reporting-period gap."],
  [
    "Overdue invoice follow-up",
    "Review unpaid balances before proposing contact.",
  ],
  [
    "Customer churn intervention",
    "Prioritise an evidence-backed retention review.",
  ],
  ["Weekly executive briefing", "Build a consistent commercial review."],
  [
    "Forecast anomaly investigation",
    "Investigate deviations from the baseline.",
  ],
  ["Deal-stage change response", "Respond to a recorded pipeline transition."],
];

export default function Workspace({ screen }: { screen: string }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: 1, staleTime: 30000, refetchOnWindowFocus: false },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <Content screen={screen} />
    </QueryClientProvider>
  );
}

function Content({ screen }: { screen: string }) {
  const router = useRouter(),
    pathname = usePathname(),
    params = useSearchParams(),
    client = useQueryClient();
  const [theme, setTheme] = useState("light"),
    [menu, setMenu] = useState(false),
    [search, setSearch] = useState(""),
    [notice, setNotice] = useState(""),
    [drawer, setDrawer] = useState<{
      title: string;
      content: React.ReactNode;
    } | null>(null),
    [selected, setSelected] = useState<Row | null>(null);
  const dialog = useRef<HTMLDialogElement>(null),
    menuDialog = useRef<HTMLDialogElement>(null);
  const start = params.get("start") || "2025-11-01",
    end = params.get("end") || "2026-10-14",
    segment = params.get("segment") || "All",
    page = Number(params.get("page") || 1);
  const query = new URLSearchParams({
    start,
    end,
    segment,
    page: String(page),
    search: params.get("search") || "",
    sort: params.get("sort") || "amount",
    direction: params.get("direction") || "desc",
  }).toString();
  const result = useQuery({
    queryKey: ["dashboard", screen, query],
    queryFn: ({ signal }) =>
      api<Data>(`dashboard/${screen}?${query}`, undefined, signal),
  });
  const data = result.data;
  const globalSearch = useQuery({
    queryKey: ["search", search],
    queryFn: ({ signal }) =>
      api<Row[]>(`search?q=${encodeURIComponent(search)}`, undefined, signal),
    enabled: search.length >= 2,
  });
  useEffect(() => {
    const saved = localStorage.getItem("revpilot-theme");
    if (saved === "dark") setTheme("dark");
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("revpilot-theme", theme);
  }, [theme]);
  useEffect(() => {
    if (drawer) dialog.current?.showModal();
    else dialog.current?.close();
  }, [drawer]);
  useEffect(() => {
    if (menu) menuDialog.current?.showModal();
    else menuDialog.current?.close();
  }, [menu]);
  function update(key: string, value: string) {
    const next = new URLSearchParams(params);
    next.set(key, value);
    if (key !== "page") next.delete("page");
    router.replace(pathname + "?" + next.toString(), { scroll: false });
  }
  function refresh() {
    client.invalidateQueries({ queryKey: ["dashboard"] });
  }
  function toast(message: string) {
    setNotice(message);
  }
  async function detail(row: Row, kind = screen) {
    setSelected(row);
    setDrawer({
      title: String(
        row.opportunity || row.account || row.name || "Record detail",
      ),
      content: (
        <Detail recordId={String(row.id)} kind={kind} onPropose={proposal} />
      ),
    });
  }
  async function proposal(id: string) {
    setDrawer({
      title: "Prepare a follow-up",
      content: (
        <ProposalForm
          id={id}
          onSaved={() => {
            refresh();
            setDrawer(null);
            toast(
              "Proposal saved. Review its exact payload in the approval centre.",
            );
          }}
        />
      ),
    });
  }
  function metricDetail(metric: Metric) {
    setDrawer({
      title: metric.label,
      content: (
        <div className="detail-stack">
          <div className="large-value">
            {numeric(metric.value)} <small>{metric.unit}</small>
          </div>
          <h3>Definition</h3>
          <p>{metric.definition}</p>
          <h3>Evidence and scope</h3>
          <p>
            PostgreSQL analytical views · {start} to {end} · {segment} segments.
          </p>
          <span className="badge">Synthetic demonstration data</span>
          <p>
            Missing values are shown as unavailable. Revenue recognition,
            invoicing, bookings and cash collection are distinct measures.
          </p>
          <Link className="button secondary" href={"/analyst?" + query}>
            Inspect the metric catalogue <ArrowRight size={15} />
          </Link>
        </div>
      ),
    });
  }
  const navLinks = (
    <>
      {nav.map(([slug, label, Icon], i) => (
        <Link
          title={label}
          aria-current={slug === screen ? "page" : undefined}
          onClick={() => setMenu(false)}
          className={"nav-link " + (slug === screen ? "active" : "")}
          key={slug}
          href={`/${slug}?${query}`}
        >
          <Icon size={17} />
          <span>{label}</span>
          {slug === "analyst" && <span className="new-tag">AI</span>}
          {slug === screen && <i />}
        </Link>
      ))}
    </>
  );
  return (
    <div className="application">
      <a className="skip" href="#workspace">
        Skip to workspace
      </a>
      <aside className="sidebar">
        <Link className="brand" href="/overview">
          <span className="brand-symbol">
            <Activity size={20} />
          </span>
          <span>
            revpilot<span className="brand-ai">AI</span>
          </span>
        </Link>
        <button
          className="org-switch"
          onClick={() =>
            setDrawer({
              title: "Your workspace",
              content: (
                <div className="detail-stack">
                  <h3>Northstar Cloud</h3>
                  <p>
                    An isolated synthetic B2B company. Demo records and actions
                    never represent actual customer performance.
                  </p>
                  <span className="badge jade">Demonstration workspace</span>
                  <p>
                    Live organisation access will require an authenticated OIDC
                    session and membership.
                  </p>
                </div>
              ),
            })
          }
        >
          <span className="org-icon">N</span>
          <span>
            Northstar Cloud<small>Revenue operations</small>
          </span>
          <ChevronDown size={14} />
        </button>
        <div className="nav-section">WORKSPACE</div>
        <nav aria-label="Main navigation">{navLinks}</nav>
        <div className="sidebar-bottom">
          <div className="status-dot" />
          <span>
            Synthetic demonstration<small>Data you can investigate.</small>
          </span>
          <ShieldCheck size={16} />
        </div>
        <Link
          className="creator"
          href="https://victorokeke.co.uk"
          target="_blank"
          rel="noreferrer"
        >
          Built by Victor Okeke <ArrowUpRight size={12} />
        </Link>
      </aside>
      <div className="main">
        <header className="topbar">
          <div className="crumb">
            <button
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              onClick={() => setMenu(true)}
            >
              <Menu size={19} />
            </button>
            <span>Workspace</span>
            <ChevronRight size={13} />
            <strong>{nav.find((n) => n[0] === screen)?.[1]}</strong>
          </div>
          <div className="top-actions">
            <div className="global-search">
              <Search size={15} />
              <input
                aria-label="Search accounts and opportunities"
                placeholder="Search anything…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <kbd>⌘ K</kbd>
              {search.length >= 2 && (
                <div className="search-results">
                  {globalSearch.isPending ? (
                    <p>Searching…</p>
                  ) : globalSearch.data?.length ? (
                    globalSearch.data.map((r) => (
                      <button
                        key={String(r.id)}
                        onClick={() => {
                          setSearch("");
                          detail(r, String(r.route));
                        }}
                      >
                        {String(r.name)}
                        <small>{String(r.route)}</small>
                      </button>
                    ))
                  ) : (
                    <p>No matching records.</p>
                  )}
                </div>
              )}
            </div>
            <span className="demo-pill">
              <span />
              Demo workspace
            </span>
            <button
              className="icon-button"
              aria-label={
                theme === "light"
                  ? "Switch to dark mode"
                  : "Switch to light mode"
              }
              onClick={() => setTheme(theme === "light" ? "dark" : "light")}
            >
              {theme === "light" ? <Moon size={17} /> : <Sun size={17} />}
            </button>
            <button
              className="icon-button"
              aria-label="Notifications"
              onClick={() =>
                setDrawer({
                  title: "Notifications",
                  content: (
                    <div className="detail-stack">
                      <p>
                        Operational notifications use persisted job and approval
                        records.
                      </p>
                      <Link
                        className="button secondary"
                        href={"/operations?" + query}
                      >
                        Review data operations <ArrowRight size={15} />
                      </Link>
                      <Link
                        className="button secondary"
                        href={"/automations?" + query}
                      >
                        Review pending approvals <ArrowRight size={15} />
                      </Link>
                    </div>
                  ),
                })
              }
            >
              <Bell size={17} />
            </button>
            <button
              className="avatar"
              aria-label="Profile and settings"
              onClick={() =>
                setDrawer({
                  title: "Workspace settings",
                  content: (
                    <div className="detail-stack">
                      <h3>Demo operator</h3>
                      <p>Northstar Cloud · isolated demonstration tenant.</p>
                      <p>
                        External writes and customer-facing messages are
                        disabled. Model, connector and AI configuration is
                        managed by environment settings.
                      </p>
                      <Link
                        className="button secondary"
                        href={"/operations?" + query}
                      >
                        Inspect configuration
                      </Link>
                    </div>
                  ),
                })
              }
            >
              VO
            </button>
          </div>
        </header>
        <main id="workspace" className="content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                <span className="eyebrow-line" />{" "}
                {String(nav.findIndex((n) => n[0] === screen) + 1).padStart(
                  2,
                  "0",
                )}{" "}
                / COMMERCIAL INTELLIGENCE
              </div>
              <h1>{copy[screen][0]}</h1>
              <p>{copy[screen][1]}</p>
            </div>
            <div className="heading-actions">
              <button
                className="button secondary refresh"
                onClick={refresh}
                disabled={result.isFetching}
                aria-label="Refresh data"
              >
                <RefreshCw
                  size={15}
                  className={result.isFetching ? "spin" : ""}
                />
              </button>
              {screen === "reports" ? (
                <button
                  className="button"
                  onClick={() =>
                    setDrawer({
                      title: "Create a report",
                      content: (
                        <ReportForm
                          start={start}
                          end={end}
                          segment={segment}
                          onSaved={() => {
                            refresh();
                            setDrawer(null);
                            toast(
                              "Report generated from a persisted analytical snapshot.",
                            );
                          }}
                        />
                      ),
                    })
                  }
                >
                  <Plus size={15} />
                  Create report
                </button>
              ) : screen === "operations" ? (
                <button
                  className="button"
                  onClick={() =>
                    setDrawer({
                      title: "Import commercial data",
                      content: (
                        <ImportForm
                          onSaved={() => {
                            refresh();
                            toast("Account import committed.");
                          }}
                        />
                      ),
                    })
                  }
                >
                  <Plus size={15} />
                  Import data
                </button>
              ) : (
                <a
                  className="button secondary"
                  href={`/api/v1/export/${screen}?${query}`}
                >
                  <ArrowDownToLine size={15} />
                  Export CSV
                </a>
              )}
            </div>
          </div>
          <div className="filterbar">
            <div className="date-range">
              <label>
                From
                <input
                  type="date"
                  aria-label="Reporting period start"
                  value={start}
                  onChange={(e) =>
                    e.target.value && update("start", e.target.value)
                  }
                />
              </label>
              <span>→</span>
              <label>
                To
                <input
                  type="date"
                  aria-label="Reporting period end"
                  value={end}
                  onChange={(e) =>
                    e.target.value && update("end", e.target.value)
                  }
                />
              </label>
            </div>
            <label className="segment-select">
              <SlidersHorizontal size={14} />
              <select
                aria-label="Customer segment"
                value={segment}
                onChange={(e) => update("segment", e.target.value)}
              >
                {["All", "Enterprise", "Mid-market", "SMB"].map((v) => (
                  <option key={v} value={v}>
                    {v === "All" ? "All segments" : v}
                  </option>
                ))}
              </select>
            </label>
            <div className="freshness">
              <span
                className={"status-dot " + (data?.meta.stale ? "warn" : "")}
              />
              {data?.meta.refreshed_at ? (
                <>Refreshed {timestamp(data.meta.refreshed_at)}</>
              ) : (
                "Connecting to data…"
              )}
            </div>
          </div>
          {data?.meta.stale && (
            <div className="notice amber">
              <Activity size={16} />
              <div>
                Stored data is more than a day old. Last successful refresh:{" "}
                {timestamp(data.meta.refreshed_at)}.
              </div>
              <button onClick={refresh}>Refresh</button>
            </div>
          )}
          {notice && (
            <div className="notice" role="status">
              <Check size={16} />
              <span>{notice}</span>
              <button
                aria-label="Dismiss notification"
                onClick={() => setNotice("")}
              >
                <X size={15} />
              </button>
            </div>
          )}
          {result.isPending ? (
            <div aria-label="Loading workspace" role="status">
              <div className="metric-grid">
                {Array.from({ length: 5 }, (_, i) => (
                  <div key={i} className="skeleton metric" />
                ))}
              </div>
              <div className="chart-grid">
                <div className="skeleton panel chart" />
                <div className="skeleton panel chart" />
              </div>
            </div>
          ) : result.isError ? (
            <div className="error-state" role="alert">
              <Activity size={26} />
              <h2>We couldn’t load this workspace.</h2>
              <p>{result.error.message}</p>
              <button className="button" onClick={() => result.refetch()}>
                Retry connection
              </button>
            </div>
          ) : (
            data && (
              <>
                {!!data.metrics.length && (
                  <section
                    className="metric-grid"
                    aria-label="Key performance indicators"
                  >
                    {data.metrics.map((m, i) => (
                      <button
                        onClick={() => metricDetail(m)}
                        className={"metric " + (i === 0 ? "lead" : "")}
                        key={m.id}
                      >
                        <div className="metric-label">
                          {m.label}
                          <ArrowUpRight size={13} />
                        </div>
                        <strong>{metricDisplay(m)}</strong>
                        <span className="metric-foot">
                          {m.unit}
                          <span>View definition</span>
                        </span>
                      </button>
                    ))}
                  </section>
                )}
                {screen === "analyst" ? (
                  <Analyst data={data} onChange={refresh} />
                ) : screen === "automations" ? (
                  <Automations data={data} onChange={refresh} notify={toast} />
                ) : screen === "reports" ? (
                  <Reports
                    data={data}
                    onCreate={() =>
                      setDrawer({
                        title: "Create a report",
                        content: (
                          <ReportForm
                            start={start}
                            end={end}
                            segment={segment}
                            onSaved={() => {
                              refresh();
                              setDrawer(null);
                            }}
                          />
                        ),
                      })
                    }
                  />
                ) : null}
                {screen === "forecasting" && (
                  <ForecastControls data={data} onChange={refresh} />
                )}
                {!!data.charts.length && (
                  <section
                    className="chart-grid"
                    aria-label="Analytical charts"
                  >
                    {data.charts.map((spec, i) => (
                      <section
                        className={
                          "panel " +
                          (i === 0 && screen === "overview"
                            ? "chart-major"
                            : "")
                        }
                        key={spec.title}
                      >
                        <div className="panel-heading">
                          <div>
                            <h2>{spec.title}</h2>
                            <p>
                              {spec.unit} ·{" "}
                              {segment === "All" ? "All segments" : segment} ·
                              SQL-backed
                            </p>
                          </div>
                          <span className="chart-index">
                            {String(i + 1).padStart(2, "0")}
                          </span>
                        </div>
                        {spec.rows.length ? (
                          <Chart
                            spec={spec}
                            theme={theme}
                            onSelect={
                              spec.title === "Revenue by segment"
                                ? (v) => update("segment", v)
                                : undefined
                            }
                          />
                        ) : (
                          <div className="empty">
                            <h3>No observations in this period.</h3>
                            <p>Choose another reporting window.</p>
                          </div>
                        )}
                        <details className="accessible-data">
                          <summary>View data table</summary>
                          <Table rows={spec.rows} />
                        </details>
                      </section>
                    ))}
                  </section>
                )}
                {["pipeline", "customers", "recovery"].includes(screen) && (
                  <section className="panel record-panel">
                    <div className="panel-heading">
                      <div>
                        <h2>
                          {screen === "customers"
                            ? "Customer directory"
                            : screen === "recovery"
                              ? "Your priority queue"
                              : "Opportunity workspace"}
                        </h2>
                        <p>
                          {numeric(data.total, 0)} records ·{" "}
                          {screen === "recovery"
                            ? "Priority = exposure Ã— capped stage age / 90; heuristic, not a recovery guarantee."
                            : "Select a record to follow the evidence."}
                        </p>
                      </div>
                      <input
                        className="table-search"
                        aria-label="Filter records"
                        placeholder="Search records…"
                        value={params.get("search") || ""}
                        onChange={(e) => update("search", e.target.value)}
                      />
                    </div>
                    <Table
                      rows={data.table}
                      onRow={(r) => detail(r)}
                      onSort={
                        screen === "pipeline"
                          ? (k) => {
                              const next = new URLSearchParams(params);
                              next.set("sort", k);
                              next.set(
                                "direction",
                                params.get("direction") === "asc"
                                  ? "desc"
                                  : "asc",
                              );
                              router.replace(pathname + "?" + next.toString(), {
                                scroll: false,
                              });
                            }
                          : undefined
                      }
                    />
                    <div className="pagination">
                      <span>Page {page} · up to 20 records</span>
                      <div>
                        <button
                          className="icon-button"
                          disabled={page <= 1}
                          aria-label="Previous page"
                          onClick={() => update("page", String(page - 1))}
                        >
                          <ChevronLeft size={16} />
                        </button>
                        <button
                          className="icon-button"
                          disabled={page * 20 >= data.total}
                          aria-label="Next page"
                          onClick={() => update("page", String(page + 1))}
                        >
                          <ChevronRight size={16} />
                        </button>
                      </div>
                    </div>
                  </section>
                )}
                {screen === "operations" && <Operations data={data} />}
                {Array.isArray(data.insights) && data.insights.length > 0 && (
                  <section className="insight-strip">
                    <div className="insight-title">
                      <Zap size={18} />
                      <span>
                        Signals to act on<small>Start with the evidence.</small>
                      </span>
                    </div>
                    {(
                      data.insights as {
                        title: string;
                        detail: string;
                        route: string;
                      }[]
                    ).map((i) => (
                      <Link href={"/" + i.route + "?" + query} key={i.title}>
                        <h3>
                          {i.title}
                          <ArrowUpRight size={14} />
                        </h3>
                        <p>{i.detail}</p>
                      </Link>
                    ))}
                  </section>
                )}
              </>
            )
          )}
          <footer className="footer">
            <span>
              <span className="footer-mark">R/</span> REVPILOT AI
            </span>
            <span>Northstar Cloud · Synthetic demonstration data</span>
            <span>Intelligence with a clear line to evidence.</span>
          </footer>
        </main>
      </div>
      <dialog
        ref={dialog}
        className="drawer"
        onCancel={() => setDrawer(null)}
        onClick={(e) => {
          if (e.target === dialog.current) setDrawer(null);
        }}
      >
        <div className="drawer-content">
          <header>
            <span className="eyebrow">WORKSPACE / DETAIL</span>
            <button
              className="icon-button"
              aria-label="Close detail"
              onClick={() => setDrawer(null)}
            >
              <X size={20} />
            </button>
          </header>
          <h2>{drawer?.title}</h2>
          {drawer?.content}
        </div>
      </dialog>
      <dialog
        ref={menuDialog}
        className="mobile-nav-dialog"
        onCancel={() => setMenu(false)}
      >
        <header>
          <strong>revpilot AI</strong>
          <button
            className="icon-button"
            onClick={() => setMenu(false)}
            aria-label="Close navigation"
          >
            <X size={20} />
          </button>
        </header>
        <nav aria-label="Mobile navigation">{navLinks}</nav>
      </dialog>
    </div>
  );
}

function Detail({
  recordId,
  kind,
  onPropose,
}: {
  recordId: string;
  kind: string;
  onPropose: (id: string) => void;
}) {
  const q = useQuery({
    queryKey: ["detail", kind, recordId],
    queryFn: () => api<Record<string, unknown>>(`details/${kind}/${recordId}`),
  });
  if (q.isPending) return <p role="status">Loading record history…</p>;
  if (q.isError) return <p role="alert">{q.error.message}</p>;
  return (
    <div className="detail-stack">
      {Object.entries(q.data).map(([key, value]) => (
        <section key={key}>
          <h3>{key.replaceAll("_", " ")}</h3>
          {Array.isArray(value) ? (
            <Table
              rows={(value as Row[]).map((row) =>
                key === "prediction"
                  ? {
                      kind: (row.payload as Row)?.kind,
                      probability_percent:
                        Number((row.payload as Row)?.probability) * 100,
                      as_of: (row.payload as Row)?.as_of,
                      scope: (row.payload as Row)?.scope,
                    }
                  : row,
              )}
            />
          ) : value && typeof value === "object" ? (
            <dl className="record-details">
              {Object.entries(value)
                .filter(
                  ([k]) =>
                    !["id", "org_id", "owner_id", "account_id"].includes(k),
                )
                .map(([k, v]) => (
                  <div key={k}>
                    <dt>{k.replaceAll("_", " ")}</dt>
                    <dd>{display(k, v)}</dd>
                  </div>
                ))}
            </dl>
          ) : (
            <p>{String(value)}</p>
          )}
        </section>
      ))}
      {kind !== "customers" && (
        <button className="button" onClick={() => onPropose(recordId)}>
          Prepare follow-up <ArrowRight size={15} />
        </button>
      )}
    </div>
  );
}

const proposalSchema = z.object({
  title: z.string().min(3, "Use at least three characters.").max(150),
  note: z.string().max(2000),
});
function ProposalForm({ id, onSaved }: { id: string; onSaved: () => void }) {
  const form = useForm<z.infer<typeof proposalSchema>>({
    resolver: zodResolver(proposalSchema),
    defaultValues: { title: "Review stalled opportunity", note: "" },
  });
  const mutation = useMutation({
    mutationFn: (values: z.infer<typeof proposalSchema>) =>
      api("proposals", { opportunity_id: id, ...values }),
    onSuccess: onSaved,
  });
  return (
    <form
      className="form-stack"
      onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
    >
      <div className="notice">
        <ShieldCheck size={18} />
        <p>
          The exact proposal is sent for approval. Demo execution records an
          internal task; it sends no external message.
        </p>
      </div>
      <label>
        Task title
        <input
          {...form.register("title")}
          aria-invalid={Boolean(form.formState.errors.title)}
        />
        {form.formState.errors.title && (
          <span role="alert">{form.formState.errors.title.message}</span>
        )}
      </label>
      <label>
        Context and next steps
        <textarea rows={5} {...form.register("note")} />
      </label>
      <button className="button" disabled={mutation.isPending}>
        {mutation.isPending ? "Saving..." : "Submit for approval"}
      </button>
      {mutation.isError && (
        <p role="alert" className="form-error">
          {mutation.error.message}
        </p>
      )}
    </form>
  );
}

function Analyst({ data, onChange }: { data: Data; onChange: () => void }) {
  const [question, setQuestion] = useState(""),
    [answer, setAnswer] = useState<unknown>(null);
  const configured = Boolean(data.configured);
  const investigation = useMutation({
    mutationFn: () => api("investigations", { question }),
    onSuccess: (r) => {
      setAnswer(r);
      onChange();
    },
  });
  return (
    <section className="analyst-workspace">
      <aside className="investigation-sidebar">
        <span className="eyebrow">INVESTIGATIONS</span>
        <h3>Your analytical notebook</h3>
        <div className="empty compact">
          {Array.isArray(data.conversations) && data.conversations.length
            ? "Saved investigations are available."
            : "No saved investigations yet."}
        </div>
        <span className="eyebrow">START WITH A QUESTION</span>
        {[
          "Why did invoiced revenue change?",
          "Which opportunities need attention?",
          "Where is customer value concentrated?",
        ].map((s) => (
          <button key={s} onClick={() => setQuestion(s)}>
            {s}
            <ArrowUpRight size={13} />
          </button>
        ))}
      </aside>
      <div className="analyst-main">
        <div className="analyst-welcome">
          <div className="analyst-symbol">
            <Activity size={32} />
          </div>
          <span className="eyebrow">YOUR REVENUE, WITH CONTEXT</span>
          <h2>
            Move from a number
            <br />
            to an understanding.
          </h2>
          <p>
            Every investigation starts with governed metrics and ends with
            evidence you can inspect.
          </p>
          {!configured && (
            <div className="notice amber">
              <Settings2 size={18} />
              <span>
                LLM provider not connected. Configure a provider and model to
                enable investigations. SQL analytics remain available.
              </span>
            </div>
          )}
          {answer !== null && (
            <article className="analytical-answer">
              <h3>Investigation result</h3>
              <p>{String((answer as Row).answer || "No response returned.")}</p>
              <details>
                <summary>Inspect evidence references</summary>
                <pre>{JSON.stringify((answer as Row).evidence, null, 2)}</pre>
              </details>
            </article>
          )}
        </div>
        <form
          className="analyst-composer"
          onSubmit={(e) => {
            e.preventDefault();
            investigation.mutate();
          }}
        >
          <textarea
            aria-label="Investigation question"
            placeholder="Ask a question about your revenue…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={3}
          />
          <div>
            <span>Governed tools · Evidence-linked answers</span>
            <button
              className="button"
              disabled={
                !configured || question.length < 5 || investigation.isPending
              }
            >
              {investigation.isPending ? "Investigating…" : "Investigate"}
              <ArrowUpRight size={15} />
            </button>
          </div>
          {investigation.isError && (
            <p role="alert">{investigation.error.message}</p>
          )}
        </form>
      </div>
      <aside className="evidence-pane">
        <div className="panel-heading">
          <h3>Evidence & definitions</h3>
          <ShieldCheck size={17} />
        </div>
        <p>
          Commercial measures have different meanings. Start with the
          definition.
        </p>
        {(
          (data.catalogue as {
            id: string;
            label: string;
            definition: string;
            unit: string;
          }[]) || []
        )
          .slice(0, 6)
          .map((m) => (
            <details key={m.id}>
              <summary>
                {m.label}
                <span>{m.unit}</span>
              </summary>
              <p>{m.definition}</p>
            </details>
          ))}
      </aside>
    </section>
  );
}

function Automations({
  data,
  onChange,
  notify,
}: {
  data: Data;
  onChange: () => void;
  notify: (s: string) => void;
}) {
  const [title, setTitle] = useState(templates[0][0]),
    [days, setDays] = useState(30),
    [amount, setAmount] = useState(10000),
    [operator, setOperator] = useState("AND"),
    [active, setActive] = useState(false),
    [simulation, setSimulation] = useState<Row[]>([]),
    [review, setReview] = useState<Row | null>(null);
  const rule = {
    title,
    threshold: days,
    minimum_amount: amount,
    operator,
    cooldown_hours: 24,
    active,
  };
  const dry = useMutation({
    mutationFn: () => api<Row[]>("rules/simulate", rule),
    onSuccess: setSimulation,
  });
  const save = useMutation({
    mutationFn: () => api("rules", rule),
    onSuccess: () => {
      onChange();
      notify(
        "Rule saved. Execution is subject to the configured worker and approval policy.",
      );
    },
  });
  const decide = useMutation({
    mutationFn: ({ row, decision }: { row: Row; decision: string }) =>
      api(`approvals/${row.id}/decision`, { decision, version: row.version }),
    onSuccess: () => {
      setReview(null);
      onChange();
      notify("Decision recorded with an immutable action audit.");
    },
  });
  const approvals = (data.approvals || []) as Row[];
  const rules = (data.rules || []) as Row[];
  return (
    <>
      <section className="section-heading">
        <div>
          <h2>Workflow library</h2>
          <p>A clear trigger. A deliberate response.</p>
        </div>
        <span className="badge">
          Approval required for every external action
        </span>
      </section>
      <div className="template-grid">
        {templates.map(([name, description], i) => (
          <button
            className={"template " + (name === title ? "selected" : "")}
            key={name}
            onClick={() => setTitle(name)}
          >
            <span className="template-icon">
              <Workflow size={18} />
            </span>
            <span className="eyebrow">
              TEMPLATE / {String(i + 1).padStart(2, "0")}
            </span>
            <h3>{name}</h3>
            <p>{description}</p>
            <span className="template-footer">
              Configure workflow <ArrowUpRight size={14} />
            </span>
          </button>
        ))}
      </div>
      <section className="panel rule-builder">
        <div className="panel-heading">
          <div>
            <h2>Build a precise rule</h2>
            <p>
              The current executable condition supports opportunity stage age
              and value.
            </p>
          </div>
          <span className="badge jade">Server-validated</span>
        </div>
        <div className="builder-grid">
          <form
            className="form-stack"
            onSubmit={(e) => {
              e.preventDefault();
              save.mutate();
            }}
          >
            <label>
              Rule name
              <input
                minLength={3}
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <div className="rule-node">
              <span className="node-number">01</span>
              <div>
                <strong>When an opportunity is evaluated</strong>
                <p>Scheduled trigger · open deals only</p>
              </div>
              <Zap size={17} />
            </div>
            <div className="connector">↓</div>
            <div className="rule-node conditions">
              <span className="node-number">02</span>
              <div>
                <label>
                  Days in stage ≥
                  <input
                    type="number"
                    aria-label="Days in stage threshold"
                    min={1}
                    max={365}
                    value={days}
                    onChange={(e) => setDays(Number(e.target.value))}
                  />
                </label>
                <select
                  aria-label="Condition operator"
                  value={operator}
                  onChange={(e) => setOperator(e.target.value)}
                >
                  <option>AND</option>
                  <option>OR</option>
                </select>
                <label>
                  Amount ≥ GBP
                  <input
                    type="number"
                    aria-label="Minimum opportunity amount"
                    min={0}
                    value={amount}
                    onChange={(e) => setAmount(Number(e.target.value))}
                  />
                </label>
              </div>
            </div>
            <div className="connector">↓</div>
            <div className="rule-node">
              <span className="node-number">03</span>
              <div>
                <strong>Propose an internal follow-up</strong>
                <p>Exact payload approval · 24-hour cooldown</p>
              </div>
              <ShieldCheck size={17} />
            </div>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={active}
                onChange={(e) => setActive(e.target.checked)}
              />
              Save as active rule
            </label>
            <div className="button-row">
              <button
                type="button"
                className="button secondary"
                disabled={dry.isPending}
                onClick={() => dry.mutate()}
              >
                Run simulation
              </button>
              <button className="button" disabled={save.isPending}>
                Save workflow
              </button>
            </div>
            {(dry.isError || save.isError) && (
              <p role="alert">{dry.error?.message || save.error?.message}</p>
            )}
          </form>
          <div className="rule-preview">
            <span className="eyebrow">EXECUTABLE DEFINITION</span>
            <pre>
              {JSON.stringify(
                {
                  ...rule,
                  action: "internal_follow_up",
                  approval_required: true,
                },
                null,
                2,
              )}
            </pre>
            <div className="notice">
              <ShieldCheck size={17} />
              <p>
                Simulating changes no records. Saving a rule persists its exact
                definition.
              </p>
            </div>
          </div>
        </div>
        {dry.isSuccess && (
          <>
            <h3>
              Simulation · {simulation.length} matching opportunities (maximum
              30)
            </h3>
            <Table rows={simulation} />
          </>
        )}
      </section>
      <div className="chart-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Approval centre</h2>
              <p>Review the payload before deciding.</p>
            </div>
            <span className="badge">
              {approvals.filter((r) => r.status === "pending").length} pending
            </span>
          </div>
          {approvals.length ? (
            approvals.map((r) => (
              <div className="approval-row" key={String(r.id)}>
                <ShieldCheck size={17} />
                <div>
                  <strong>
                    {String(
                      ((r.payload as Row)?.action &&
                        ((r.payload as Row).action as Row).title) ||
                        "Follow-up proposal",
                    )}
                  </strong>
                  <small>{timestamp(r.created_at)}</small>
                </div>
                <span className="badge amber">{String(r.status)}</span>
                {r.status === "pending" && (
                  <button
                    className="button secondary"
                    onClick={() => setReview(r)}
                  >
                    Review
                  </button>
                )}
              </div>
            ))
          ) : (
            <div className="empty">
              <ShieldCheck size={26} />
              <strong>No pending approvals.</strong>
              <p>Propose an intervention from Pipeline or Revenue Recovery.</p>
            </div>
          )}
          {review && (
            <div className="approval-review">
              <h3>Exact action payload · version {String(review.version)}</h3>
              <pre>
                {JSON.stringify((review.payload as Row)?.action, null, 2)}
              </pre>
              <div className="button-row">
                <button
                  className="button secondary"
                  disabled={decide.isPending}
                  onClick={() =>
                    decide.mutate({ row: review, decision: "reject" })
                  }
                >
                  Reject
                </button>
                <button
                  className="button"
                  disabled={decide.isPending}
                  onClick={() =>
                    decide.mutate({ row: review, decision: "approve" })
                  }
                >
                  Approve demo task
                </button>
              </div>
              {decide.isError && <p role="alert">{decide.error.message}</p>}
            </div>
          )}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Saved workflows</h2>
              <p>Definitions persisted to PostgreSQL.</p>
            </div>
            <span className="badge">{rules.length} rules</span>
          </div>
          {rules.length ? (
            rules.map((r) => (
              <div className="approval-row" key={String(r.id)}>
                <Workflow size={17} />
                <div>
                  <strong>{String((r.payload as Row).title)}</strong>
                  <small>{timestamp(r.created_at)}</small>
                </div>
                <span className="badge">{String(r.status)}</span>
              </div>
            ))
          ) : (
            <div className="empty">
              <strong>Your workflow library starts here.</strong>
              <p>Configure, simulate and save a rule above.</p>
            </div>
          )}
        </section>
      </div>
      <section className="panel">
        <div className="panel-heading">
          <h2>Execution history</h2>
        </div>
        <Table rows={data.table} />
      </section>
    </>
  );
}

function ForecastControls({
  data,
  onChange,
}: {
  data: Data;
  onChange: () => void;
}) {
  const [values, setValues] = useState<Record<string, number>>({
      win_rate: 0,
      slippage: 0,
      deal_size: 0,
      churn: 0,
      expansion: 0,
      growth: 0,
    }),
    [title, setTitle] = useState("Base case");
  const models = (data.models || []) as Row[];
  const run = useMutation({
    mutationFn: () => api("scenarios", { title, ...values }),
    onSuccess: onChange,
  });
  return (
    <section className="panel forecast-controls">
      <div className="panel-heading">
        <div>
          <h2>Scenario workspace</h2>
          <p>Recalculate assumptions through the forecasting service.</p>
        </div>
        <span className={"badge " + (models.length ? "jade" : "amber")}>
          {models.length ? "Model registered" : "Model training required"}
        </span>
      </div>
      <div className="scenario-grid">
        <div>
          <div className="button-row">
            {["Base case", "Upside case", "Downside case"].map((v, i) => (
              <button
                key={v}
                className={"button " + (title === v ? "" : "secondary")}
                onClick={() => {
                  setTitle(v);
                  setValues({
                    win_rate: i === 1 ? 5 : i === 2 ? -5 : 0,
                    slippage: i === 1 ? -5 : i === 2 ? 10 : 0,
                    deal_size: 0,
                    churn: 0,
                    expansion: i === 1 ? 5 : 0,
                    growth: i === 1 ? 8 : i === 2 ? -8 : 0,
                  });
                }}
              >
                {v}
              </button>
            ))}
          </div>
          <div className="scenario-inputs">
            {Object.entries(values).map(([k, v]) => (
              <label key={k}>
                {k.replaceAll("_", " ")}
                <div>
                  <input
                    type="range"
                    min={-30}
                    max={30}
                    value={v}
                    onChange={(e) =>
                      setValues({ ...values, [k]: Number(e.target.value) })
                    }
                  />
                  <output>
                    {v > 0 ? "+" : ""}
                    {v}%
                  </output>
                </div>
              </label>
            ))}
          </div>
          <button
            className="button"
            onClick={() => run.mutate()}
            disabled={run.isPending}
          >
            Recalculate & save <ArrowRight size={15} />
          </button>
          {run.isError && (
            <p className="form-error" role="alert">
              {run.error.message}
            </p>
          )}
          {run.isSuccess && (
            <div className="notice">
              Scenario saved from the registered forecast.
            </div>
          )}
        </div>
        <aside className="scenario-note">
          <span className="eyebrow">MODEL CONTEXT</span>
          <h3>A forecast needs an evaluation.</h3>
          <p>
            Scenario assumptions describe sensitivity. They are not causal
            effects or probability guarantees.
          </p>
          {models.length ? (
            <ModelRegistry
              models={models.filter(
                (m) => (m.payload as Row).kind === "forecast",
              )}
            />
          ) : (
            <div className="notice amber">
              No registered revenue forecast yet. Historical SQL analytics
              remain available.
            </div>
          )}
        </aside>
      </div>
    </section>
  );
}

function ReportForm({
  start,
  end,
  segment,
  onSaved,
}: {
  start: string;
  end: string;
  segment: string;
  onSaved: () => void;
}) {
  const [title, setTitle] = useState("Executive revenue briefing"),
    [metrics, setMetrics] = useState(["invoiced", "mrr", "pipeline"]);
  const create = useMutation({
    mutationFn: () => api("reports", { title, start, end, segment, metrics }),
    onSuccess: onSaved,
  });
  return (
    <form
      className="form-stack"
      onSubmit={(e) => {
        e.preventDefault();
        create.mutate();
      }}
    >
      <p>
        The report saves an analytical snapshot for {start} to {end}, {segment}{" "}
        segments.
      </p>
      <label>
        Report name
        <input
          required
          minLength={3}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </label>
      <fieldset>
        <legend>Metrics to include</legend>
        {[
          "invoiced",
          "cash",
          "mrr",
          "arr",
          "pipeline",
          "weighted",
          "at_risk",
        ].map((m) => (
          <label className="checkbox" key={m}>
            <input
              type="checkbox"
              checked={metrics.includes(m)}
              onChange={(e) =>
                setMetrics(
                  e.target.checked
                    ? [...metrics, m]
                    : metrics.filter((v) => v !== m),
                )
              }
            />
            {m.replaceAll("_", " ")}
          </label>
        ))}
      </fieldset>
      <button className="button" disabled={!metrics.length || create.isPending}>
        Generate report
      </button>
      {create.isError && <p role="alert">{create.error.message}</p>}
    </form>
  );
}
function Reports({ data, onCreate }: { data: Data; onCreate: () => void }) {
  return (
    <>
      <section className="report-banner">
        <div>
          <span className="eyebrow">FROM ANALYSIS TO ALIGNMENT</span>
          <h2>
            A shared view.
            <br />A stronger conversation.
          </h2>
          <p>
            Preserve the reporting window, definitions and numbers behind the
            discussion.
          </p>
          <button className="button" onClick={onCreate}>
            Build your briefing <ArrowRight size={15} />
          </button>
        </div>
        <div className="report-illustration" aria-hidden="true">
          <div className="report-paper">
            <span>REVPILOT / INTELLIGENCE BRIEF</span>
            <h3>
              Commercial
              <br />
              performance.
            </h3>
            <div className="paper-rule" />
            <ol className="paper-outline">
              <li>Performance & context</li>
              <li>Metrics & definitions</li>
              <li>Reporting period</li>
            </ol>
            <small>A versioned analytical snapshot.</small>
          </div>
        </div>
      </section>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Report library</h2>
            <p>Real snapshots. Explicit definitions. Reproducible periods.</p>
          </div>
          <span className="badge">{data.table.length} reports</span>
        </div>
        {data.table.length ? (
          data.table.map((r) => (
            <div className="report-row" key={String(r.id)}>
              <span className="report-type">
                <BookOpen size={20} />
              </span>
              <div>
                <h3>{String(r.report)}</h3>
                <p>
                  Version {String(r.version)} · {timestamp(r.created_at)}
                </p>
              </div>
              <span className="badge jade">Generated</span>
              <a
                className="button secondary"
                href={`/api/v1/reports/${r.id}/download?format=csv`}
              >
                CSV <ArrowDownToLine size={14} />
              </a>
              <a
                className="button secondary"
                href={`/api/v1/reports/${r.id}/download?format=pdf`}
              >
                PDF <ArrowDownToLine size={14} />
              </a>
            </div>
          ))
        ) : (
          <div className="empty">
            <BookOpen size={28} />
            <strong>Your first briefing starts with a reporting period.</strong>
            <p>
              Create a report to generate a persisted snapshot and CSV/PDF
              downloads.
            </p>
            <button className="button secondary" onClick={onCreate}>
              Create your first report
            </button>
          </div>
        )}
      </section>
      <section className="panel delivery-state">
        <div>
          <span className="eyebrow">SCHEDULED DELIVERY</span>
          <h3>Configure the destination before sharing.</h3>
          <p>
            Email transport and authorised recipients must be configured before
            automated distribution. Generating a report sends no external
            communication.
          </p>
        </div>
        <span className="badge amber">Delivery not configured</span>
      </section>
    </>
  );
}

function Operations({ data }: { data: Data }) {
  const jobs = (data.jobs || []) as Row[],
    quality = (data.quality || []) as Row[],
    models = (data.models || []) as Row[],
    imports = (data.imports || []) as Row[];
  return (
    <>
      <section className="integration-grid">
        {[
          ["Synthetic company", "Northstar Cloud", "Connected", "jade"],
          ["CSV / Excel", "Transactional imports", "Available", ""],
          ["HubSpot", "CRM accounts & deals", "Not connected", "amber"],
          ["Stripe", "Subscriptions & billing", "Not connected", "amber"],
        ].map(([name, description, status, tone]) => (
          <div className="panel integration" key={name}>
            <div className="integration-logo">
              {name === "Synthetic company" ? (
                <Database size={20} />
              ) : name === "Stripe" ? (
                <strong>S</strong>
              ) : name === "HubSpot" ? (
                <Workflow size={20} />
              ) : (
                <BookOpen size={20} />
              )}
            </div>
            <h3>{name}</h3>
            <p>{description}</p>
            <span className={"badge " + tone}>{status}</span>
          </div>
        ))}
      </section>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Ingestion history</h2>
            <p>Actual completed runs, preserved with provenance.</p>
          </div>
          <span className="badge jade">PostgreSQL-backed</span>
        </div>
        <Table
          rows={jobs.map((r) => ({
            status: r.status,
            created_at: r.created_at,
            ...(r.payload as Row),
          }))}
        />
      </section>
      <div className="chart-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Data quality</h2>
              <p>Persisted validation evidence.</p>
            </div>
            <ShieldCheck size={18} />
          </div>
          <Table
            rows={quality.map((r) => ({
              status: r.status,
              checked_at: r.created_at,
              ...(r.payload as Row),
            }))}
          />
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Import history</h2>
              <p>Preview, validate, then commit.</p>
            </div>
            <ArrowDownToLine size={18} />
          </div>
          <Table
            rows={imports.map((r) => ({
              status: r.status,
              filename: (r.payload as Row).filename,
              row_count: (r.payload as Row).row_count,
              created_at: r.created_at,
            }))}
          />
        </section>
      </div>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Model registry</h2>
            <p>Training scope and measured evaluation results.</p>
          </div>
          <span className="badge">{models.length} versions</span>
        </div>
        <ModelRegistry models={models} />
      </section>
    </>
  );
}

function ImportForm({ onSaved }: { onSaved: () => void }) {
  const [preview, setPreview] = useState<{
      id: string;
      headers: string[];
      preview: Row[];
      row_count: number;
    } | null>(null),
    [error, setError] = useState(""),
    [pending, setPending] = useState(false),
    [mapping, setMapping] = useState({
      name_column: "",
      segment_column: "",
      region_column: "",
    }),
    [done, setDone] = useState(false);
  async function upload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPending(true);
    setError("");
    try {
      const body = new FormData(e.currentTarget);
      const r = await fetch("/api/v1/imports/preview", {
        method: "POST",
        body,
      });
      const data = await r.json();
      if (!r.ok) throw new Error(JSON.stringify(data.detail));
      setPreview(data);
      setMapping({
        name_column:
          data.headers.find((h: string) => /name/i.test(h)) || data.headers[0],
        segment_column:
          data.headers.find((h: string) => /segment/i.test(h)) ||
          data.headers[0],
        region_column:
          data.headers.find((h: string) => /region/i.test(h)) ||
          data.headers[0],
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setPending(false);
    }
  }
  async function confirm() {
    setPending(true);
    setError("");
    try {
      await api(`imports/${preview?.id}/confirm`, mapping);
      setDone(true);
      onSaved();
    } catch (e) {
      setError(String(e));
    } finally {
      setPending(false);
    }
  }
  if (done)
    return (
      <div className="empty">
        <Check size={32} />
        <h3>Import committed.</h3>
        <p>Validated accounts were inserted in a single transaction.</p>
      </div>
    );
  return (
    <div className="form-stack">
      <div className="notice">
        Account imports are available. Additional entity mappings are being
        implemented; unsupported data is not silently loaded.
      </div>
      {!preview ? (
        <form className="form-stack" onSubmit={upload}>
          <label>
            Choose a CSV or Excel file
            <input
              aria-label="Import file"
              name="file"
              type="file"
              accept=".csv,.xlsx"
              required
            />
          </label>
          <p>
            Up to 2 MB and 10,000 rows. Required fields: name, segment
            (Enterprise / Mid-market / SMB), region.
          </p>
          <button className="button" disabled={pending}>
            {pending ? "Validating…" : "Preview file"}
          </button>
        </form>
      ) : (
        <>
          <h3>{preview.row_count} rows detected</h3>
          <Table rows={preview.preview} />
          {Object.entries(mapping).map(([key, value]) => (
            <label key={key}>
              Map {key.replace("_column", "")}
              <select
                aria-label={`Map ${key.replace("_column", "")}`}
                value={value}
                onChange={(e) =>
                  setMapping({ ...mapping, [key]: e.target.value })
                }
              >
                {preview.headers.map((h) => (
                  <option key={h}>{h}</option>
                ))}
              </select>
            </label>
          ))}
          <p>
            Review the column mapping. Confirmation validates every row before
            inserting any records.
          </p>
          <button className="button" disabled={pending} onClick={confirm}>
            {pending ? "Committing…" : "Confirm account import"}
          </button>
        </>
      )}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

function ModelRegistry({ models }: { models: Row[] }) {
  if (!models.length)
    return (
      <div className="empty">
        <strong>No registered models.</strong>
        <p>
          Training and evaluation records appear here after a completed run.
        </p>
      </div>
    );
  return (
    <div className="model-registry">
      {models.map((m) => {
        const p = m.payload as Row;
        const metrics = (p.metrics || {}) as Row;
        return (
          <article className="model-record" key={String(m.id)}>
            <div>
              <span className="eyebrow">
                {String(p.kind).replaceAll("_", " ")}
              </span>
              <span className="badge jade">{String(m.status)}</span>
            </div>
            <h3>{String(p.name)}</h3>
            <small>Trained {timestamp(m.created_at)}</small>
            <dl>
              {Object.entries(metrics).map(([k, v]) => (
                <div key={k}>
                  <dt>{k.replaceAll("_", " ")}</dt>
                  <dd>{numeric(v, /auc|brier/.test(k) ? 3 : 2)}</dd>
                </div>
              ))}
            </dl>
            <p>{String(p.scope || "Synthetic demonstration model.")}</p>
            {p.mlflow_run_id ? (
              <small>
                Tracked in MLflow · {String(p.mlflow_run_id).slice(0, 8)}
              </small>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}
