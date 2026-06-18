import { useEffect, useState } from "react";
import { listContracts, compareClause } from "../api/client";

const CLAUSE_TYPES = ["indemnity","limitation_of_liability","governing_law","termination",
  "ip_ownership","payment_terms","confidentiality"];

export function BatchCompare() {
  const [rows, setRows] = useState<any[]>([]);
  const [picked, setPicked] = useState<number[]>([]);
  const [clause, setClause] = useState(CLAUSE_TYPES[2]);
  const [result, setResult] = useState<any>(null);
  useEffect(() => { listContracts().then(rs => setRows(rs.filter((r:any)=>r.status==="done"))); }, []);

  const toggle = (id: number) =>
    setPicked(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id]);

  async function run() { setResult(await compareClause(picked, clause)); }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-bold">Batch Clause Comparison</h1>
      <div className="flex flex-wrap gap-2">
        {rows.map(r => <button key={r.id} onClick={() => toggle(r.id)}
          className={`px-3 py-1 rounded border ${picked.includes(r.id) ? "bg-blue-600 text-white" : ""}`}>
          {r.filename}</button>)}
      </div>
      <select value={clause} onChange={e => setClause(e.target.value)} className="border rounded p-2">
        {CLAUSE_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g," ")}</option>)}
      </select>
      <button onClick={run} disabled={picked.length < 2}
        className="ml-2 px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-40">Compare</button>

      {result && <>
        <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${result.cells.length}, 1fr)` }}>
          {result.cells.map((c: any) => (
            <div key={c.contract_id} className="border rounded-xl p-3 space-y-1">
              <div className="font-semibold">{c.contract_name}</div>
              <div className="text-xs text-gray-500">{c.classification ?? "—"}{c.risk_score != null && ` · risk ${c.risk_score}`}</div>
              <p className="text-sm">{c.text || "(not present)"}</p>
            </div>))}
        </div>
        <div><h2 className="font-semibold">Key differences</h2>
          <ul className="list-disc ml-5">{result.differences.map((d: string, i: number) => <li key={i}>{d}</li>)}</ul></div>
      </>}
    </div>
  );
}
