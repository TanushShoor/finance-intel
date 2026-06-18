import { NavLink, Outlet } from "react-router-dom";

const tabs = [
  { to: "/", label: "Filings", end: true },
  { to: "/benchmark", label: "Benchmark", end: false },
];

export function Shell() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-surface/85 backdrop-blur sticky top-0 z-10">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <NavLink to="/" className="flex items-baseline gap-2">
            <span className="font-display text-xl font-bold tracking-tight text-ink">
              LEDGER
            </span>
            <span className="eyebrow hidden sm:inline">financial document analyst</span>
          </NavLink>
          <nav className="flex items-center gap-1">
            {tabs.map((t) => (
              <NavLink
                key={t.to}
                to={t.to}
                end={t.end}
                className={({ isActive }) =>
                  `px-3 py-1.5 font-mono text-xs uppercase tracking-label transition-colors ${
                    isActive ? "bg-ink text-surface" : "text-muted hover:text-ink"
                  }`
                }
              >
                {t.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
