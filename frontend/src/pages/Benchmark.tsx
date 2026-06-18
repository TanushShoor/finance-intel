import { useEffect, useState } from "react";
import { listDocuments, benchmark, compareRisk } from "../api/client";
import type { Benchmark as BenchmarkResult, RiskComparison } from "../types";
import { metricLabel, RISK_STATUS } from "../lib/finance";

export function Benchmark() {
  const [rows, setRows] = useState<any[]>([]);
  const [picked, setPicked] = useState<number[]>([]);
  const [grid, setGrid] = useState<BenchmarkResult | null>(null);
  const [busy, setBusy] = useState(false);

  const [prior, setPrior] = useState<number | "">("");
  const [current, setCurrent] = useState<number | "">("");
  const [diff, setDiff] = useState<RiskComparison | null>(null);
  const [diffBusy, setDiffBusy] = useState(false);

  useEffect(() => {
    listDocuments().then((rs) => setRows(rs.filter((r: any) => r.status === "done")));
  }, []);

  const label = (r: any) => r.company || r.filename;
  const toggle = (id: number) =>
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));

  async function runBenchmark() {
    setBusy(true);
    try {
      setGrid(await benchmark(picked));
    } finally {
      setBusy(false);
    }
  }
  async function runRiskDiff() {
    if (prior === "" || current === "") return;
    setDiffBusy(true);
    try {
      setDiff(await compareRisk(Number(prior), Number(current)));
    } finally {
      setDiffBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="border-b border-line pb-6">
        <div className="eyebrow">Cross-company</div>
        <h1 className="mt-2 font-display text-4xl font-bold tracking-tight">Benchmarking</h1>
      </div>

      {rows.length === 0 && (
        <p className="mt-8 text-sm text-muted">No analysed filings yet.</p>
      )}

      {/* Competitor benchmarking */}
      <section className="mt-8">
        <h2 className="eyebrow">Metric comparison · {picked.length} selected</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {rows.map((r) => {
            const on = picked.includes(r.id);
            return (
              <button
                key={r.id}
                onClick={() => toggle(r.id)}
                aria-pressed={on}
                className={`border px-3 py-1.5 font-mono text-xs uppercase tracking-label transition-colors ${
                  on ? "border-ink bg-ink text-surface" : "border-line bg-surface text-muted hover:text-ink"
                }`}
              >
                {label(r)}
              </button>
            );
          })}
        </div>
        <button
          onClick={runBenchmark}
          disabled={picked.length < 2 || busy}
          className="mt-4 bg-cobalt px-5 py-2 font-mono text-xs uppercase tracking-label text-surface transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          {busy ? "Comparing…" : "Build benchmark"}
        </button>

        {grid && grid.rows.length > 0 && (
          <div className="mt-6 space-y-6">
            <div className="panel overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-line">
                    <th className="px-4 py-2 text-left eyebrow font-normal">Company</th>
                    {grid.metric_names.map((m) => (
                      <th key={m} className="px-4 py-2 text-right font-mono text-[0.68rem] uppercase tracking-label text-muted">
                        {metricLabel(m)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {grid.rows.map((row) => (
                    <tr key={row.company} className="border-b border-line last:border-0">
                      <td className="px-4 py-2 font-display font-semibold">{row.company}</td>
                      {grid.metric_names.map((m) => (
                        <td key={m} className="px-4 py-2 text-right font-mono tabular-nums">
                          {row.values[m] ?? "—"}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {grid.highlights.length > 0 && (
              <div className="panel p-5">
                <h3 className="eyebrow">Highlights</h3>
                <ul className="mt-3 space-y-2">
                  {grid.highlights.map((h, i) => (
                    <li key={i} className="border-l-2 border-line pl-3 text-sm leading-relaxed text-ink/90">{h}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Risk-factor period comparison */}
      <section className="mt-12 border-t border-line pt-8">
        <h2 className="eyebrow">Risk-factor comparison (period over period)</h2>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <label className="block">
            <span className="font-mono text-[0.62rem] uppercase tracking-label text-muted">Prior</span>
            <select value={prior} onChange={(e) => setPrior(e.target.value === "" ? "" : Number(e.target.value))}
              className="mt-1 block border border-line bg-surface px-3 py-2 font-mono text-sm">
              <option value="">—</option>
              {rows.map((r) => <option key={r.id} value={r.id}>{label(r)} {r.period ? `(${r.period})` : ""}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="font-mono text-[0.62rem] uppercase tracking-label text-muted">Current</span>
            <select value={current} onChange={(e) => setCurrent(e.target.value === "" ? "" : Number(e.target.value))}
              className="mt-1 block border border-line bg-surface px-3 py-2 font-mono text-sm">
              <option value="">—</option>
              {rows.map((r) => <option key={r.id} value={r.id}>{label(r)} {r.period ? `(${r.period})` : ""}</option>)}
            </select>
          </label>
          <button
            onClick={runRiskDiff}
            disabled={prior === "" || current === "" || prior === current || diffBusy}
            className="bg-cobalt px-5 py-2 font-mono text-xs uppercase tracking-label text-surface transition-opacity hover:opacity-90 disabled:opacity-40"
          >
            {diffBusy ? "Comparing…" : "Compare risks"}
          </button>
        </div>

        {diff && (
          <ul className="mt-6 space-y-2">
            {diff.deltas.map((d, i) => {
              const meta = RISK_STATUS[d.status] ?? RISK_STATUS.unchanged;
              return (
                <li key={i} className="panel flex items-start gap-3 p-4">
                  <span
                    className="mt-0.5 border px-1.5 py-0.5 font-mono text-[0.6rem] uppercase tracking-label"
                    style={{ color: meta.color, borderColor: meta.color }}
                  >
                    {meta.label}
                  </span>
                  <div>
                    <h3 className="font-display font-semibold leading-tight">{d.title}</h3>
                    {d.rationale && <p className="mt-1 text-sm leading-relaxed text-muted">{d.rationale}</p>}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
