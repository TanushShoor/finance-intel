import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getContract } from "../api/client";
import type { ContractDetail } from "../types";

export function Summary() {
  const { id } = useParams();
  const [c, setC] = useState<ContractDetail | null>(null);
  useEffect(() => { getContract(Number(id)).then(setC); }, [id]);
  const s = c?.analysis?.summary;
  if (!s) return <div className="p-6">No summary yet.</div>;
  return (
    <div className="max-w-2xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-bold">Executive Summary</h1>
      <section><h2 className="font-semibold">What it covers</h2><p>{s.coverage}</p></section>
      <section><h2 className="font-semibold">Who carries the risk</h2><p>{s.who_carries_risk}</p></section>
      <section><h2 className="font-semibold">Key commercial terms</h2>
        <ul className="list-disc ml-5">{s.key_commercial_terms.map((t, i) => <li key={i}>{t}</li>)}</ul></section>
      <section><h2 className="font-semibold">Top 3 issues to negotiate</h2>
        <ol className="list-decimal ml-5">{s.top_issues.map((t, i) => <li key={i}>{t}</li>)}</ol></section>
    </div>
  );
}
