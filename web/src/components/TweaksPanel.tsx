/**
 * Floating Tweaks panel — only ev_threshold for now.
 * Persists to localStorage; UI computes EV/bets locally so the slider is instant.
 */
import { useEffect, useState } from "react";

const KEY = "boonta.evThreshold";

export function useEvThreshold() {
  const [value, setValue] = useState<number>(() => {
    const v = localStorage.getItem(KEY);
    return v ? parseFloat(v) : 1.0;
  });
  useEffect(() => {
    localStorage.setItem(KEY, String(value));
  }, [value]);
  return [value, setValue] as const;
}

export function TweaksPanel({
  evThreshold,
  setEvThreshold,
}: {
  evThreshold: number;
  setEvThreshold: (v: number) => void;
}) {
  return (
    <div
      style={{
        position: "fixed",
        right: 16,
        bottom: 36,
        background: "var(--bg-1)",
        border: "1px solid var(--line)",
        padding: 12,
        minWidth: 240,
        fontFamily: "var(--mono)",
        fontSize: 11,
        zIndex: 100,
      }}
    >
      <div
        style={{
          fontSize: 10,
          color: "var(--fg-3)",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          marginBottom: 8,
        }}
      >
        TWEAKS
      </div>
      <div style={{ marginBottom: 6, color: "var(--fg-2)" }}>
        ev_threshold:{" "}
        <span className="amb bold">{evThreshold.toFixed(2)}</span>
      </div>
      <input
        type="range"
        min="0.8"
        max="1.5"
        step="0.05"
        value={evThreshold}
        onChange={(e) => setEvThreshold(parseFloat(e.target.value))}
        style={{ width: "100%" }}
      />
      <div className="dim" style={{ fontSize: 10, marginTop: 6 }}>
        1.00 = ブレイクイーブン. ↑で厳しめにピック.
      </div>
    </div>
  );
}
