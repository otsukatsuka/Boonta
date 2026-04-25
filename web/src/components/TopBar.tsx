import type { SystemStatus } from "../api/types";

interface Tab { id: string; label: string; }

const TABS: Tab[] = [
  { id: "dash", label: "DASH" },
  { id: "race", label: "RACE" },
  { id: "back", label: "BACKTEST" },
  { id: "data", label: "DATA" },
  { id: "model", label: "MODEL" },
];

export function TopBar({
  tab,
  onTab,
  clock,
  status,
}: {
  tab: string;
  onTab: (id: string) => void;
  clock: string;
  status?: SystemStatus | null;
}) {
  const jrdbState = status ? "SYNC" : "—";
  const modalState = status?.modal_ready ? "READY" : "—";
  return (
    <div className="term-topbar">
      <div className="brand">BOONTA · TERM</div>
      {TABS.map((t) => (
        <div
          key={t.id}
          className={"nav-tab " + (tab === t.id ? "active" : "")}
          onClick={() => onTab(t.id)}
        >
          {t.label}
        </div>
      ))}
      <div className="clock">
        <span>
          <span className="dim">JRDB</span>{" "}
          <span style={{ color: "var(--green)" }}>{jrdbState}</span>
        </span>
        <span className="dim">|</span>
        <span>
          <span className="dim">MODAL</span>{" "}
          <span style={{ color: status?.modal_ready ? "var(--green)" : "var(--fg-3)" }}>
            {modalState}
          </span>
        </span>
        <span className="dim">|</span>
        <span>
          <span className="dim">v2.04.25</span>
        </span>
        <span className="live-dot" />
        <span style={{ color: "var(--fg-1)" }}>{clock}</span>
      </div>
    </div>
  );
}
