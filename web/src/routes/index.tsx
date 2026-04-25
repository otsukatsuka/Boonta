import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMemo } from "react";
import { Panel } from "../components/Panel";
import { Umaban } from "../components/Umaban";
import { useEvThreshold } from "../components/TweaksPanel";
import { usePredictBatch, useRaces } from "../hooks/useApi";
import type { RaceListItem } from "../api/types";

function todayJst(): string {
  const tz = new Date(Date.now() + 9 * 60 * 60 * 1000);
  return tz.toISOString().slice(0, 10);
}

function DashboardScreen() {
  const navigate = useNavigate();
  const [evThreshold] = useEvThreshold();
  const search = Route.useSearch();
  const date = search.date ?? todayJst();
  const setDate = (d: string) =>
    navigate({ to: "/", search: { date: d }, replace: true });
  const racesQ = useRaces(date);
  const predictBatch = usePredictBatch();
  const races: RaceListItem[] = racesQ.data ?? [];

  const paceCounts = useMemo(() => {
    const counts: Record<string, number> = { H: 0, M: 0, S: 0 };
    races.forEach((r) => {
      if (r.pace && r.pace in counts) counts[r.pace]++;
    });
    return counts;
  }, [races]);

  const signals = races
    .filter((r) => r.best_ev_tan != null && r.best_ev_tan >= evThreshold)
    .slice(0, 4);

  function openRace(race_key: string) {
    navigate({ to: "/race/$raceKey", params: { raceKey: race_key } });
  }

  return (
    <div
      className="term-grid"
      style={{
        gridTemplateColumns: "minmax(0, 2fr) minmax(0, 1fr)",
        gridTemplateRows: "auto minmax(0, 1fr)",
      }}
    >
      <div
        style={{
          gridColumn: "1 / -1",
          display: "flex",
          gap: 8,
          padding: "8px 12px",
          background: "var(--bg-1)",
          borderBottom: "1px solid var(--line)",
          alignItems: "center",
        }}
      >
        <span style={{ color: "var(--amber)", fontFamily: "var(--mono)" }}>
          $ boonta
        </span>
        <span className="dim">predict</span>
        <span>--date</span>
        <input
          className="term-input"
          type="date"
          style={{ width: 150 }}
          value={date}
          onChange={(e) => e.target.value && setDate(e.target.value)}
        />
        <span>--ev-threshold</span>
        <input
          className="term-input"
          style={{ width: 60 }}
          value={evThreshold.toFixed(2)}
          readOnly
        />
        <button
          className="term-btn primary"
          disabled={predictBatch.isPending || races.length === 0}
          onClick={() => predictBatch.mutate(date)}
        >
          {predictBatch.isPending ? "RUNNING…" : "RUN"}
        </button>
        <span className="dim" style={{ marginLeft: "auto" }}>
          {racesQ.isLoading
            ? "loading…"
            : racesQ.error
              ? "error"
              : `${races.length} races`}
        </span>
      </div>

      <Panel
        title="本日のレース"
        meta={`${races.length} races · ${new Set(races.map((r) => r.venue)).size} tracks`}
        flush
      >
        <table className="dt">
          <thead>
            <tr>
              <th className="l">場 / R</th>
              <th className="l">レース名</th>
              <th>距離</th>
              <th>頭</th>
              <th>馬場</th>
              <th>ペース</th>
              <th>本命</th>
              <th>P(複)</th>
              <th>EV単</th>
              <th>EV複</th>
              <th>発走</th>
              <th>SIG</th>
            </tr>
          </thead>
          <tbody>
            {races.map((r) => {
              const evGood = (r.best_ev_tan ?? 0) >= evThreshold;
              return (
                <tr
                  key={r.race_key}
                  className="clickable"
                  onClick={() => openRace(r.race_key)}
                >
                  <td className="l">
                    <span className="bold">{r.venue}</span>{" "}
                    <span className="dim">{r.race_no}R</span>
                  </td>
                  <td className="l">
                    <span className="bold">{r.name ?? "—"}</span>{" "}
                    {r.grade && (
                      <span
                        className={
                          "tag " +
                          (r.grade === "G1"
                            ? "amber"
                            : r.grade === "G2"
                              ? "cyan"
                              : "")
                        }
                      >
                        {r.grade}
                      </span>
                    )}
                  </td>
                  <td>{r.distance ? `${r.surface ?? ""}${r.distance}` : "—"}</td>
                  <td>{r.head_count ?? "—"}</td>
                  <td className="dim">
                    {r.condition ?? "—"}/{r.weather ?? "—"}
                  </td>
                  <td>
                    {r.pace ? (
                      <span className={"pace-pill " + r.pace}>{r.pace}</span>
                    ) : (
                      <span className="dim">—</span>
                    )}
                  </td>
                  <td className="l">
                    {r.ml_top ? (
                      <span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
                        <Umaban
                          n={r.ml_top.horse_number}
                          waku={Math.ceil(r.ml_top.horse_number / 2)}
                          sm
                        />
                        <span>{r.ml_top.name}</span>
                      </span>
                    ) : (
                      <span className="dim">未予測</span>
                    )}
                  </td>
                  <td className="amb tnum bold">
                    {r.ml_top ? (r.ml_top.prob * 100).toFixed(1) : "—"}
                  </td>
                  <td className={"tnum " + (evGood ? "pos bold" : "dim")}>
                    {r.best_ev_tan != null ? r.best_ev_tan.toFixed(2) : "—"}
                    {evGood ? " ★" : ""}
                  </td>
                  <td
                    className={
                      "tnum " +
                      ((r.best_ev_fuku ?? 0) >= evThreshold ? "pos" : "dim")
                    }
                  >
                    {r.best_ev_fuku != null ? r.best_ev_fuku.toFixed(2) : "—"}
                  </td>
                  <td className="dim tnum">{r.post_time ?? "—"}</td>
                  <td>
                    {evGood ? (
                      <span className="tag solid-amber">BUY</span>
                    ) : (r.best_ev_tan ?? 0) >= 0.9 ? (
                      <span className="tag amber">WATCH</span>
                    ) : (
                      <span className="tag">SKIP</span>
                    )}
                  </td>
                </tr>
              );
            })}
            {races.length === 0 && !racesQ.isLoading && (
              <tr>
                <td colSpan={12} style={{ padding: 24 }} className="dim">
                  データなし。 <code>python cli.py db ingest-all --date YYMMDD</code> で取り込んでね。
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Panel>

      <div
        style={{
          display: "grid",
          gridTemplateRows: "auto auto 1fr",
          gap: 1,
          background: "var(--line)",
          minHeight: 0,
        }}
      >
        <Panel title="EV シグナル" meta={`thr=${evThreshold.toFixed(2)}`}>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {signals.length === 0 && (
              <div className="dim">該当レースなし</div>
            )}
            {signals.map((r) => (
              <div
                key={r.race_key}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: "4px 0",
                  borderBottom: "1px dashed var(--bg-3)",
                }}
              >
                <span>
                  <span className="bold">
                    {r.venue}
                    {r.race_no}R
                  </span>{" "}
                  <span className="dim">/ {r.name ?? "—"}</span>
                </span>
                <span className="pos tnum bold">
                  EV {r.best_ev_tan?.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="ペース予想 分布" meta={`${races.length} races`}>
          <div style={{ display: "flex", gap: 6 }}>
            {(["H", "M", "S"] as const).map((p) => {
              const c = paceCounts[p];
              return (
                <div
                  key={p}
                  style={{
                    flex: c || 0.3,
                    padding: "6px 8px",
                    background: "var(--bg-2)",
                    border: "1px solid var(--line)",
                  }}
                >
                  <div className={"pace-pill " + p}>{p}</div>
                  <div style={{ fontSize: 18, marginTop: 4 }} className="bold tnum">
                    {c}
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>
        <Panel title="戦略 KPI" meta="2025 backtest" flush>
          <div className="dim" style={{ padding: 12 }}>
            BACKTEST タブで集計表示 (Phase 2)
          </div>
        </Panel>
      </div>
    </div>
  );
}

type DashSearch = { date?: string };

export const Route = createFileRoute("/")({
  validateSearch: (search: Record<string, unknown>): DashSearch => ({
    date:
      typeof search.date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(search.date)
        ? search.date
        : undefined,
  }),
  component: DashboardScreen,
});
