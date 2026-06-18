import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getContract } from "../api/client";
import type { ContractDetail } from "../types";
import { RiskGauge } from "../components/RiskGauge";
import { ClauseCard } from "../components/ClauseCard";

export function Analysis() {
  const { id } = useParams();
  const [c, setC] = useState<ContractDetail | null>(null);
  useEffect(() => {
    const poll = () => getContract(Number(id)).then(setC);
    poll(); const t = setInterval(poll, 2000); return () => clearInterval(t);
  }, [id]);
  if (!c) return <div className="p-6">Loading…</div>;
  if (c.status !== "done") return <div className="p-6">Status: {c.status} {c.error}</div>;
  const a = c.analysis!;
  const devBy = Object.fromEntries(a.deviations.map(d => [d.clause_type, d]));
  const riskBy = Object.fromEntries(a.risks.map(r => [r.clause_type, r]));
  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{c.filename}</h1>
        <Link className="text-blue-600" to={`/contracts/${id}/summary`}>Executive summary →</Link>
      </div>
      <RiskGauge score={a.overall_risk_score} />
      <div className="grid grid-cols-2 gap-2 text-sm">
        {Object.entries(a.category_breakdown).map(([k, v]) =>
          <div key={k} className="flex justify-between border rounded px-3 py-1">
            <span className="capitalize">{k}</span><span className="font-bold">{v}</span></div>)}
      </div>
      <div className="space-y-3">
        {a.clauses.map(cl => <ClauseCard key={cl.type} clause={cl}
          deviation={devBy[cl.type]} risk={riskBy[cl.type]} />)}
      </div>
    </div>
  );
}
