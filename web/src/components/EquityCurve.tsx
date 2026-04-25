import type { EquityPoint } from "../api/types";

export function EquityCurve({
  points,
  w = 700,
  h = 320,
}: {
  points: EquityPoint[];
  w?: number;
  h?: number;
}) {
  if (points.length === 0) {
    return (
      <div className="dim" style={{ padding: 24 }}>
        no data
      </div>
    );
  }
  const padX = 50;
  const padR = 20;
  const padY = 16;
  const padB = 28;
  const inW = w - padX - padR;
  const inH = h - padY - padB;
  const ys = points.map((p) => p.cum);
  const minE = Math.min(0, ...ys);
  const maxE = Math.max(0, ...ys);
  const range = maxE - minE || 1;
  const xScale = (i: number) =>
    padX + (i / Math.max(1, points.length - 1)) * inW;
  const yScale = (v: number) => padY + (1 - (v - minE) / range) * inH;
  const path = points.map((p, i) => `${xScale(i)},${yScale(p.cum)}`).join(" L");
  const zeroY = yScale(0);
  const last = points[points.length - 1].cum;
  const stroke = last >= 0 ? "var(--green)" : "var(--red)";

  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      {[0, 0.25, 0.5, 0.75, 1].map((t) => {
        const v = minE + t * range;
        return (
          <g key={t}>
            <line
              x1={padX}
              x2={w - padR}
              y1={padY + (1 - t) * inH}
              y2={padY + (1 - t) * inH}
              stroke="var(--bg-3)"
              strokeDasharray="2 3"
            />
            <text
              x={padX - 6}
              y={padY + (1 - t) * inH + 3}
              fill="var(--fg-3)"
              fontSize="9"
              textAnchor="end"
              fontFamily="var(--mono)"
            >
              {Math.round(v / 1000)}k
            </text>
          </g>
        );
      })}
      <line
        x1={padX}
        x2={w - padR}
        y1={zeroY}
        y2={zeroY}
        stroke="var(--fg-3)"
        strokeWidth="1"
      />
      {points.map((p, i) => (
        <text
          key={p.month}
          x={xScale(i)}
          y={h - 8}
          fill="var(--fg-3)"
          fontSize="9"
          textAnchor="middle"
          fontFamily="var(--mono)"
        >
          {p.month.slice(5)}
        </text>
      ))}
      <path d={"M" + path} fill="none" stroke={stroke} strokeWidth="1.6" />
      {points.map((p, i) => (
        <circle
          key={p.month}
          cx={xScale(i)}
          cy={yScale(p.cum)}
          r="2"
          fill={stroke}
        />
      ))}
    </svg>
  );
}
