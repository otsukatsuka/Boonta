import type { Horse } from "../api/types";

export function EVScatter({
  horses,
  evThreshold = 1.0,
  w = 520,
  h = 300,
}: {
  horses: Horse[];
  evThreshold?: number;
  w?: number;
  h?: number;
}) {
  const padX = 40;
  const padY = 24;
  const padR = 14;
  const padB = 32;
  const inW = w - padX - padR;
  const inH = h - padY - padB;

  const xMin = Math.log(1.5);
  const xMax = Math.log(140);
  const probs = horses.map((h) => h.prob ?? 0);
  const yMax = Math.max(0.6, ...probs) * 1.1;
  const xScale = (v: number) =>
    padX + ((Math.log(Math.max(1, v)) - xMin) / (xMax - xMin)) * inW;
  const yScale = (v: number) => padY + (1 - v / yMax) * inH;

  const isoEvs = [0.6, 0.8, 1.0, 1.2, 1.5];
  const oddsTicks = [2, 5, 10, 20, 50, 100];
  const probTicks = [0.1, 0.2, 0.3, 0.4, 0.5];

  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      {oddsTicks.map((o) => (
        <g key={o}>
          <line
            x1={xScale(o)}
            x2={xScale(o)}
            y1={padY}
            y2={h - padB}
            stroke="var(--bg-3)"
            strokeDasharray="2 3"
          />
          <text
            x={xScale(o)}
            y={h - padB + 12}
            fill="var(--fg-3)"
            fontSize="9"
            textAnchor="middle"
            fontFamily="var(--mono)"
          >
            {o}
          </text>
        </g>
      ))}
      {probTicks.map((p) => (
        <g key={p}>
          <line
            x1={padX}
            x2={w - padR}
            y1={yScale(p)}
            y2={yScale(p)}
            stroke="var(--bg-3)"
            strokeDasharray="2 3"
          />
          <text
            x={padX - 4}
            y={yScale(p) + 3}
            fill="var(--fg-3)"
            fontSize="9"
            textAnchor="end"
            fontFamily="var(--mono)"
          >
            {(p * 100).toFixed(0)}
          </text>
        </g>
      ))}
      <text
        x={padX}
        y={padY - 6}
        fontSize="9"
        fill="var(--fg-3)"
        fontFamily="var(--mono)"
      >
        P(複) %
      </text>
      <text
        x={w - padR}
        y={h - 4}
        fontSize="9"
        fill="var(--fg-3)"
        fontFamily="var(--mono)"
        textAnchor="end"
      >
        単勝オッズ (log)
      </text>
      {isoEvs.map((ev) => {
        const pts: string[] = [];
        for (let lx = 0; lx <= 60; lx++) {
          const lo = xMin + (lx / 60) * (xMax - xMin);
          const odds = Math.exp(lo);
          const p = (ev * 3) / odds;
          if (p < 0 || p > yMax) continue;
          pts.push(`${xScale(odds)},${yScale(p)}`);
        }
        const isThr = Math.abs(ev - evThreshold) < 0.01;
        return (
          <g key={ev}>
            <polyline
              points={pts.join(" ")}
              fill="none"
              stroke={isThr ? "var(--amber)" : "var(--line-bright)"}
              strokeWidth={isThr ? "1.4" : "0.8"}
              strokeDasharray={isThr ? "" : "3 3"}
            />
            <text
              x={xScale(135)}
              y={yScale((ev * 3) / 135)}
              fill={isThr ? "var(--amber)" : "var(--fg-3)"}
              fontSize="9"
              fontFamily="var(--mono)"
              textAnchor="end"
            >
              EV={ev.toFixed(1)}
            </text>
          </g>
        );
      })}
      {horses
        .filter((h) => h.prob != null && h.odds != null)
        .map((h) => {
          const cx = xScale(h.odds!);
          const cy = yScale(h.prob!);
          const ev = h.ev_tan ?? 0;
          const positiveEV = ev >= evThreshold;
          const color = positiveEV
            ? "var(--green)"
            : ev >= 0.8
              ? "var(--amber)"
              : "var(--fg-3)";
          const r = 4 + Math.min(10, Math.max(0, ev * 4));
          return (
            <g key={h.horse_number}>
              <circle
                cx={cx}
                cy={cy}
                r={r}
                fill={color}
                fillOpacity="0.16"
                stroke={color}
                strokeWidth="1"
              />
              <text
                x={cx}
                y={cy + 3}
                fill={color}
                fontSize="10"
                fontFamily="var(--mono)"
                fontWeight="700"
                textAnchor="middle"
              >
                {h.horse_number}
              </text>
            </g>
          );
        })}
    </svg>
  );
}
