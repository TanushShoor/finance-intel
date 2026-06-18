import type { ExtractedClause, Deviation, ClauseRisk } from "../types";
import { DeviationBadge } from "./DeviationBadge";

export function ClauseCard({ clause, deviation, risk }:
  { clause: ExtractedClause; deviation?: Deviation; risk?: ClauseRisk }) {
  if (!clause.present)
    return <div className="p-3 rounded border text-gray-400">
      {clause.type} — not present</div>;
  return (
    <div className="p-4 rounded-xl border space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold capitalize">{clause.type.replace(/_/g, " ")}</h3>
        <div className="flex items-center gap-2">
          <DeviationBadge classification={deviation?.classification} />
          {risk && <span className="text-sm font-bold">{risk.score}</span>}
        </div>
      </div>
      <p className="text-sm text-gray-700">{clause.text}</p>
      {deviation && <p className="text-xs text-gray-500 italic">{deviation.rationale}</p>}
    </div>
  );
}
