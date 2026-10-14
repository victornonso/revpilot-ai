"use client";
import { Row, display } from "@/lib/api";
export default function Table({
  rows,
  onRow,
  onSort,
}: {
  rows: Row[];
  onRow?: (r: Row) => void;
  onSort?: (key: string) => void;
}) {
  if (!rows.length)
    return (
      <div className="empty">
        <strong>No records in this view.</strong>
        <p>Try another reporting period or change the filters.</p>
      </div>
    );
  const keys = Object.keys(rows[0]).filter(
    (k) => !["id", "org_id", "payload", "record_hash"].includes(k),
  );
  return (
    <div
      className="table-scroll"
      tabIndex={0}
      role="region"
      aria-label="Scrollable analytical data"
    >
      <table>
        <thead>
          <tr>
            {keys.map((k) => (
              <th key={k} scope="col">
                {onSort ? (
                  <button onClick={() => onSort(k)}>
                    {k.replaceAll("_", " ")} ↕
                  </button>
                ) : (
                  k.replaceAll("_", " ")
                )}
              </th>
            ))}
            {onRow && <th scope="col">Details</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={String(r.id || i)}>
              {keys.map((k) => (
                <td key={k}>
                  {["status", "stage", "risk"].includes(k) ? (
                    <span
                      className={`badge ${/fail|stall|pending|overdue/i.test(String(r[k])) ? "amber" : /success|pass|execut|won|approved/i.test(String(r[k])) ? "jade" : ""}`}
                    >
                      {display(k, r[k])}
                    </span>
                  ) : (
                    display(k, r[k])
                  )}
                </td>
              ))}
              {onRow && (
                <td>
                  <button
                    className="table-action"
                    onClick={() => onRow(r)}
                    aria-label={`Inspect ${r.opportunity || r.account || r.name || "record"}`}
                  >
                    Inspect ↗
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
