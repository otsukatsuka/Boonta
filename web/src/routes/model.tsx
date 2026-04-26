import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Bar } from "../components/Bar";
import { CalibrationChart } from "../components/CalibrationChart";
import { Panel } from "../components/Panel";
import { Sparkline } from "../components/Sparkline";
import { StatBlock } from "../components/StatBlock";
import {
  useCalibration,
  useFeatureImportance,
  useLeaderboard,
  useModelStatus,
  useTrainingRuns,
} from "../hooks/useApi";
import type { TrainingRunOut } from "../api/types";

function fmtNum(v: number | null | undefined, digits = 4): string {
  if (v == null) return "—";
  return v.toFixed(digits);
}

function fmtTime(secs: number | null | undefined): string {
  if (secs == null) return "—";
  if (secs < 60) return secs + "s";
  return (secs / 60).toFixed(1) + "m";
}

function StatusTag({ status }: { status: string }) {
  const cls = status === "DEPLOYED" ? "tag solid-amber" : "tag";
  return (
    <span className={cls} style={{ fontSize: 9 }}>
      {status}
    </span>
  );
}

function TrainingRunsTable({
  runs,
  selectedId,
  onSelect,
}: {
  runs: TrainingRunOut[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const trend = useMemo(
    () =>
      runs
        .slice()
        .reverse()
        .map((r) => (r.auc != null ? r.auc : r.logloss != null ? 1 - r.logloss : 0)),
    [runs],
  );

  if (runs.length === 0) {
    return (
      <div className="dim" style={{ padding: 16 }}>
        まだ training_run はありません — <code>python cli.py train --date-range YYYYMMDD YYYYMMDD</code> で記録される。
      </div>
    );
  }

  return (
    <table className="dt">
      <thead>
        <tr>
          <th className="l">RUN</th>
          <th className="l">DATE</th>
          <th className="l">PRESET</th>
          <th>LOGLOSS</th>
          <th>AUC</th>
          <th>BRIER</th>
          <th>HIT@3</th>
          <th>SAMPLES</th>
          <th>TIME</th>
          <th>TREND</th>
          <th>STATUS</th>
        </tr>
      </thead>
      <tbody>
        {runs.map((r) => {
          const isSel = r.run_id === selectedId;
          return (
            <tr
              key={r.id}
              onClick={() => onSelect(r.run_id)}
              style={{
                background: isSel ? "oklch(0.22 0.02 75 / 0.3)" : "transparent",
                cursor: "pointer",
              }}
            >
              <td className="l bold amb tnum">{r.run_id}</td>
              <td className="l dim tnum">{r.trained_at.slice(0, 10)}</td>
              <td className="l">{r.preset}</td>
              <td className="tnum bold">{fmtNum(r.logloss)}</td>
              <td className="tnum">{fmtNum(r.auc)}</td>
              <td className="tnum dim">{fmtNum(r.brier)}</td>
              <td className="tnum amb">
                {r.hit_at_3 != null ? (r.hit_at_3 * 100).toFixed(2) : "—"}
              </td>
              <td className="tnum dim">
                {r.num_samples != null ? r.num_samples.toLocaleString() : "—"}
              </td>
              <td className="tnum dim">{fmtTime(r.train_time_seconds)}</td>
              <td>
                {isSel && trend.length > 1 && (
                  <Sparkline data={trend} w={80} h={16} color="var(--amber)" />
                )}
              </td>
              <td>
                <StatusTag status={r.status} />
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function LeaderboardTable({ runId }: { runId: string | undefined }) {
  const { data, isLoading } = useLeaderboard(runId);
  if (isLoading) return <div className="dim">loading…</div>;
  const rows = data?.rows ?? [];
  if (rows.length === 0)
    return (
      <div className="dim" style={{ padding: 8 }}>
        leaderboard データなし — 次回 train 時に記録される
      </div>
    );

  let maxWeight = 0;
  for (const r of rows) if (r.weight && r.weight > maxWeight) maxWeight = r.weight;
  const weightMax = maxWeight > 0 ? maxWeight : 1;

  return (
    <table className="dt">
      <thead>
        <tr>
          <th className="l">MODEL</th>
          <th>SCORE</th>
          <th>FIT</th>
          <th>WEIGHT</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((m, i) => (
          <tr key={m.model + i}>
            <td className="l">
              <span className="dim tnum" style={{ marginRight: 6 }}>
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className={i === 0 ? "amb bold" : ""}>{m.model}</span>
            </td>
            <td className={"tnum " + (i === 0 ? "bold" : "dim")}>
              {fmtNum(m.score_val)}
            </td>
            <td className="tnum dim">
              {m.fit_time != null ? m.fit_time.toFixed(0) + "s" : "—"}
            </td>
            <td>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                {m.weight != null && (
                  <Bar value={m.weight} max={weightMax} color="amber" w={50} />
                )}
                <span
                  className={"tnum " + (m.weight && m.weight > 0 ? "bold" : "dim")}
                >
                  {m.weight != null ? m.weight.toFixed(3) : "—"}
                </span>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function CalibrationPanel({ runId }: { runId: string | undefined }) {
  const { data, isLoading } = useCalibration(runId);
  if (isLoading) return <div className="dim">loading…</div>;
  if (!data) return <div className="dim">no data</div>;

  if (data.bins.length === 0) {
    return (
      <div className="dim" style={{ padding: 8 }}>
        no held-out predictions for this run
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <CalibrationChart bins={data.bins} w={420} h={250} />
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "4px 12px",
          fontSize: 11,
          fontFamily: "var(--mono)",
          paddingTop: 6,
          borderTop: "1px dashed var(--bg-3)",
        }}
      >
        <span className="dim">ECE (expected calibration error)</span>
        <span className="amb tnum bold">{fmtNum(data.ece)}</span>
        <span className="dim">MCE (max calibration error)</span>
        <span className="tnum">{fmtNum(data.mce)}</span>
        <span className="dim">samples</span>
        <span className="tnum">{data.n_total.toLocaleString()}</span>
        <span className="dim">window</span>
        <span className="tnum dim">
          {data.window_from ?? "—"} → {data.window_to ?? "—"}
        </span>
      </div>
    </div>
  );
}

function FeatureImportancePanel() {
  const { data, isLoading, isError } = useFeatureImportance();
  if (isLoading) return <div className="dim">loading…</div>;
  if (isError || !data) {
    return (
      <div className="dim" style={{ padding: 8 }}>
        Modal feature_importance unavailable
      </div>
    );
  }
  const top = data.slice(0, 18);
  let max = 0;
  for (const f of top) if (f.importance > max) max = f.importance;
  if (max === 0) max = 1;

  return (
    <div>
      {top.map((f) => (
        <div
          key={f.name}
          style={{
            display: "grid",
            gridTemplateColumns: "110px 1fr 50px",
            gap: 8,
            alignItems: "center",
            padding: "3px 0",
            fontFamily: "var(--mono)",
            fontSize: 11,
          }}
        >
          <span className="bold" title={f.jp_label ?? f.name}>
            {f.name}
          </span>
          <Bar value={f.importance} max={max} color="amber" w={120} />
          <span
            className="tnum amb bold"
            style={{ textAlign: "right" }}
          >
            {(f.importance * 100).toFixed(2)}
          </span>
        </div>
      ))}
    </div>
  );
}

function ModelScreen() {
  const runsQ = useTrainingRuns(6);
  const statusQ = useModelStatus();
  const runs = runsQ.data ?? [];
  const deployed = runs.find((r) => r.status === "DEPLOYED") ?? runs[0];
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedRunId && deployed) {
      setSelectedRunId(deployed.run_id);
    }
  }, [deployed, selectedRunId]);

  const selected =
    runs.find((r) => r.run_id === selectedRunId) ?? deployed ?? null;

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid var(--line)",
          background: "var(--bg-1)",
        }}
      >
        <StatBlock
          k="DEPLOYED"
          v={deployed?.run_id ?? "—"}
          sub={deployed ? deployed.trained_at.slice(0, 10) : ""}
          cls="amb"
        />
        <StatBlock
          k="LOG LOSS"
          v={fmtNum(selected?.logloss ?? null)}
          sub="hold-out"
          cls="pos"
        />
        <StatBlock
          k="ROC AUC"
          v={fmtNum(selected?.auc ?? null)}
          sub="is_place"
          cls="pos"
        />
        <StatBlock
          k="BRIER"
          v={fmtNum(selected?.brier ?? null)}
          sub="lower=better"
        />
        <StatBlock
          k="HIT@3"
          v={
            selected?.hit_at_3 != null
              ? (selected.hit_at_3 * 100).toFixed(2) + "%"
              : "—"
          }
          sub="複勝命中率"
          cls="amb"
        />
        <StatBlock
          k="PRESET"
          v={selected?.preset ?? "—"}
          sub="AutoGluon"
        />
        <StatBlock
          k="MODAL"
          v={statusQ.data?.modal_ready ? "READY" : "—"}
          sub={statusQ.data?.modal_ready ? "online" : "offline"}
          cls={statusQ.data?.modal_ready ? "pos" : ""}
        />
      </div>

      <div
        className="term-grid"
        style={{
          gridTemplateColumns: "minmax(0,1.2fr) minmax(0,1fr) minmax(0,1fr)",
          gridTemplateRows: "auto minmax(0,1fr)",
        }}
      >
        <div className="panel" style={{ gridColumn: "1 / span 3" }}>
          <div className="panel-head">
            <span className="title">TRAINING RUNS</span>
            <span className="meta">
              直近 {runs.length} ラン · クリックで詳細 · DEPLOYED = 本番反映中
            </span>
          </div>
          <div className="panel-body">
            <TrainingRunsTable
              runs={runs}
              selectedId={selectedRunId}
              onSelect={setSelectedRunId}
            />
          </div>
        </div>

        <Panel
          title={`LEADERBOARD${selected ? ` · ${selected.run_id}` : ""}`}
          meta="AutoGluon ensemble"
        >
          <LeaderboardTable runId={selected?.run_id} />
        </Panel>

        <Panel title="CALIBRATION" meta="予測確率 vs 実測命中率 · 10 bins">
          <CalibrationPanel runId={selected?.run_id} />
        </Panel>

        <Panel title="FEATURE IMPORTANCE" meta="permutation · deployed model">
          <FeatureImportancePanel />
        </Panel>
      </div>
    </div>
  );
}

export const Route = createFileRoute("/model")({
  component: ModelScreen,
});
