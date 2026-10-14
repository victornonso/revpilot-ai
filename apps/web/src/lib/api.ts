export type Row = Record<string, unknown>;
export type Metric = {
  id: string;
  label: string;
  value: number | string | null;
  unit: string;
  definition: string;
};
export type ChartSpec = {
  title: string;
  kind: string;
  unit: string;
  span: number;
  rows: Row[];
};
export type Data = {
  metrics: Metric[];
  charts: ChartSpec[];
  table: Row[];
  total: number;
  page: number;
  meta: {
    organisation: string;
    demo: boolean;
    stale: boolean;
    refreshed_at: string;
    financial_basis: string;
  };
  [key: string]: unknown;
};
export async function api<T = Data>(
  route: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch("/api/v1/" + route, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    signal: signal
      ? AbortSignal.any([signal, AbortSignal.timeout(45000)])
      : AbortSignal.timeout(45000),
  });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Service unavailable" }));
    throw new Error(
      typeof error.detail === "string"
        ? error.detail
        : JSON.stringify(error.detail),
    );
  }
  return response.json();
}
export function numeric(value: unknown, digits = 2) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  return Number.isFinite(n)
    ? n.toLocaleString("en-GB", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      })
    : String(value);
}
export function metricDisplay(metric: Metric) {
  if (metric.value === null) return "—";
  const n = Number(metric.value);
  if (metric.unit.startsWith("GBP")) {
    const scale = Math.abs(n) >= 1e6 ? 1e6 : Math.abs(n) >= 1e3 ? 1e3 : 1;
    return (
      "£" +
      numeric(n / scale) +
      (scale === 1e6 ? "m" : scale === 1e3 ? "k" : "")
    );
  }
  return numeric(n, /accounts|count/.test(metric.unit) ? 0 : 2);
}
export function timestamp(value: unknown) {
  if (!value) return "Not available";
  const date = new Date(String(value));
  return Number.isFinite(date.getTime())
    ? new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "Europe/London",
        timeZoneName: "short",
      }).format(date)
    : String(value);
}
export function display(key: string, value: unknown) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string" && /^\d{4}-\d\d-\d\dT/.test(value))
    return timestamp(value);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") return JSON.stringify(value);
  if (
    typeof value === "number" ||
    (typeof value === "string" && /^-?\d+(\.\d+)?$/.test(value))
  )
    return numeric(value, /count|days|version|^id$/.test(key) ? 0 : 2);
  return String(value);
}
