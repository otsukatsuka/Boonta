export function CoverageHeatmap({
  years,
  counts,
  cell = 28,
  gap = 2,
}: {
  years: number[];
  counts: number[][];
  cell?: number;
  gap?: number;
}) {
  const monthsW = 12 * cell + 11 * gap;
  let max = 0;
  for (const row of counts) for (const v of row) if (v > max) max = v;
  if (max === 0) max = 1;

  return (
    <div style={{ fontFamily: "var(--mono)" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `44px ${monthsW}px`,
          columnGap: 8,
          alignItems: "end",
          marginBottom: 4,
        }}
      >
        <div />
        <div
          style={{
            display: "grid",
            gridTemplateColumns: `repeat(12, ${cell}px)`,
            columnGap: gap,
          }}
        >
          {Array.from({ length: 12 }, (_, i) => (
            <div
              key={i}
              style={{ fontSize: 9, color: "var(--fg-3)", textAlign: "center" }}
            >
              {i + 1}
            </div>
          ))}
        </div>
      </div>
      {years.map((y, yi) => (
        <div
          key={y}
          style={{
            display: "grid",
            gridTemplateColumns: `44px ${monthsW}px`,
            columnGap: 8,
            alignItems: "center",
            marginBottom: gap,
          }}
        >
          <div style={{ fontSize: 11, color: "var(--fg-2)", textAlign: "right" }}>
            {y}
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: `repeat(12, ${cell}px)`,
              columnGap: gap,
            }}
          >
            {(counts[yi] ?? Array(12).fill(0)).map((c, m) => {
              const ratio = c / max;
              const bg =
                c === 0
                  ? "var(--bg-2)"
                  : ratio < 0.4
                    ? "oklch(0.55 0.15 30)"
                    : ratio < 0.75
                      ? "oklch(0.7 0.16 75)"
                      : "oklch(0.78 0.18 145)";
              const opacity = c === 0 ? 1 : 0.45 + ratio * 0.55;
              const textColor =
                ratio >= 0.4 ? "oklch(0.15 0 0)" : "var(--fg-3)";
              return (
                <div
                  key={m}
                  title={`${y}-${String(m + 1).padStart(2, "0")}: ${c} races`}
                  style={{
                    height: cell,
                    background: bg,
                    opacity,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 9,
                    color: textColor,
                  }}
                >
                  {c === 0 ? "" : c}
                </div>
              );
            })}
          </div>
        </div>
      ))}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginTop: 10,
          fontSize: 10,
          color: "var(--fg-3)",
        }}
      >
        <span>0</span>
        <div style={{ width: 8, height: 10, background: "var(--bg-2)" }} />
        <div
          style={{
            width: 8,
            height: 10,
            background: "oklch(0.55 0.15 30)",
            opacity: 0.85,
          }}
        />
        <div
          style={{
            width: 8,
            height: 10,
            background: "oklch(0.7 0.16 75)",
            opacity: 0.9,
          }}
        />
        <div
          style={{ width: 8, height: 10, background: "oklch(0.78 0.18 145)" }}
        />
        <span>{max}</span>
        <span style={{ marginLeft: "auto" }}>cell = レース数 / 月</span>
      </div>
    </div>
  );
}
