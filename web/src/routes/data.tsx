import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Panel } from "../components/Panel";
import { StatBlock } from "../components/StatBlock";
import { CoverageHeatmap } from "../components/CoverageHeatmap";
import { FeatureMiniHist } from "../components/FeatureMiniHist";
import {
  useCoverage,
  useFeatureImportance,
  useFeatureStats,
  useFeatures,
  useFeeds,
} from "../hooks/useApi";
import type { FeatureMeta, FeatureStat, FeedRow } from "../api/types";

function fmtBytes(b: number | null): string {
  if (b == null) return "—";
  if (b < 1024) return b + " B";
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + " KB";
  return (b / 1024 / 1024).toFixed(2) + " MB";
}

function fmtLag(min: number | null): string {
  if (min == null) return "—";
  if (min < 60) return min + "m";
  if (min < 1440) return Math.floor(min / 60) + "h " + (min % 60) + "m";
  return Math.floor(min / 1440) + "d " + Math.floor((min % 1440) / 60) + "h";
}

function jstHHMM(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const tz = new Date(d.getTime() + 9 * 60 * 60 * 1000);
  return tz.toISOString().slice(11, 16) + " JST";
}

function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v == null) return "—";
  return v.toFixed(digits) + "%";
}

function fmtNum(v: number | null | undefined, digits = 2): string {
  if (v == null) return "—";
  return v.toFixed(digits);
}

function FeedsTable({ feeds }: { feeds: FeedRow[] }) {
  return (
    <table className="dt">
      <thead>
        <tr>
          <th className="l">FEED</th>
          <th className="l">名称</th>
          <th>ROWS</th>
          <th>SIZE</th>
          <th>LAST</th>
          <th>LAG</th>
          <th>ST</th>
        </tr>
      </thead>
      <tbody>
        {feeds.map((f) => {
          const isNa = f.status === "NA";
          const lagCls =
            f.lag_minutes == null
              ? "dim"
              : f.lag_minutes < 60
                ? "pos"
                : f.lag_minutes < 1440
                  ? "amb"
                  : "neg";
          const tagCls =
            f.status === "OK"
              ? "solid-green"
              : f.status === "WARN"
                ? "amber"
                : "";
          return (
            <tr key={f.id} style={isNa ? { opacity: 0.45 } : undefined}>
              <td className="l bold amb tnum">{f.id}</td>
              <td className="l">{f.name}</td>
              <td className="tnum">
                {f.rows != null ? f.rows.toLocaleString() : "—"}
              </td>
              <td className="tnum dim">{fmtBytes(f.bytes)}</td>
              <td className="tnum dim">{jstHHMM(f.last_iso)}</td>
              <td className={"tnum " + lagCls}>{fmtLag(f.lag_minutes)}</td>
              <td>
                <span className={"tag " + tagCls}>{f.status}</span>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function FeatureInspector({
  features,
  stats,
  importance,
}: {
  features: FeatureMeta[];
  stats: FeatureStat[];
  importance: Map<string, number>;
}) {
  const [sel, setSel] = useState<string>(features[0]?.name ?? "");
  const statsByName = useMemo(() => {
    const m = new Map<string, FeatureStat>();
    for (const s of stats) m.set(s.name, s);
    return m;
  }, [stats]);

  const selected = features.find((f) => f.name === sel) ?? features[0];
  const selectedStat =
    selected && (statsByName.get(selected.name) ?? {
      name: selected.name,
      type: selected.type,
      min: null,
      max: null,
      mean: null,
      std: null,
      missing_pct: null,
      cardinality: null,
    });

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(0,1.2fr) minmax(0,1fr)",
        gap: 14,
      }}
    >
      <div style={{ overflow: "auto", maxHeight: 420 }}>
        <table className="dt">
          <thead>
            <tr>
              <th className="l">NAME</th>
              <th className="l">TYPE</th>
              <th>MIN</th>
              <th>MEAN</th>
              <th>MAX</th>
              <th>NA%</th>
              <th>IMP</th>
              <th>HIST</th>
            </tr>
          </thead>
          <tbody>
            {features.map((f) => {
              const s = statsByName.get(f.name);
              const imp = importance.get(f.name);
              const isSel = sel === f.name;
              const stat: FeatureStat = s ?? {
                name: f.name,
                type: f.type,
                min: null,
                max: null,
                mean: null,
                std: null,
                missing_pct: null,
                cardinality: null,
              };
              return (
                <tr
                  key={f.name}
                  onClick={() => setSel(f.name)}
                  style={{
                    background: isSel ? "oklch(0.22 0.02 75 / 0.3)" : "transparent",
                    cursor: "pointer",
                  }}
                >
                  <td className="l bold">{f.name}</td>
                  <td className="l dim">
                    {f.type === "num"
                      ? "num"
                      : `cat${stat.cardinality != null ? ` (${stat.cardinality})` : ""}`}
                  </td>
                  <td className="tnum dim">
                    {f.type === "num" ? fmtNum(stat.min) : "—"}
                  </td>
                  <td className="tnum">
                    {f.type === "num" ? fmtNum(stat.mean) : "—"}
                  </td>
                  <td className="tnum dim">
                    {f.type === "num" ? fmtNum(stat.max) : "—"}
                  </td>
                  <td
                    className={
                      "tnum " +
                      (stat.missing_pct != null && stat.missing_pct > 1
                        ? "amb"
                        : "dim")
                    }
                  >
                    {fmtPct(stat.missing_pct, 1)}
                  </td>
                  <td className="tnum amb bold">
                    {imp != null ? (imp * 100).toFixed(1) : "—"}
                  </td>
                  <td>
                    <FeatureMiniHist stat={stat} w={100} h={20} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div style={{ padding: 14, background: "var(--bg-0)", border: "1px solid var(--bg-3)" }}>
        {selected && selectedStat && (
          <div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
                marginBottom: 6,
              }}
            >
              <span className="bold" style={{ fontSize: 14 }}>
                {selected.name}
              </span>
              <span className="dim" style={{ fontSize: 10 }}>
                {selected.jp_label ?? ""}
              </span>
            </div>
            <FeatureMiniHist stat={selectedStat} w={350} h={70} />
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "6px 12px",
                marginTop: 10,
                fontSize: 11,
                fontFamily: "var(--mono)",
              }}
            >
              <div className="dim">type</div>
              <div>
                {selected.type === "num"
                  ? "numeric"
                  : `categorical${selectedStat.cardinality != null ? ` · cardinality ${selectedStat.cardinality}` : ""}`}
              </div>
              {selected.type === "num" && (
                <>
                  <div className="dim">min / max</div>
                  <div className="tnum">
                    {fmtNum(selectedStat.min)} / {fmtNum(selectedStat.max)}
                  </div>
                  <div className="dim">mean ± std</div>
                  <div className="tnum">
                    {fmtNum(selectedStat.mean)} ± {fmtNum(selectedStat.std)}
                  </div>
                </>
              )}
              <div className="dim">missing</div>
              <div
                className={
                  selectedStat.missing_pct != null && selectedStat.missing_pct > 1
                    ? "amb tnum"
                    : "tnum"
                }
              >
                {fmtPct(selectedStat.missing_pct, 2)}
              </div>
              <div className="dim">importance</div>
              <div className="amb bold tnum">
                {(() => {
                  const imp = importance.get(selected.name);
                  return imp != null ? (imp * 100).toFixed(2) + "%" : "—";
                })()}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function DataScreen() {
  const feedsQ = useFeeds();
  const coverageQ = useCoverage();
  const featuresQ = useFeatures();
  const statsQ = useFeatureStats();
  const importanceQ = useFeatureImportance();

  const feeds = feedsQ.data?.feeds ?? [];
  const totals = feedsQ.data;
  const coverage = coverageQ.data;
  const features = featuresQ.data ?? [];
  const stats = statsQ.data ?? [];
  const importanceMap = useMemo(() => {
    const m = new Map<string, number>();
    for (const i of importanceQ.data ?? []) m.set(i.name, i.importance);
    return m;
  }, [importanceQ.data]);

  const totalRaces = useMemo(() => {
    if (!coverage) return 0;
    let n = 0;
    for (const row of coverage.counts) for (const v of row) n += v;
    return n;
  }, [coverage]);

  const datasetSpan =
    coverage && coverage.years.length
      ? `${coverage.years[0]} → ${coverage.years[coverage.years.length - 1]}`
      : "—";

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
          k="FEEDS"
          v={totals ? `${totals.ok_count}/${totals.total_count}` : "—"}
          sub="JRDB sources"
          cls="pos"
        />
        <StatBlock
          k="LATEST"
          v={jstHHMM(totals?.latest_iso ?? null)}
          sub="last sync"
        />
        <StatBlock
          k="ROWS · TODAY"
          v={totals ? totals.total_rows.toLocaleString() : "—"}
          sub="all feeds"
        />
        <StatBlock
          k="SIZE · TODAY"
          v={totals ? fmtBytes(totals.total_bytes) : "—"}
          sub="raw uncompressed"
        />
        <StatBlock
          k="FEATURES"
          v={features.length || "—"}
          sub="ML feature columns"
          cls="amb"
        />
        <StatBlock k="DATASET" v={datasetSpan} sub="years span" />
        <StatBlock
          k="RACES"
          v={totalRaces.toLocaleString()}
          sub="parsed total"
        />
      </div>

      <div
        className="term-grid"
        style={{
          gridTemplateColumns: "minmax(0,1.1fr) minmax(0,1fr)",
          gridTemplateRows: "auto minmax(0,1fr)",
        }}
      >
        <Panel title="JRDB FEEDS" meta="日次同期 · 8 sources">
          <FeedsTable feeds={feeds} />
        </Panel>

        <Panel title="DATASET COVERAGE" meta="月次レース取得数 (年×月)">
          {coverage ? (
            <CoverageHeatmap years={coverage.years} counts={coverage.counts} />
          ) : (
            <div className="dim">loading…</div>
          )}
        </Panel>

        <div className="panel" style={{ gridColumn: "1 / span 2" }}>
          <div className="panel-head">
            <span className="title">KYI FEATURE INSPECTOR</span>
            <span className="meta">
              {features.length} features · click row to inspect
            </span>
          </div>
          <div className="panel-body">
            {features.length > 0 ? (
              <FeatureInspector
                features={features}
                stats={stats}
                importance={importanceMap}
              />
            ) : (
              <div className="dim">loading…</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export const Route = createFileRoute("/data")({
  component: DataScreen,
});
