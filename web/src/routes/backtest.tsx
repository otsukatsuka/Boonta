import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Panel } from "../components/Panel";
import { Bar } from "../components/Bar";
import { Sparkline } from "../components/Sparkline";
import { EquityCurve } from "../components/EquityCurve";
import { useEvThreshold } from "../components/TweaksPanel";
import {
  useRunBacktest,
  useSensitivity,
  useStrategies,
} from "../hooks/useApi";
import { fmtJPY } from "../lib/format";
import type { Strategy } from "../api/types";

function todayJst(): string {
  const tz = new Date(Date.now() + 9 * 60 * 60 * 1000);
  return tz.toISOString().slice(0, 10);
}
function oneYearAgo(d: string): string {
  const date = new Date(d);
  date.setFullYear(date.getFullYear() - 1);
  return date.toISOString().slice(0, 10);
}

function StrategyRow({
  s,
  selected,
  onClick,
}: {
  s: Strategy;
  selected: boolean;
  onClick: () => void;
}) {
  const pnl = s.returned - s.invested;
  const equityVals = s.equity.map((p) => p.cum);
  return (
    <tr
      className="clickable"
      onClick={onClick}
      style={{
        background: selected ? "oklch(0.22 0.02 75 / 0.3)" : "",
      }}
    >
      <td className="l bold">{s.label}</td>
      <td>
        <span className={"tag " + (s.kind === "EV" ? "amber" : "cyan")}>
          {s.kind}
        </span>
      </td>
      <td
        className={
          "tnum bold " +
          (s.roi >= 100
            ? "pos"
            : s.roi >= 90
              ? "amb"
              : s.roi >= 70
                ? ""
                : "neg")
        }
      >
        {s.roi.toFixed(1)}%
      </td>
      <td>
        {equityVals.length > 0 ? (
          <Sparkline data={equityVals} w={120} h={20} color={pnl >= 0 ? "var(--green)" : "var(--red)"} />
        ) : (
          <span className="dim">—</span>
        )}
      </td>
      <td className="tnum dim">{s.hits.toLocaleString()}</td>
      <td className="tnum dim">
        {s.bet_races.toLocaleString()} / {s.races.toLocaleString()}
      </td>
      <td className={"tnum bold " + (pnl >= 0 ? "pos" : "neg")}>
        {pnl >= 0 ? "+" : ""}
        {fmtJPY(pnl)}
      </td>
    </tr>
  );
}

function Stat({
  k,
  v,
  cls = "",
  big = false,
}: {
  k: string;
  v: string;
  cls?: string;
  big?: boolean;
}) {
  return (
    <div>
      <div
        className="dim"
        style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em" }}
      >
        {k}
      </div>
      <div
        className={"tnum bold " + cls}
        style={{ fontSize: big ? 22 : 14, fontFamily: "var(--mono)" }}
      >
        {v}
      </div>
    </div>
  );
}

function SummaryStats({ s }: { s: Strategy }) {
  const pnl = s.returned - s.invested;
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
      <Stat k="戦略" v={s.label} />
      <Stat k="種別" v={s.kind} />
      <Stat k="期間" v={`${s.date_from} → ${s.date_to}`} />
      <Stat k="モデル" v={s.model_version} />
      <Stat k="レース数" v={s.races.toLocaleString()} />
      <Stat k="購入レース数" v={s.bet_races.toLocaleString()} />
      <Stat k="投資額" v={fmtJPY(s.invested)} />
      <Stat k="回収額" v={fmtJPY(s.returned)} />
      <Stat k="P&L" v={(pnl >= 0 ? "+" : "") + fmtJPY(pnl)} cls={pnl >= 0 ? "pos" : "neg"} />
      <Stat
        k="回収率"
        v={s.roi.toFixed(1) + "%"}
        cls={s.roi >= 100 ? "pos" : s.roi >= 90 ? "amb" : ""}
        big
      />
      <Stat k="的中数" v={s.hits.toLocaleString()} />
      <Stat
        k="的中率"
        v={s.bet_races > 0 ? ((s.hits / s.bet_races) * 100).toFixed(1) + "%" : "—"}
      />
    </div>
  );
}

function SensitivityTable({ runId }: { runId: number | undefined }) {
  const { data, isLoading } = useSensitivity(runId);
  const rows = data ?? [];
  if (isLoading) return <div className="dim">loading…</div>;
  if (rows.length === 0)
    return <div className="dim">この戦略は EV 系ではないため感度なし</div>;
  return (
    <table className="dt">
      <thead>
        <tr>
          <th>THR</th>
          <th>BET RACES</th>
          <th>HITS</th>
          <th>ROI</th>
          <th>HEAT</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.thr}>
            <td className="tnum">{r.thr.toFixed(2)}</td>
            <td className="tnum dim">{r.bet_races?.toLocaleString() ?? "—"}</td>
            <td className="tnum dim">{r.hits ?? "—"}</td>
            <td
              className={
                "tnum bold " +
                (r.roi == null
                  ? "dim"
                  : r.roi >= 100
                    ? "pos"
                    : r.roi >= 90
                      ? "amb"
                      : "")
              }
            >
              {r.roi != null ? r.roi.toFixed(1) + "%" : "—"}
            </td>
            <td>
              {r.roi != null ? (
                <Bar
                  value={Math.max(0, r.roi - 70)}
                  max={40}
                  color={r.roi >= 100 ? "green" : "amber"}
                  w={80}
                />
              ) : (
                <span className="dim">—</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function BacktestScreen() {
  const [evThreshold] = useEvThreshold();
  const today = todayJst();
  const [dateFrom, setDateFrom] = useState(oneYearAgo(today));
  const [dateTo, setDateTo] = useState(today);
  const strategiesQ = useStrategies();
  const runMut = useRunBacktest();
  const all: Strategy[] = strategiesQ.data ?? [];
  const search = Route.useSearch();
  const [selectedId, setSelectedId] = useState<string | null>(
    search.strategy ?? null,
  );

  const selected = useMemo(
    () => all.find((s) => s.id === selectedId) ?? all[0] ?? null,
    [all, selectedId],
  );

  return (
    <div
      className="term-grid"
      style={{
        gridTemplateColumns: "minmax(0,1fr) minmax(0,2fr)",
        gridTemplateRows: "auto 1fr auto",
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
        <span className="dim">backtest run</span>
        <span>--date-range</span>
        <input
          className="term-input"
          type="date"
          style={{ width: 150 }}
          value={dateFrom}
          onChange={(e) => e.target.value && setDateFrom(e.target.value)}
        />
        <input
          className="term-input"
          type="date"
          style={{ width: 150 }}
          value={dateTo}
          onChange={(e) => e.target.value && setDateTo(e.target.value)}
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
          disabled={runMut.isPending}
          onClick={() =>
            runMut.mutate({
              strategy: "all",
              date_from: dateFrom,
              date_to: dateTo,
              ev_threshold: evThreshold,
              sensitivity: true,
            })
          }
        >
          {runMut.isPending ? "RUNNING…" : "RUN"}
        </button>
        <span className="dim" style={{ marginLeft: "auto" }}>
          {runMut.isPending
            ? "evaluating 6 strategies (5–15 min)…"
            : `${all.length} strategies stored`}
        </span>
      </div>

      <Panel title="戦略マトリクス" meta={`${all.length} strategies`} flush>
        {all.length === 0 ? (
          <div className="dim" style={{ padding: 16 }}>
            まだ実行されていません。 RUN ボタン or
            <code> python cli.py backtest run --strategy all --date-range YYYYMMDD YYYYMMDD</code>
          </div>
        ) : (
          <table className="dt">
            <thead>
              <tr>
                <th className="l">戦略</th>
                <th>KIND</th>
                <th>ROI</th>
                <th>EQUITY</th>
                <th>HITS</th>
                <th>BET RACES</th>
                <th>P&L</th>
              </tr>
            </thead>
            <tbody>
              {all.map((s) => (
                <StrategyRow
                  key={s.id}
                  s={s}
                  selected={selected?.id === s.id}
                  onClick={() => setSelectedId(s.id)}
                />
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      <Panel
        title={selected ? `Equity Curve · ${selected.label}` : "Equity Curve"}
        meta={
          selected
            ? `ROI ${selected.roi.toFixed(1)}% · ${selected.bet_races.toLocaleString()} bets`
            : ""
        }
      >
        {selected ? (
          <EquityCurve points={selected.equity} w={700} h={320} />
        ) : (
          <div className="dim">no strategy selected</div>
        )}
      </Panel>

      <Panel
        title="Threshold Sensitivity"
        meta={selected ? `ev_threshold sweep · ${selected.label}` : ""}
      >
        <SensitivityTable runId={selected?.run_id} />
      </Panel>

      <Panel title="戦略サマリー" meta={selected?.label ?? ""}>
        {selected ? (
          <SummaryStats s={selected} />
        ) : (
          <div className="dim">no strategy selected</div>
        )}
      </Panel>
    </div>
  );
}

type BacktestSearch = { strategy?: string };

export const Route = createFileRoute("/backtest")({
  validateSearch: (search: Record<string, unknown>): BacktestSearch => ({
    strategy:
      typeof search.strategy === "string" ? search.strategy : undefined,
  }),
  component: BacktestScreen,
});
