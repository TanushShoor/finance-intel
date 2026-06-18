import { useEffect, useRef, useState } from "react";
import type { Progress } from "../types";
import { STAGE_LABELS } from "../lib/finance";

type Card = { n: number; text: string };

const STAGE_ORDER = ["structuring", "identifying", "metrics", "tone", "risk_factors", "memo"];

/** Live analysis progress. During the chunked structuring stage, each parsed
 *  chunk rises from the bottom; later stages show their label + a step tracker. */
export function ChunkProgress({ progress }: { progress: Progress | null }) {
  const [cards, setCards] = useState<Card[]>([]);
  const lastN = useRef<number>(0);

  const streaming = !!progress && progress.total > 0;

  useEffect(() => {
    if (!streaming || !progress) return;
    if (progress.current === lastN.current) return;
    lastN.current = progress.current;
    setCards((prev) => [...prev, { n: progress.current, text: progress.preview }].slice(-4));
  }, [streaming, progress?.current, progress?.preview]);

  const stage = progress?.stage ?? "";
  const heading = STAGE_LABELS[stage] ?? "Analysing";
  const stageIdx = STAGE_ORDER.indexOf(stage);
  const pct = streaming && progress ? Math.round((progress.current / progress.total) * 100) : 0;

  return (
    <div className="mx-auto max-w-5xl px-6 py-16">
      <div className="eyebrow">{heading}</div>

      {/* Stage tracker */}
      <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1">
        {STAGE_ORDER.map((s, i) => (
          <span
            key={s}
            className={`font-mono text-[0.62rem] uppercase tracking-label ${
              i < stageIdx ? "text-muted line-through" : i === stageIdx ? "text-ink" : "text-line"
            }`}
          >
            {STAGE_LABELS[s].replace(/^(\w+).*/, "$1")}
          </span>
        ))}
      </div>

      {streaming && progress ? (
        <>
          <div className="mt-6 flex items-baseline gap-3">
            <span className="font-mono text-3xl font-semibold tabular-nums">
              {String(progress.current).padStart(2, "0")}
              <span className="text-muted"> / {String(progress.total).padStart(2, "0")}</span>
            </span>
            <span className="font-mono text-xs uppercase tracking-label text-muted">
              chunks parsed
            </span>
          </div>
          <div className="mt-3 h-1 w-full max-w-md bg-sunken">
            <span
              className="block h-full bg-ink transition-[width] duration-500 ease-out"
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="mt-8 flex h-64 max-w-xl flex-col justify-end gap-2 overflow-hidden">
            {cards.map((c, i) => {
              const depth = cards.length - 1 - i;
              const opacity = depth === 0 ? 1 : Math.max(0.25, 1 - depth * 0.28);
              return (
                <div
                  key={c.n}
                  className={`panel px-4 py-3 ${depth === 0 ? "chunk-rise" : ""}`}
                  style={{ opacity }}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[0.68rem] uppercase tracking-label text-muted">
                      Chunk {String(c.n).padStart(2, "0")}
                    </span>
                    {depth === 0 && (
                      <span className="font-mono text-[0.68rem] uppercase tracking-label text-cobalt">
                        parsing…
                      </span>
                    )}
                  </div>
                  <p className="mt-1 line-clamp-2 font-mono text-xs leading-relaxed text-ink/80">
                    {c.text || "…"}
                  </p>
                </div>
              );
            })}
          </div>
        </>
      ) : (
        <p className="mt-6 font-mono text-sm text-muted">working…</p>
      )}
    </div>
  );
}
