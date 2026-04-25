import type { SystemStatus } from "../api/types";

export function StatusBar({
  tab,
  evThreshold,
  status,
  date,
  raceCount,
}: {
  tab: string;
  evThreshold: number;
  status?: SystemStatus | null;
  date: string;
  raceCount?: number;
}) {
  return (
    <div className="term-statusbar">
      <span className="seg">
        <span className="k">CMD</span>
        <span className="v">{tab.toUpperCase()}</span>
      </span>
      <span className="seg">
        <span className="k">DATE</span>
        <span className="v">{date}</span>
      </span>
      <span className="seg">
        <span className="k">RACES</span>
        <span className="v">{raceCount ?? "—"}</span>
      </span>
      <span className="seg">
        <span className="k">EV-THR</span>
        <span className="v amb">{evThreshold.toFixed(2)}</span>
      </span>
      <span className="seg">
        <span className="k">PRESET</span>
        <span className="v">{status?.preset ?? "—"}</span>
      </span>
      <span className="seg">
        <span className="k">FEAT</span>
        <span className="v">{status?.feature_count ?? "—"}</span>
      </span>
      <span className="seg">
        <span className="k">MODEL</span>
        <span className="v ok">
          {status?.model_name ?? "—"}
          {status?.model_version ? `@${status.model_version}` : ""}
        </span>
      </span>
      <span style={{ marginLeft: "auto" }} className="seg">
        <span className="k">F1</span>
        <span className="v">HELP</span> · <span className="k">/</span>
        <span className="v">SEARCH</span> · <span className="k">G</span>
        <span className="v">GO</span>
      </span>
    </div>
  );
}
