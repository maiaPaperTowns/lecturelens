import { NavLink, Outlet } from "react-router-dom";

import { IS_DEMO } from "../services/api";

const NAV = [
  { to: "/", label: "Home", end: true },
  { to: "/upload", label: "Upload" },
  { to: "/lectures", label: "Lectures" },
  { to: "/metrics", label: "Metrics" },
];

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-20 border-b border-line bg-paper/85 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
          <NavLink to="/" className="flex items-baseline gap-2">
            <span className="font-display text-xl font-semibold text-ink">LectureLens</span>
            <span className="hidden h-1.5 w-1.5 rounded-full bg-ember sm:block" />
          </NavLink>
          <nav className="flex items-center gap-1">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `rounded-full px-3 py-1.5 text-[0.7rem] font-medium uppercase tracking-label transition ${
                    isActive ? "text-wine" : "text-ink-faint hover:text-ink"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-5 py-10">
        <Outlet />
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-5 py-6 text-[0.7rem] uppercase tracking-label text-ink-faint">
          <span>LectureLens</span>
          <span>Offline PyTorch + scikit-learn study-map pipeline</span>
          {IS_DEMO && <span className="text-ember-ink">Live demo, read only</span>}
        </div>
      </footer>
    </div>
  );
}
