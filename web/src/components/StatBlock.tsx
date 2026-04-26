import type { ReactNode } from "react";

export function StatBlock({
  k,
  v,
  sub,
  cls = "",
}: {
  k: string;
  v: ReactNode;
  sub?: ReactNode;
  cls?: string;
}) {
  return (
    <div
      style={{
        padding: "10px 14px",
        borderRight: "1px solid var(--line)",
        flex: 1,
        minWidth: 0,
      }}
    >
      <div
        style={{
          fontSize: 9,
          color: "var(--fg-3)",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
        }}
      >
        {k}
      </div>
      <div
        className={"tnum bold " + cls}
        style={{
          fontFamily: "var(--mono)",
          fontSize: 22,
          lineHeight: "1.1",
          marginTop: 2,
        }}
      >
        {v}
      </div>
      {sub && (
        <div style={{ fontSize: 9, color: "var(--fg-3)", marginTop: 2 }}>{sub}</div>
      )}
    </div>
  );
}
