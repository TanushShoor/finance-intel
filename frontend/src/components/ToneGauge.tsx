import type { ToneAnalysis } from "../types";
import { SENTIMENT } from "../lib/finance";

/** Management-tone instrument readout: overall sentiment + a confidence meter. */
export function ToneGauge({ tone }: { tone: ToneAnalysis }) {
  const s = SENTIMENT[tone.overall_sentiment] ?? SENTIMENT.neutral;
  return (
    <div className="panel p-5">
      <div className="flex items-start justify-between">
        <div>
          <div className="eyebrow">Management tone</div>
          <div
            className="mt-2 font-display text-3xl font-bold leading-none"
            style={{ color: s.color }}
          >
            {s.label}
          </div>
        </div>
        <span className="font-mono text-[0.68rem] uppercase tracking-label text-muted">
          hedging: {tone.hedging_level}
        </span>
      </div>

      <div className="mt-4">
        <div className="flex items-baseline justify-between">
          <span className="eyebrow">Confidence</span>
          <span className="font-mono text-sm font-semibold tabular-nums" style={{ color: s.color }}>
            {tone.confidence_score}
          </span>
        </div>
        <div className="relative mt-1 h-1.5 w-full bg-sunken border border-line">
          <span
            className="absolute top-1/2 h-3.5 w-1 -translate-x-1/2 -translate-y-1/2"
            style={{ left: `${tone.confidence_score}%`, background: s.color }}
          />
        </div>
      </div>

      {tone.summary && <p className="mt-4 text-sm leading-relaxed text-ink/90">{tone.summary}</p>}
    </div>
  );
}
