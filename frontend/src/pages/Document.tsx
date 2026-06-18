import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getDocument } from "../api/client";
import type { ContractDetail, DocumentBlock, OutlineEntry } from "../types";

/** Stable anchor id for a heading block, so the outline can jump to it. */
function anchorId(number: string | null, idx: number) {
  return `sec-${number ? number.replace(/[^\w.]/g, "") : idx}`;
}

function Notice({ title, body }: { title: string; body?: string }) {
  return (
    <div className="mx-auto max-w-5xl px-6 py-16">
      <div className="eyebrow">{title}</div>
      {body && <p className="mt-3 font-mono text-sm text-muted">{body}</p>}
    </div>
  );
}

function Block({ block, idx }: { block: DocumentBlock; idx: number }) {
  if (block.type === "header")
    return (
      <h2
        id={anchorId(block.number, idx)}
        className="scroll-mt-24 border-t border-line pt-8 font-display text-2xl font-bold leading-tight tracking-tight"
      >
        {block.number && (
          <span className="mr-3 font-mono text-base font-medium text-muted">
            {block.number}
          </span>
        )}
        {block.text}
      </h2>
    );
  if (block.type === "subheader")
    return (
      <h3
        id={anchorId(block.number, idx)}
        className="scroll-mt-24 font-display text-lg font-semibold leading-snug"
      >
        {block.number && (
          <span className="mr-2 font-mono text-sm font-medium text-muted">
            {block.number}
          </span>
        )}
        {block.text}
      </h3>
    );
  return <p className="leading-[1.75] text-ink/90">{block.text}</p>;
}

export function Document() {
  const { id } = useParams();
  const [c, setC] = useState<ContractDetail | null>(null);

  useEffect(() => {
    const poll = () => getDocument(Number(id)).then(setC);
    poll();
    const t = setInterval(poll, 2000);
    return () => clearInterval(t);
  }, [id]);

  if (!c) return <Notice title="Loading document…" />;
  if (c.status === "failed")
    return <Notice title="Analysis failed" body={c.error ?? "Unknown error."} />;
  if (c.status !== "done")
    return <Notice title={`${c.status}…`} body="Reconstructing the document structure." />;

  const doc = c.analysis?.structure;
  if (!doc || doc.blocks.length === 0)
    return <Notice title="No structure available" body="This document produced no readable structure." />;

  // Link each outline entry to its heading block. Synthesis de-dups headings, so
  // match by section number first, then by heading text, before giving up.
  const byNumber = new Map<string, string>();
  const byText = new Map<string, string>();
  doc.blocks.forEach((b, i) => {
    if (b.type === "paragraph") return;
    const id = anchorId(b.number, i);
    if (b.number && !byNumber.has(b.number)) byNumber.set(b.number, id);
    const t = b.text.trim().toLowerCase();
    if (t && !byText.has(t)) byText.set(t, id);
  });
  const anchorFor = (entry: OutlineEntry) => {
    if (entry.number && byNumber.has(entry.number)) return byNumber.get(entry.number)!;
    const t = entry.title.trim().toLowerCase();
    if (byText.has(t)) return byText.get(t)!;
    return undefined;
  };

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="border-b border-line pb-6">
        <Link
          to={`/contracts/${id}`}
          className="font-mono text-xs uppercase tracking-label text-cobalt hover:underline"
        >
          ← Analysis report
        </Link>
        <h1 className="mt-3 font-display text-4xl font-bold leading-tight tracking-tight">
          {doc.title || c.filename}
        </h1>
      </div>

      <div className="mt-8 grid gap-10 lg:grid-cols-[240px_minmax(0,1fr)]">
        {/* Outline / table of contents */}
        <aside className="order-2 lg:order-1">
          <nav className="lg:sticky lg:top-24">
            <h2 className="eyebrow">Contents</h2>
            {doc.outline.length === 0 ? (
              <p className="mt-3 text-sm text-muted">No outline.</p>
            ) : (
              <ol className="mt-3 space-y-1.5">
                {doc.outline.map((o, i) => {
                  const target = anchorFor(o);
                  const inner = (
                    <>
                      {o.number && (
                        <span className="font-mono text-xs">{o.number}</span>
                      )}
                      <span>{o.title}</span>
                    </>
                  );
                  return (
                    <li key={i} className={o.level === 2 ? "pl-4" : ""}>
                      {target ? (
                        <a
                          href={`#${target}`}
                          className="flex gap-2 text-sm leading-snug text-muted hover:text-cobalt"
                        >
                          {inner}
                        </a>
                      ) : (
                        <span className="flex gap-2 text-sm leading-snug text-muted">
                          {inner}
                        </span>
                      )}
                    </li>
                  );
                })}
              </ol>
            )}
          </nav>
        </aside>

        {/* Document body — a comfortable reading column. */}
        <article className="order-1 max-w-[68ch] space-y-5 lg:order-2">
          {doc.blocks.map((b, i) => (
            <Block key={i} block={b} idx={i} />
          ))}
        </article>
      </div>
    </div>
  );
}
