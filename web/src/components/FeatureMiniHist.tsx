import type { FeatureStat } from "../api/types";

export function FeatureMiniHist({
  stat,
  w = 120,
  h = 24,
}: {
  stat: FeatureStat;
  w?: number;
  h?: number;
}) {
  if (stat.type !== "num") {
    const card = stat.cardinality ?? 4;
    const bars = Array.from(
      { length: Math.max(2, Math.min(card, 8)) },
      (_, i) => 0.3 + Math.sin(i * 1.7) * 0.3 + 0.2,
    );
    return (
      <svg width={w} height={h}>
        {bars.map((v, i) => {
          const bw = w / bars.length - 2;
          const vv = Math.max(0.05, Math.min(1, v));
          return (
            <rect
              key={i}
              x={i * (bw + 2)}
              y={h - vv * h}
              width={bw}
              height={vv * h}
              fill="var(--cyan)"
              opacity={0.7}
            />
          );
        })}
      </svg>
    );
  }
  const seed = (stat.name.charCodeAt(0) || 1) * 0.13 + (stat.std ?? 1);
  const bars = Array.from({ length: 18 }, (_, i) => {
    const x = (i - 8.5) / 4.5;
    return Math.max(0.04, Math.exp(-x * x) * 0.95 + Math.sin(i * seed) * 0.08);
  });
  return (
    <svg width={w} height={h}>
      {bars.map((v, i) => {
        const bw = w / bars.length;
        return (
          <rect
            key={i}
            x={i * bw}
            y={h - v * h}
            width={bw - 0.5}
            height={v * h}
            fill="var(--amber)"
            opacity={0.8}
          />
        );
      })}
    </svg>
  );
}
