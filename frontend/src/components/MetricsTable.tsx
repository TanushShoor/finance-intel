import type { Metric } from "../types";
import { metricLabel } from "../lib/finance";

/** Pivots extracted metrics into a name × period table, with a change column
 *  when a row carries two or more numeric values (YoY / QoQ). */
export function MetricsTable({ metrics }: { metrics: Metric[] }) {
  if (metrics.length === 0)
    return (
      <p className="panel p-5 text-sm text-muted">
        No financial figures were extracted from this document.
      </p>
    );

  const periods: string[] = [];
  const names: string[] = [];
  const cell = new Map<string, Metric>();
  for (const m of metrics) {
    const p = m.period ?? "—";
    if (!periods.includes(p)) periods.push(p);
    if (!names.includes(m.name)) names.push(m.name);
    const key = `${m.name}|${p}`;
    if (!cell.has(key)) cell.set(key, m);
  }

  function change(name: string): { text: string; up: boolean } | null {
    const nums = periods
      .map((p) => cell.get(`${name}|${p}`)?.value_numeric)
      .filter((v): v is number => typeof v === "number");
    if (nums.length < 2) return null;
    const first = nums[0];
    const last = nums[nums.length - 1];
    if (!first) return null;
    const pct = ((last - first) / Math.abs(first)) * 100;
    return { text: `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`, up: pct >= 0 };
  }

  return (
    <div className="panel overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-line">
            <th className="px-4 py-2 text-left eyebrow font-normal">Metric</th>
            {periods.map((p) => (
              <th key={p} className="px-4 py-2 text-right font-mono text-[0.68rem] uppercase tracking-label text-muted">
                {p}
              </th>
            ))}
            <th className="px-4 py-2 text-right eyebrow font-normal">Δ</th>
          </tr>
        </thead>
        <tbody>
          {names.map((name) => {
            const c = change(name);
            return (
              <tr key={name} className="border-b border-line last:border-0">
                <td className="px-4 py-2 font-medium">{metricLabel(name)}</td>
                {periods.map((p) => (
                  <td key={p} className="px-4 py-2 text-right font-mono tabular-nums">
                    {cell.get(`${name}|${p}`)?.value ?? "—"}
                  </td>
                ))}
                <td
                  className="px-4 py-2 text-right font-mono tabular-nums"
                  style={{ color: c ? (c.up ? "#1E7A66" : "#B23322") : undefined }}
                >
                  {c ? c.text : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
