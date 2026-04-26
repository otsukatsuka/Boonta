import type { CalibrationBin } from "../api/types";

export function CalibrationChart({
  bins,
  w = 420,
  h = 260,
}: {
  bins: CalibrationBin[];
  w?: number;
  h?: number;
}) {
  const pad = { l: 36, r: 8, t: 8, b: 28 };
  const iw = w - pad.l - pad.r;
  const ih = h - pad.t - pad.b;
  const xToPx = (x: number) => pad.l + x * iw;
  const yToPx = (y: number) => pad.t + (1 - y) * ih;

  const sorted = [...bins].sort((a, b) => a.pred_mid - b.pred_mid);
  const path =
    sorted.length > 0
      ? "M " +
        sorted
          .map((b) => `${xToPx(b.pred_mid)},${yToPx(b.actual_rate)}`)
          .join(" L ")
      : "";

  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      {[0, 0.2, 0.4, 0.6, 0.8, 1].map((g, i) => (
        <g key={i}>
          <line
            x1={xToPx(g)}
            y1={pad.t}
            x2={xToPx(g)}
            y2={pad.t + ih}
            stroke="var(--bg-2)"
          />
          <line
            x1={pad.l}
            y1={yToPx(g)}
            x2={pad.l + iw}
            y2={yToPx(g)}
            stroke="var(--bg-2)"
          />
          <text
            x={xToPx(g)}
            y={h - 10}
            fontSize="9"
            fill="var(--fg-3)"
            textAnchor="middle"
            fontFamily="var(--mono)"
          >
            {g.toFixed(1)}
          </text>
          <text
            x={pad.l - 6}
            y={yToPx(g) + 3}
            fontSize="9"
            fill="var(--fg-3)"
            textAnchor="end"
            fontFamily="var(--mono)"
          >
            {g.toFixed(1)}
          </text>
        </g>
      ))}
      <line
        x1={xToPx(0)}
        y1={yToPx(0)}
        x2={xToPx(1)}
        y2={yToPx(1)}
        stroke="var(--fg-3)"
        strokeDasharray="4 4"
        strokeWidth={1}
      />
      {path && (
        <path
          d={path}
          fill="none"
          stroke="var(--amber)"
          strokeWidth={1.8}
        />
      )}
      {sorted.map((b, i) => (
        <circle
          key={i}
          cx={xToPx(b.pred_mid)}
          cy={yToPx(b.actual_rate)}
          r={3.5}
          fill="var(--amber)"
        >
          <title>
            pred {b.pred_mid.toFixed(2)} → actual {b.actual_rate.toFixed(2)} (n={b.n})
          </title>
        </circle>
      ))}
      <text
        x={pad.l + iw / 2}
        y={h - 1}
        fontSize="10"
        fill="var(--fg-2)"
        textAnchor="middle"
        fontFamily="var(--mono)"
      >
        predicted P(複)
      </text>
      <text
        x={10}
        y={pad.t + ih / 2}
        fontSize="10"
        fill="var(--fg-2)"
        textAnchor="middle"
        fontFamily="var(--mono)"
        transform={`rotate(-90 10 ${pad.t + ih / 2})`}
      >
        actual rate
      </text>
    </svg>
  );
}
