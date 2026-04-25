import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMemo } from "react";
import { Panel } from "../components/Panel";
import { Umaban } from "../components/Umaban";
import { Bar } from "../components/Bar";
import { PacePill } from "../components/PacePill";
import { EVScatter } from "../components/EVScatter";
import { CornerPositions } from "../components/CornerPositions";
import { useEvThreshold } from "../components/TweaksPanel";
import { usePredictRace, useRaceDetail } from "../hooks/useApi";
import { withRecomputedEV, buildBetPlan } from "../lib/betting";
import { IO_LABEL, STYLE_LABEL } from "../lib/format";
import type { Horse } from "../api/types";

function BetsCard({
  plan,
  evThreshold,
}: {
  plan: ReturnType<typeof buildBetPlan>;
  evThreshold: number;
}) {
  const Row = ({
    label,
    code,
    count,
    children,
  }: {
    label: string;
    code: string;
    count: number;
    children: React.ReactNode;
  }) => (
    <div style={{ padding: "8px 0", borderBottom: "1px dashed var(--bg-3)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <span>
          <span className="amb bold">{label}</span>{" "}
          <span className="dim" style={{ fontSize: 10 }}>
            {code}
          </span>
        </span>
        <span className="dim tnum" style={{ fontSize: 10 }}>
          {count}点
        </span>
      </div>
      <div style={{ marginTop: 4, fontFamily: "var(--mono)" }}>{children}</div>
    </div>
  );
  const nums = (arr: number[]) =>
    arr.length ? (
      arr.map((n) => (
        <span
          key={n}
          className="bold tnum"
          style={{
            display: "inline-block",
            padding: "1px 6px",
            border: "1px solid var(--line)",
            marginRight: 4,
            marginBottom: 4,
          }}
        >
          {n}
        </span>
      ))
    ) : (
      <span className="dim">該当なし</span>
    );
  const combos = (arr: number[][]) =>
    arr.length ? (
      arr.map((c, i) => (
        <span
          key={i}
          className="tnum"
          style={{
            display: "inline-block",
            padding: "1px 6px",
            border: "1px solid var(--line)",
            marginRight: 4,
            marginBottom: 4,
          }}
        >
          {c.join("-")}
        </span>
      ))
    ) : (
      <span className="dim">該当なし</span>
    );
  return (
    <div>
      <div className="dim" style={{ fontSize: 10, marginBottom: 4 }}>
        ev_threshold={evThreshold.toFixed(2)}
      </div>
      <Row label="単勝" code="TANSHO" count={plan.tansho.length}>
        {nums(plan.tansho)}
      </Row>
      <Row label="複勝" code="FUKUSHO" count={plan.fukusho.length}>
        {nums(plan.fukusho)}
      </Row>
      <Row label="馬連 BOX" code="UMAREN · top3" count={plan.umaren_box.length}>
        {combos(plan.umaren_box)}
      </Row>
      <Row
        label="3連複 BOX"
        code="SANRENPUKU · top4"
        count={plan.sanrenpuku_box.length}
      >
        {combos(plan.sanrenpuku_box)}
      </Row>
      <Row
        label={`3連複 軸1頭流し (軸 ${plan.nagashi.axis ?? "-"})`}
        code="NAGASHI"
        count={plan.nagashi.combos.length}
      >
        {combos(plan.nagashi.combos)}
      </Row>
    </div>
  );
}

function RaceDetailScreen() {
  const { raceKey } = Route.useParams();
  const navigate = useNavigate();
  const [evThreshold] = useEvThreshold();
  const { data, isLoading, error } = useRaceDetail(raceKey);
  const predict = usePredictRace(raceKey);

  const horses: Horse[] = useMemo(
    () => withRecomputedEV(data?.horses ?? []),
    [data],
  );
  const sortedByEv = useMemo(
    () => [...horses].sort((a, b) => (b.ev_tan ?? -1) - (a.ev_tan ?? -1)),
    [horses],
  );
  const plan = useMemo(
    () => buildBetPlan(horses, evThreshold),
    [horses, evThreshold],
  );

  if (isLoading || !data) {
    return (
      <div style={{ padding: 24 }} className="dim">
        loading {raceKey}…
      </div>
    );
  }
  if (error) {
    return (
      <div style={{ padding: 24 }} className="dim">
        error: {String(error)}
      </div>
    );
  }
  const race = data.race;

  return (
    <div style={{ display: "grid", gridTemplateRows: "auto minmax(0,1fr)", flex: 1, minHeight: 0 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          padding: "10px 14px",
          background: "var(--bg-1)",
          borderBottom: "1px solid var(--line)",
        }}
      >
        <button className="term-btn" onClick={() => navigate({ to: "/" })}>
          ‹ DASH
        </button>
        <span className="dim">race_key</span>
        <span style={{ color: "var(--amber)" }} className="bold">
          {race.race_key}
        </span>
        <span className="dim">|</span>
        <span
          style={{
            fontFamily: "var(--display)",
            fontSize: 20,
            fontWeight: 700,
            letterSpacing: "0.02em",
          }}
        >
          {race.venue} {race.race_no}R
          {race.name ? ` · ${race.name}` : ""}
        </span>
        {race.grade && (
          <span className={"tag " + (race.grade === "G1" ? "solid-amber" : "amber")}>
            {race.grade}
          </span>
        )}
        <span className="dim">
          {race.surface}
          {race.distance ? `${race.distance}m` : ""}
          {race.condition ? ` · ${race.condition}馬場` : ""}
          {race.weather ? ` · ${race.weather}` : ""}
        </span>
        <span style={{ marginLeft: "auto", display: "flex", gap: 14, alignItems: "center" }}>
          {race.pace && <PacePill pace={race.pace} />}
          <span className="dim">発走</span>
          <span className="bold">{race.post_time ?? "—"}</span>
          <span className="dim">|</span>
          <span className="dim">頭数</span>
          <span className="bold">{race.head_count ?? "—"}</span>
          <button
            className="term-btn primary"
            disabled={predict.isPending}
            onClick={() => predict.mutate()}
          >
            {predict.isPending ? "PREDICTING…" : "PREDICT"}
          </button>
        </span>
      </div>

      <div
        className="term-grid"
        style={{
          gridTemplateColumns: "minmax(0, 1.4fr) minmax(0, 1fr)",
          gridTemplateRows: "auto auto auto",
        }}
      >
        <div style={{ gridRow: "1 / span 3" }}>
          <Panel
            title="出馬 + ML予測 + EV"
            meta={`${horses.length} horses · sorted by EV単`}
            flush
          >
            <table className="dt">
              <thead>
                <tr>
                  <th>馬</th>
                  <th>枠</th>
                  <th className="l">馬名 / 騎手</th>
                  <th>脚</th>
                  <th>IDM</th>
                  <th>道</th>
                  <th>後</th>
                  <th>ゴ</th>
                  <th>内外</th>
                  <th>単</th>
                  <th>複</th>
                  <th>P(複)</th>
                  <th>EV単</th>
                  <th>EV複</th>
                </tr>
              </thead>
              <tbody>
                {sortedByEv.map((h) => (
                  <tr key={h.horse_number}>
                    <td className="bold tnum">{h.horse_number}</td>
                    <td>
                      <Umaban n={h.horse_number} waku={h.waku ?? 0} sm />
                    </td>
                    <td className="l">
                      <div className="bold">{h.name}</div>
                      <div className="dim" style={{ fontSize: 10 }}>
                        {h.jockey ?? "—"}
                        {h.jockey_index != null ? ` (${h.jockey_index.toFixed(0)})` : ""}
                      </div>
                    </td>
                    <td>{h.running_style ? STYLE_LABEL[h.running_style] : "—"}</td>
                    <td className="tnum">{h.idm?.toFixed(1) ?? "—"}</td>
                    <td className="tnum dim">{h.mid_position ?? "—"}</td>
                    <td className="tnum dim">{h.late3f_position ?? "—"}</td>
                    <td
                      className={"tnum " + (h.goal_position && h.goal_position <= 3 ? "amb bold" : "")}
                    >
                      {h.goal_position ?? "—"}
                    </td>
                    <td className="dim">{h.goal_io ? IO_LABEL[h.goal_io] : "—"}</td>
                    <td className="tnum">{h.odds?.toFixed(1) ?? "—"}</td>
                    <td className="tnum dim">{h.fukusho_odds?.toFixed(1) ?? "—"}</td>
                    <td className="tnum">
                      {h.prob != null ? (
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 6,
                            justifyContent: "flex-end",
                          }}
                        >
                          <Bar value={h.prob} max={0.6} color="amber" w={36} />
                          <span className={h.prob >= 0.4 ? "amb bold" : ""}>
                            {(h.prob * 100).toFixed(1)}
                          </span>
                        </div>
                      ) : (
                        <span className="dim">—</span>
                      )}
                    </td>
                    <td
                      className={
                        "tnum bold " +
                        (h.ev_tan == null
                          ? "dim"
                          : h.ev_tan >= evThreshold
                            ? "pos"
                            : h.ev_tan >= 0.8
                              ? "amb"
                              : "dim")
                      }
                    >
                      {h.ev_tan != null ? h.ev_tan.toFixed(2) : "—"}
                      {h.ev_tan != null && h.ev_tan >= evThreshold ? " ★" : ""}
                    </td>
                    <td
                      className={
                        "tnum " +
                        (h.ev_fuku == null
                          ? "dim"
                          : h.ev_fuku >= evThreshold
                            ? "pos"
                            : "dim")
                      }
                    >
                      {h.ev_fuku != null ? h.ev_fuku.toFixed(2) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        </div>

        <Panel title="位置取り予想 / コーナー" meta="start → mid → late3F → goal">
          <CornerPositions horses={horses} w={520} h={220} />
        </Panel>

        <Panel
          title="EV 散布図"
          meta={`iso EV 線 · 閾値=${evThreshold.toFixed(2)}`}
        >
          <EVScatter horses={horses} evThreshold={evThreshold} w={520} h={240} />
        </Panel>

        <Panel
          title="買い目 (EV ベース)"
          meta={`ev_threshold=${evThreshold.toFixed(2)}`}
        >
          <BetsCard plan={plan} evThreshold={evThreshold} />
        </Panel>
      </div>
    </div>
  );
}

export const Route = createFileRoute("/race/$raceKey")({
  component: RaceDetailScreen,
});
