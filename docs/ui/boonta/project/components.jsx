// Shared utilities + small components for RACE TERMINAL screens.
// Exposes globals via window.* so other Babel <script> blocks can use them.

const { useState, useMemo, useEffect, useRef } = React;

// --- formatters ---
const fmtJPY = (n) => "¥" + (n).toLocaleString("ja-JP");
const fmtPct = (n, d=1) => (n*100).toFixed(d) + "%";
const fmtNum = (n, d=2) => Number(n).toFixed(d);
const padN = (n, w=2) => String(n).padStart(w, " ");

// Pace label
const PACE_LABEL = { H: "ハイ", M: "ミドル", S: "スロー" };
const STYLE_LABEL = { 1: "逃", 2: "先", 3: "差", 4: "追" };
const STYLE_LONG  = { 1: "逃げ", 2: "先行", 3: "差し", 4: "追込" };
const IO_LABEL = { 1: "最内", 2: "内", 3: "中", 4: "外", 5: "大外" };

// race_key = 場(2) + 年(2) + 回(1) + 日(1,hex) + R(2)
function parseRaceKey(k) {
  return {
    venue_code: k.slice(0,2),
    year: k.slice(2,4),
    kai: k.slice(4,5),
    nichi: k.slice(5,6),
    race_no: parseInt(k.slice(6,8), 10),
  };
}

// --- generic UI ---
function Panel({ title, meta, children, flush=false, action }) {
  return (
    <div className="panel">
      <div className="panel-head">
        <span className="title">{title}</span>
        <span style={{display:"flex", gap:8, alignItems:"center"}}>
          {meta && <span className="meta">{meta}</span>}
          {action}
        </span>
      </div>
      <div className={"panel-body" + (flush ? " flush" : "")}>{children}</div>
    </div>
  );
}

function Bar({ value, max=1, color="amber", w=80 }) {
  const pct = Math.min(100, Math.max(0, (value/max)*100));
  return (
    <div className="bar-bg" style={{ width: w }}>
      <div className={"bar-fill " + color} style={{ width: pct + "%" }} />
    </div>
  );
}

function Sparkline({ data, w=120, h=22, color="var(--amber)" }) {
  if (!data || !data.length) return null;
  const min = Math.min(...data), max = Math.max(...data);
  const range = max - min || 1;
  const step = w / (data.length - 1 || 1);
  const pts = data.map((v, i) => `${i*step},${h - ((v-min)/range)*h}`).join(" ");
  return (
    <svg width={w} height={h} style={{display:"block"}}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.2" />
    </svg>
  );
}

function Umaban({ n, waku, sm=false }) {
  return (
    <span className={`umaban waku-${waku} ${sm ? "umaban-sm" : ""}`}>{n}</span>
  );
}

function PacePill({ pace }) {
  return <span className={"pace-pill " + pace}>{pace} {PACE_LABEL[pace]}</span>;
}

// EV scatter: x = odds (log), y = prob (%), size = ev_tan
function EVScatter({ horses, evThreshold=1.0, w=520, h=300, axis="ev_tan" }) {
  const padX = 40, padY = 24, padR = 14, padB = 32;
  const inW = w - padX - padR, inH = h - padY - padB;
  // Log odds 1..100
  const xMin = Math.log(1.5), xMax = Math.log(140);
  const yMax = Math.max(0.6, ...horses.map(h => h.prob)) * 1.1;
  const xScale = v => padX + ((Math.log(Math.max(1, v)) - xMin) / (xMax - xMin)) * inW;
  const yScale = v => padY + (1 - v / yMax) * inH;

  // EV iso curves: prob = (ev*3) / odds  (for ev_tan)
  // Or:           prob = ev / fuku       (we'll just use ev_tan iso)
  const isoEvs = [0.6, 0.8, 1.0, 1.2, 1.5];
  const oddsTicks = [2, 5, 10, 20, 50, 100];
  const probTicks = [0.1, 0.2, 0.3, 0.4, 0.5];

  return (
    <svg width={w} height={h} style={{display:"block"}}>
      {/* grid */}
      {oddsTicks.map(o => (
        <g key={o}>
          <line x1={xScale(o)} x2={xScale(o)} y1={padY} y2={h - padB} stroke="var(--bg-3)" strokeDasharray="2 3"/>
          <text x={xScale(o)} y={h - padB + 12} fill="var(--fg-3)" fontSize="9" textAnchor="middle" fontFamily="var(--mono)">{o}</text>
        </g>
      ))}
      {probTicks.map(p => (
        <g key={p}>
          <line x1={padX} x2={w - padR} y1={yScale(p)} y2={yScale(p)} stroke="var(--bg-3)" strokeDasharray="2 3"/>
          <text x={padX - 4} y={yScale(p) + 3} fill="var(--fg-3)" fontSize="9" textAnchor="end" fontFamily="var(--mono)">{(p*100).toFixed(0)}</text>
        </g>
      ))}
      <text x={padX} y={padY - 6} fontSize="9" fill="var(--fg-3)" fontFamily="var(--mono)">P(複) %</text>
      <text x={w - padR} y={h - 4} fontSize="9" fill="var(--fg-3)" fontFamily="var(--mono)" textAnchor="end">単勝オッズ (log)</text>
      {/* iso EV lines for ev_tan: prob = ev*3/odds */}
      {isoEvs.map(ev => {
        const path = oddsTicks.flatMap((_, i) => {
          const oddsRange = [];
          for (let lx = 0; lx <= 60; lx++) {
            const lo = xMin + (lx/60)*(xMax - xMin);
            const odds = Math.exp(lo);
            const p = ev * 3 / odds;
            if (p < 0 || p > yMax) continue;
            oddsRange.push(`${xScale(odds)},${yScale(p)}`);
          }
          return [oddsRange.join(" ")];
        }).join(" ");
        const isThr = Math.abs(ev - evThreshold) < 0.01;
        return (
          <g key={ev}>
            <polyline points={path} fill="none"
              stroke={isThr ? "var(--amber)" : "var(--line-bright)"}
              strokeWidth={isThr ? "1.4" : "0.8"}
              strokeDasharray={isThr ? "" : "3 3"}
            />
            {/* label */}
            <text x={xScale(135)} y={yScale(ev*3/135)} fill={isThr ? "var(--amber)" : "var(--fg-3)"}
              fontSize="9" fontFamily="var(--mono)" textAnchor="end">EV={ev.toFixed(1)}</text>
          </g>
        );
      })}
      {/* horses */}
      {horses.map(h => {
        const cx = xScale(h.odds), cy = yScale(h.prob);
        const positiveEV = h.ev_tan >= evThreshold;
        const color = positiveEV ? "var(--green)" : (h.ev_tan >= 0.8 ? "var(--amber)" : "var(--fg-3)");
        const r = 4 + Math.min(10, Math.max(0, h.ev_tan * 4));
        return (
          <g key={h.n}>
            <circle cx={cx} cy={cy} r={r} fill={color} fillOpacity="0.16" stroke={color} strokeWidth="1"/>
            <text x={cx} y={cy + 3} fill={color} fontSize="10" fontFamily="var(--mono)" fontWeight="700" textAnchor="middle">{h.n}</text>
          </g>
        );
      })}
    </svg>
  );
}

// Corner position (馬番が前/中/後で並ぶ)
// Stages: スタート / 道中 / 後3F / ゴール
function CornerPositions({ horses, w=560, h=260 }) {
  const stages = [
    { key: "start", label: "スタート", get: h => h.n }, // by gate
    { key: "mid",   label: "道中",     get: h => h.midp },
    { key: "late",  label: "後3F",     get: h => h.latep },
    { key: "goal",  label: "ゴール",   get: h => h.goalp },
  ];
  const padX = 50, padR = 20, padY = 22, padB = 18;
  const inW = w - padX - padR, inH = h - padY - padB;
  const N = horses.length;
  const xs = stages.map((_, i) => padX + (i/(stages.length-1)) * inW);
  const yScale = pos => padY + ((pos - 1) / (N - 1)) * inH;

  // For start: rank by gate (umaban). For others: rank by position.
  const ranked = stages.map(s => {
    const arr = [...horses].sort((a, b) => s.get(a) - s.get(b));
    const map = {};
    arr.forEach((h, i) => { map[h.n] = i + 1; });
    return map;
  });

  return (
    <svg width={w} height={h} style={{display:"block"}}>
      {/* stage labels */}
      {stages.map((s, i) => (
        <g key={s.key}>
          <line x1={xs[i]} x2={xs[i]} y1={padY - 6} y2={h - padB + 4} stroke="var(--line)" strokeDasharray="2 3"/>
          <text x={xs[i]} y={padY - 8} fill="var(--fg-2)" fontSize="10" textAnchor="middle" fontFamily="var(--mono)" textTransform="uppercase">{s.label}</text>
        </g>
      ))}
      {/* position axis */}
      {[1, Math.ceil(N/2), N].map(p => (
        <text key={p} x={padX - 8} y={yScale(p)+3} fill="var(--fg-3)" fontSize="9" textAnchor="end" fontFamily="var(--mono)">{p}位</text>
      ))}
      {/* lines per horse */}
      {horses.map(h => {
        const path = stages.map((s, i) => `${xs[i]},${yScale(ranked[i][h.n])}`).join(" L");
        const color = h.prob >= 0.4 ? "var(--amber)" : h.prob >= 0.25 ? "var(--cyan)" : "var(--fg-3)";
        const opacity = h.prob >= 0.4 ? 1 : h.prob >= 0.25 ? 0.7 : 0.3;
        return (
          <g key={h.n} opacity={opacity}>
            <path d={"M" + path} fill="none" stroke={color} strokeWidth={h.prob >= 0.4 ? 1.6 : 1} />
            {stages.map((s, i) => (
              <circle key={i} cx={xs[i]} cy={yScale(ranked[i][h.n])} r="3" fill={color}/>
            ))}
            <text x={xs[xs.length-1] + 6} y={yScale(ranked[ranked.length-1][h.n]) + 3}
              fill={color} fontSize="10" fontFamily="var(--mono)" fontWeight="700">{h.n}</text>
          </g>
        );
      })}
    </svg>
  );
}

Object.assign(window, {
  React, useState, useMemo, useEffect, useRef,
  fmtJPY, fmtPct, fmtNum, padN,
  PACE_LABEL, STYLE_LABEL, STYLE_LONG, IO_LABEL,
  parseRaceKey,
  Panel, Bar, Sparkline, Umaban, PacePill,
  EVScatter, CornerPositions,
});
