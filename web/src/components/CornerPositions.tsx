import type { Horse } from "../api/types";

export function CornerPositions({
  horses,
  w = 560,
  h = 260,
}: {
  horses: Horse[];
  w?: number;
  h?: number;
}) {
  const stages = [
    { key: "start", label: "スタート", get: (h: Horse) => h.horse_number },
    { key: "mid", label: "道中", get: (h: Horse) => h.mid_position ?? 99 },
    { key: "late", label: "後3F", get: (h: Horse) => h.late3f_position ?? 99 },
    { key: "goal", label: "ゴール", get: (h: Horse) => h.goal_position ?? 99 },
  ];
  const padX = 50;
  const padR = 20;
  const padY = 22;
  const padB = 18;
  const inW = w - padX - padR;
  const inH = h - padY - padB;
  const N = horses.length;
  if (N < 2) return null;

  const xs = stages.map((_, i) => padX + (i / (stages.length - 1)) * inW);
  const yScale = (pos: number) => padY + ((pos - 1) / (N - 1)) * inH;

  const ranked = stages.map((s) => {
    const arr = [...horses].sort((a, b) => s.get(a) - s.get(b));
    const map: Record<number, number> = {};
    arr.forEach((h, i) => {
      map[h.horse_number] = i + 1;
    });
    return map;
  });

  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      {stages.map((s, i) => (
        <g key={s.key}>
          <line
            x1={xs[i]}
            x2={xs[i]}
            y1={padY - 6}
            y2={h - padB + 4}
            stroke="var(--line)"
            strokeDasharray="2 3"
          />
          <text
            x={xs[i]}
            y={padY - 8}
            fill="var(--fg-2)"
            fontSize="10"
            textAnchor="middle"
            fontFamily="var(--mono)"
          >
            {s.label}
          </text>
        </g>
      ))}
      {[1, Math.ceil(N / 2), N].map((p) => (
        <text
          key={p}
          x={padX - 8}
          y={yScale(p) + 3}
          fill="var(--fg-3)"
          fontSize="9"
          textAnchor="end"
          fontFamily="var(--mono)"
        >
          {p}位
        </text>
      ))}
      {horses.map((h) => {
        const path = stages
          .map((_, i) => `${xs[i]},${yScale(ranked[i][h.horse_number])}`)
          .join(" L");
        const prob = h.prob ?? 0;
        const color =
          prob >= 0.4 ? "var(--amber)" : prob >= 0.25 ? "var(--cyan)" : "var(--fg-3)";
        const opacity = prob >= 0.4 ? 1 : prob >= 0.25 ? 0.7 : 0.3;
        return (
          <g key={h.horse_number} opacity={opacity}>
            <path
              d={"M" + path}
              fill="none"
              stroke={color}
              strokeWidth={prob >= 0.4 ? 1.6 : 1}
            />
            {stages.map((_, i) => (
              <circle
                key={i}
                cx={xs[i]}
                cy={yScale(ranked[i][h.horse_number])}
                r="3"
                fill={color}
              />
            ))}
            <text
              x={xs[xs.length - 1] + 6}
              y={yScale(ranked[ranked.length - 1][h.horse_number]) + 3}
              fill={color}
              fontSize="10"
              fontFamily="var(--mono)"
              fontWeight="700"
            >
              {h.horse_number}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
