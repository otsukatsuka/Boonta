// DATA & MODEL screens — Bloomberg-terminal cockpit for the pipeline + ML.
const { useState: useStateDM, useMemo: useMemoDM, useEffect: useEffectDM } = React;
const { Bar: BarDM, Sparkline: SparkDM } = window;

// ─────────── DATA SCREEN ───────────
const JRDB_FEEDS = [
  { id:"KYI", name:"出馬表 (KYI)",   bytes:842113,  rows:1428, last:"2026-04-25 06:02", status:"OK", lag:14 },
  { id:"SED", name:"成績 (SED)",     bytes:2103447, rows:8612, last:"2026-04-25 22:45", status:"OK", lag:8 },
  { id:"HJC", name:"払戻 (HJC)",     bytes:184226,  rows:864,  last:"2026-04-25 22:46", status:"OK", lag:8 },
  { id:"BAC", name:"番組表 (BAC)",   bytes:312009,  rows:208,  last:"2026-04-25 06:01", status:"OK", lag:14 },
  { id:"CHA", name:"調教 (CHA)",     bytes:521004,  rows:1820, last:"2026-04-24 18:30", status:"OK", lag:1112 },
  { id:"CYB", name:"調教コメ (CYB)", bytes:198440,  rows:912,  last:"2026-04-24 18:30", status:"WARN", lag:1112 },
  { id:"KAB", name:"開催 (KAB)",     bytes:8024,    rows:18,   last:"2026-04-25 06:00", status:"OK", lag:14 },
  { id:"OZ",  name:"オッズ (OZ)",    bytes:1804202, rows:1428, last:"2026-04-25 09:18", status:"OK", lag:1 },
];

// year x month coverage matrix (rows: 2020..2026, cols: 1..12)
const COVERAGE = (() => {
  const years = [2020, 2021, 2022, 2023, 2024, 2025, 2026];
  const m = {};
  years.forEach((y, yi) => {
    m[y] = [];
    for (let mo = 1; mo <= 12; mo++) {
      let v;
      if (y === 2026 && mo > 4) v = 0;
      else if (y === 2026 && mo === 4) v = 0.62;
      else {
        const noise = Math.sin(y * 13 + mo * 7) * 0.05;
        v = Math.min(1, 0.92 + noise + (yi >= 4 ? 0.05 : 0));
        if (y === 2020 && mo <= 3) v = 0.78 + noise; // covid gap
      }
      m[y].push(v);
    }
  });
  return { years, matrix: m };
})();

// 35 KYI features — sample
const FEATURES = [
  { name:"IDM",          jp:"IDM (基準指数)",       type:"num", missing:0.4,  min:30,   max:115,  mean:64.2,  std:11.1, importance:0.142 },
  { name:"jky_idx",      jp:"騎手指数",             type:"num", missing:0.0,  min:35,   max:90,   mean:60.4,  std:8.7,  importance:0.098 },
  { name:"info_idx",     jp:"情報指数",             type:"num", missing:0.2,  min:30,   max:95,   mean:60.8,  std:9.2,  importance:0.087 },
  { name:"trainer_idx",  jp:"調教師指数",           type:"num", missing:0.0,  min:38,   max:88,   mean:58.1,  std:7.4,  importance:0.051 },
  { name:"running_style",jp:"脚質",                  type:"cat", missing:1.2,  card:4,                                  importance:0.072 },
  { name:"sb_idx",       jp:"総合指数",             type:"num", missing:0.0,  min:32,   max:110,  mean:62.0,  std:10.2, importance:0.121 },
  { name:"odds_tan",     jp:"単勝オッズ",           type:"num", missing:0.0,  min:1.2,  max:498.0,mean:36.4,  std:54.1, importance:0.115 },
  { name:"weight",       jp:"馬体重",                type:"num", missing:0.3,  min:380,  max:566,  mean:476,   std:24,   importance:0.041 },
  { name:"weight_diff",  jp:"馬体重増減",           type:"num", missing:0.4,  min:-22,  max:22,   mean:0.1,   std:4.3,  importance:0.034 },
  { name:"ground_appro", jp:"馬場適性",             type:"cat", missing:0.6,  card:5,                                  importance:0.058 },
  { name:"distance_appro",jp:"距離適性",             type:"cat", missing:0.7,  card:5,                                  importance:0.062 },
  { name:"course_appro", jp:"コース適性",           type:"cat", missing:1.4,  card:4,                                  importance:0.029 },
  { name:"jky_win_rate", jp:"騎手勝率",             type:"num", missing:0.0,  min:0,    max:0.32, mean:0.072, std:0.05, importance:0.044 },
  { name:"jky_place_rate",jp:"騎手連対率",           type:"num", missing:0.0,  min:0,    max:0.48, mean:0.181, std:0.08, importance:0.038 },
  { name:"trainer_win_rate",jp:"調教師勝率",         type:"num", missing:0.0,  min:0,    max:0.28, mean:0.069, std:0.04, importance:0.027 },
  { name:"horse_age",    jp:"馬齢",                  type:"num", missing:0.0,  min:2,    max:10,   mean:4.2,   std:1.4,  importance:0.021 },
  { name:"sex",          jp:"性別",                  type:"cat", missing:0.0,  card:3,                                  importance:0.014 },
  { name:"frame",        jp:"枠番",                  type:"num", missing:0.0,  min:1,    max:8,    mean:4.5,   std:2.3,  importance:0.018 },
];

const CLI_LOG = [
  { ts:"06:02:14", cmd:"download --feed KYI --date 2026-04-25", ok:true,  dur:8.2 },
  { ts:"06:02:22", cmd:"parse kyi --file ./data/kyi/KYI260425.txt", ok:true,  dur:1.4 },
  { ts:"08:30:00", cmd:"predict --date 2026-04-25 --preset best_quality", ok:true, dur:42.1 },
  { ts:"22:45:11", cmd:"download --feed SED HJC --date 2026-04-25", ok:true, dur:11.8 },
  { ts:"22:46:01", cmd:"parse sed --file ./data/sed/SED260425.txt", ok:true, dur:2.9 },
  { ts:"22:48:30", cmd:"evaluate --from 2025-01-01 --to 2025-12-31", ok:true, dur:128.4 },
  { ts:"23:01:18", cmd:"train --preset best_quality --time-limit 3600", ok:false, dur:3601.0, err:"OOM at fold 3 (16GB ceiling)" },
];

function StatBlock({ k, v, sub, cls="" }) {
  return (
    <div style={{padding:"10px 14px", borderRight:"1px solid var(--line)", flex:1, minWidth:0}}>
      <div style={{fontSize:9, color:"var(--fg-3)", textTransform:"uppercase", letterSpacing:"0.1em"}}>{k}</div>
      <div className={"tnum bold "+cls} style={{fontFamily:"var(--mono)", fontSize:22, lineHeight:"1.1", marginTop:2}}>{v}</div>
      {sub && <div style={{fontSize:9, color:"var(--fg-3)", marginTop:2}}>{sub}</div>}
    </div>
  );
}

function fmtBytes(b) {
  if (b < 1024) return b + " B";
  if (b < 1024*1024) return (b/1024).toFixed(1) + " KB";
  return (b/1024/1024).toFixed(2) + " MB";
}
function fmtLag(min) {
  if (min < 60) return min + "m";
  if (min < 1440) return Math.floor(min/60) + "h " + (min%60) + "m";
  return Math.floor(min/1440) + "d " + Math.floor((min%1440)/60) + "h";
}

function CoverageHeatmap() {
  const cell = 28, gap = 2, monthsW = 12 * cell + 11 * gap;
  return (
    <div style={{fontFamily:"var(--mono)"}}>
      <div style={{display:"grid", gridTemplateColumns:`44px ${monthsW}px`, columnGap:8, alignItems:"end", marginBottom:4}}>
        <div></div>
        <div style={{display:"grid", gridTemplateColumns:`repeat(12, ${cell}px)`, columnGap:gap}}>
          {Array.from({length:12}, (_,i) => (
            <div key={i} style={{fontSize:9, color:"var(--fg-3)", textAlign:"center"}}>{i+1}</div>
          ))}
        </div>
      </div>
      {COVERAGE.years.map(y => (
        <div key={y} style={{display:"grid", gridTemplateColumns:`44px ${monthsW}px`, columnGap:8, alignItems:"center", marginBottom:gap}}>
          <div style={{fontSize:11, color:"var(--fg-2)", textAlign:"right"}}>{y}</div>
          <div style={{display:"grid", gridTemplateColumns:`repeat(12, ${cell}px)`, columnGap:gap}}>
            {COVERAGE.matrix[y].map((v, m) => {
              const hue = v === 0 ? "var(--bg-2)" : v < 0.85 ? "oklch(0.55 0.15 30)" : v < 0.95 ? "oklch(0.7 0.16 75)" : "oklch(0.78 0.18 145)";
              return (
                <div key={m} title={`${y}-${String(m+1).padStart(2,"0")}: ${(v*100).toFixed(0)}%`}
                  style={{height:cell, background:hue, opacity: v === 0 ? 1 : 0.45 + v*0.55, display:"flex", alignItems:"center", justifyContent:"center", fontSize:9, color: v >= 0.85 ? "oklch(0.15 0 0)" : "var(--fg-3)"}}>
                  {v === 0 ? "" : Math.round(v*100)}
                </div>
              );
            })}
          </div>
        </div>
      ))}
      <div style={{display:"flex", alignItems:"center", gap:10, marginTop:10, fontSize:10, color:"var(--fg-3)"}}>
        <span>0%</span>
        <div style={{width:8, height:10, background:"var(--bg-2)"}}/>
        <div style={{width:8, height:10, background:"oklch(0.55 0.15 30)", opacity:0.85}}/>
        <div style={{width:8, height:10, background:"oklch(0.7 0.16 75)", opacity:0.9}}/>
        <div style={{width:8, height:10, background:"oklch(0.78 0.18 145)"}}/>
        <span>100%</span>
        <span style={{marginLeft:"auto"}}>cell = レース取得率/月</span>
      </div>
    </div>
  );
}

function FeatureMiniHist({ feat, w=120, h=24 }) {
  if (feat.type !== "num") {
    // categorical bars (cardinality)
    const bars = Array.from({length: feat.card || 4}, (_, i) => 0.3 + Math.sin(i * 1.7) * 0.3 + Math.random()*0.2);
    return (
      <svg width={w} height={h}>
        {bars.map((v, i) => {
          const bw = w / bars.length - 2;
          return <rect key={i} x={i * (bw + 2)} y={h - v*h} width={bw} height={v*h} fill="var(--cyan)" opacity={0.7}/>;
        })}
      </svg>
    );
  }
  // numeric histogram (synthetic 12 bars Gaussian-ish)
  const bars = Array.from({length: 18}, (_, i) => {
    const x = (i - 8.5) / 4.5;
    return Math.max(0.04, Math.exp(-x*x) * 0.95 + (Math.sin(i * (feat.importance*30)) * 0.08));
  });
  return (
    <svg width={w} height={h}>
      {bars.map((v, i) => {
        const bw = w / bars.length;
        return <rect key={i} x={i * bw} y={h - v*h} width={bw - 0.5} height={v*h} fill="var(--amber)" opacity={0.8}/>;
      })}
    </svg>
  );
}

function DataScreen() {
  const [sel, setSel] = useStateDM("IDM");
  const totalBytes = JRDB_FEEDS.reduce((s,f)=>s+f.bytes,0);
  const totalRows = JRDB_FEEDS.reduce((s,f)=>s+f.rows,0);
  const okFeeds = JRDB_FEEDS.filter(f=>f.status==="OK").length;

  return (
    <div style={{display:"flex", flexDirection:"column", flex:1, minHeight:0}}>
      {/* stat strip */}
      <div style={{display:"flex", borderBottom:"1px solid var(--line)", background:"var(--bg-1)"}}>
        <StatBlock k="FEEDS" v={`${okFeeds}/${JRDB_FEEDS.length}`} sub="JRDB sources" cls="pos"/>
        <StatBlock k="LATEST" v="06:02 JST" sub="2026-04-25 KYI"/>
        <StatBlock k="ROWS · TODAY" v={totalRows.toLocaleString()} sub="all feeds"/>
        <StatBlock k="SIZE · TODAY" v={fmtBytes(totalBytes)} sub="raw uncompressed"/>
        <StatBlock k="FEATURES" v="35" sub="KYI-derived" cls="amb"/>
        <StatBlock k="DATASET" v="2020-01 → 2026-04" sub="6.3 yrs"/>
        <StatBlock k="RACES" v="22,461" sub="parsed total"/>
      </div>

      <div className="term-grid" style={{gridTemplateColumns:"minmax(0,1.1fr) minmax(0,1fr)", gridTemplateRows:"auto minmax(0,1fr) auto"}}>
        {/* JRDB feeds table */}
        <div className="panel">
          <div className="panel-head">
            <span className="title">JRDB FEEDS</span>
            <span className="meta">日次同期 · 8 sources · last sync 06:02 JST</span>
          </div>
          <div className="panel-body">
            <table className="dt">
              <thead><tr><th className="l">FEED</th><th className="l">名称</th><th>ROWS</th><th>SIZE</th><th>LAST</th><th>LAG</th><th>ST</th></tr></thead>
              <tbody>
                {JRDB_FEEDS.map(f => (
                  <tr key={f.id}>
                    <td className="l bold amb tnum">{f.id}</td>
                    <td className="l">{f.name}</td>
                    <td className="tnum">{f.rows.toLocaleString()}</td>
                    <td className="tnum dim">{fmtBytes(f.bytes)}</td>
                    <td className="tnum dim">{f.last.split(" ")[1]}</td>
                    <td className={"tnum " + (f.lag < 60 ? "pos" : f.lag < 1440 ? "amb" : "neg")}>{fmtLag(f.lag)}</td>
                    <td><span className={"tag " + (f.status==="OK" ? "solid-green" : "amber")}>{f.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Coverage heatmap */}
        <div className="panel">
          <div className="panel-head">
            <span className="title">DATASET COVERAGE</span>
            <span className="meta">月次レース取得率 (年×月)</span>
          </div>
          <div className="panel-body">
            <CoverageHeatmap/>
          </div>
        </div>

        {/* Feature inspector */}
        <div className="panel" style={{gridColumn:"1 / span 2"}}>
          <div className="panel-head">
            <span className="title">KYI FEATURE INSPECTOR</span>
            <span className="meta">35 features · click row to inspect distribution</span>
          </div>
          <div className="panel-body" style={{display:"grid", gridTemplateColumns:"minmax(0,1.2fr) minmax(0,1fr)", gap:14}}>
            <table className="dt">
              <thead><tr><th className="l">NAME</th><th className="l">TYPE</th><th>MIN</th><th>MEAN</th><th>MAX</th><th>NA%</th><th>IMP</th><th>HIST</th></tr></thead>
              <tbody>
                {FEATURES.map(f => (
                  <tr key={f.name} onClick={()=>setSel(f.name)} style={{background: sel===f.name ? "oklch(0.22 0.02 75 / 0.3)" : "transparent", cursor:"pointer"}}>
                    <td className="l bold">{f.name}</td>
                    <td className="l dim">{f.type === "num" ? "num" : `cat (${f.card})`}</td>
                    <td className="tnum dim">{f.type==="num" ? f.min : "-"}</td>
                    <td className="tnum">{f.type==="num" ? f.mean.toFixed(2) : "-"}</td>
                    <td className="tnum dim">{f.type==="num" ? f.max : "-"}</td>
                    <td className={"tnum " + (f.missing > 1 ? "amb" : "dim")}>{f.missing.toFixed(1)}</td>
                    <td className="tnum amb bold">{(f.importance*100).toFixed(1)}</td>
                    <td><FeatureMiniHist feat={f} w={100} h={20}/></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{padding:14, background:"var(--bg-0)", border:"1px solid var(--bg-3)"}}>
              {(() => {
                const f = FEATURES.find(x=>x.name===sel) || FEATURES[0];
                return (
                  <div>
                    <div style={{display:"flex", justifyContent:"space-between", alignItems:"baseline", marginBottom:6}}>
                      <span className="bold" style={{fontSize:14}}>{f.name}</span>
                      <span className="dim" style={{fontSize:10}}>{f.jp}</span>
                    </div>
                    <FeatureMiniHist feat={f} w={350} h={70}/>
                    <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:"6px 12px", marginTop:10, fontSize:11, fontFamily:"var(--mono)"}}>
                      <div className="dim">type</div><div>{f.type === "num" ? "numeric (float)" : `categorical · cardinality ${f.card}`}</div>
                      {f.type === "num" && <><div className="dim">min / max</div><div className="tnum">{f.min} / {f.max}</div></>}
                      {f.type === "num" && <><div className="dim">mean ± std</div><div className="tnum">{f.mean.toFixed(2)} ± {f.std.toFixed(2)}</div></>}
                      <div className="dim">missing</div><div className={f.missing > 1 ? "amb tnum" : "tnum"}>{f.missing.toFixed(2)}%</div>
                      <div className="dim">importance</div><div className="amb bold tnum">{(f.importance*100).toFixed(2)}%</div>
                    </div>
                  </div>
                );
              })()}
            </div>
          </div>
        </div>

        {/* CLI log */}
        <div className="panel" style={{gridColumn:"1 / span 2"}}>
          <div className="panel-head">
            <span className="title">CLI ACTIVITY LOG</span>
            <span className="meta">直近 24h のパイプライン実行履歴</span>
          </div>
          <div className="panel-body" style={{fontFamily:"var(--mono)", fontSize:12}}>
            {CLI_LOG.map((l, i) => (
              <div key={i} style={{display:"grid", gridTemplateColumns:"70px 1fr 60px 50px", gap:10, padding:"4px 0", borderBottom:"1px dashed var(--bg-2)", alignItems:"baseline"}}>
                <span className="dim tnum">{l.ts}</span>
                <span><span className="amb">$</span> {l.cmd} {l.err && <span className="neg" style={{fontSize:11}}>· {l.err}</span>}</span>
                <span className="dim tnum">{l.dur < 60 ? l.dur.toFixed(1)+"s" : (l.dur/60).toFixed(1)+"m"}</span>
                <span className={l.ok ? "pos" : "neg"} style={{fontSize:10, fontWeight:700}}>{l.ok ? "✓ OK" : "✗ FAIL"}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────── MODEL SCREEN ───────────
const TRAIN_RUNS = [
  { id:"v2.04.25", date:"2026-04-25", preset:"best_quality", logloss:0.5821, auc:0.7124, brier:0.1742, hit3:0.4812, time:3580, status:"DEPLOYED" },
  { id:"v2.04.18", date:"2026-04-18", preset:"best_quality", logloss:0.5847, auc:0.7098, brier:0.1758, hit3:0.4780, time:3554, status:"archived" },
  { id:"v2.04.11", date:"2026-04-11", preset:"high_quality", logloss:0.5891, auc:0.7042, brier:0.1781, hit3:0.4731, time:1812, status:"archived" },
  { id:"v2.04.04", date:"2026-04-04", preset:"best_quality", logloss:0.5819, auc:0.7131, brier:0.1740, hit3:0.4824, time:3604, status:"archived" },
  { id:"v2.03.28", date:"2026-03-28", preset:"medium",       logloss:0.5942, auc:0.6981, brier:0.1812, hit3:0.4612, time:842,  status:"archived" },
  { id:"v2.03.21", date:"2026-03-21", preset:"high_quality", logloss:0.5886, auc:0.7051, brier:0.1779, hit3:0.4742, time:1834, status:"archived" },
];
const LEADERBOARD = [
  { model:"WeightedEnsemble_L2",  logloss:0.5821, auc:0.7124, weight:1.000, time:42 },
  { model:"LightGBM_BAG_L1",      logloss:0.5894, auc:0.7062, weight:0.342, time:1240 },
  { model:"CatBoost_BAG_L1",      logloss:0.5908, auc:0.7048, weight:0.281, time:1820 },
  { model:"XGBoost_BAG_L1",       logloss:0.5921, auc:0.7039, weight:0.198, time:980 },
  { model:"NeuralNetTorch_BAG_L1",logloss:0.6034, auc:0.6952, weight:0.121, time:2410 },
  { model:"RandomForest_BAG_L1",  logloss:0.6112, auc:0.6884, weight:0.058, time:412 },
  { model:"ExtraTrees_BAG_L1",    logloss:0.6128, auc:0.6871, weight:0.000, time:380 },
  { model:"KNeighbors_BAG_L1",    logloss:0.6478, auc:0.6502, weight:0.000, time:84  },
];
const FEATURE_IMP = [
  { f:"IDM",          imp:0.142 },
  { f:"sb_idx",       imp:0.121 },
  { f:"odds_tan",     imp:0.115 },
  { f:"jky_idx",      imp:0.098 },
  { f:"info_idx",     imp:0.087 },
  { f:"running_style",imp:0.072 },
  { f:"distance_appro",imp:0.062 },
  { f:"ground_appro", imp:0.058 },
  { f:"trainer_idx",  imp:0.051 },
  { f:"jky_win_rate", imp:0.044 },
  { f:"weight",       imp:0.041 },
  { f:"jky_place_rate",imp:0.038 },
  { f:"weight_diff",  imp:0.034 },
  { f:"course_appro", imp:0.029 },
  { f:"trainer_win_rate",imp:0.027 },
  { f:"horse_age",    imp:0.021 },
  { f:"frame",        imp:0.018 },
  { f:"sex",          imp:0.014 },
];

// Calibration: 10 bins of pred prob vs actual rate
const CALIB = (() => {
  const bins = [];
  for (let i = 0; i < 10; i++) {
    const p = (i + 0.5) / 10;
    // slight under-confidence at high end
    const actual = p - 0.025 * Math.sin(p * Math.PI * 2) + (Math.random() - 0.5) * 0.02;
    const n = Math.round(2200 - i * 180 + Math.random() * 100);
    bins.push({ pred: p, actual: Math.max(0, Math.min(1, actual)), n });
  }
  return bins;
})();

function CalibrationChart({ w=420, h=260 }) {
  const pad = { l:36, r:8, t:8, b:28 };
  const iw = w - pad.l - pad.r, ih = h - pad.t - pad.b;
  const xToPx = x => pad.l + x * iw;
  const yToPx = y => pad.t + (1 - y) * ih;
  return (
    <svg width={w} height={h} style={{display:"block"}}>
      {/* grid */}
      {[0, 0.2, 0.4, 0.6, 0.8, 1].map((g, i) => (
        <g key={i}>
          <line x1={xToPx(g)} y1={pad.t} x2={xToPx(g)} y2={pad.t + ih} stroke="var(--bg-2)"/>
          <line x1={pad.l} y1={yToPx(g)} x2={pad.l + iw} y2={yToPx(g)} stroke="var(--bg-2)"/>
          <text x={xToPx(g)} y={h - 10} fontSize="9" fill="var(--fg-3)" textAnchor="middle" fontFamily="var(--mono)">{g.toFixed(1)}</text>
          <text x={pad.l - 6} y={yToPx(g) + 3} fontSize="9" fill="var(--fg-3)" textAnchor="end" fontFamily="var(--mono)">{g.toFixed(1)}</text>
        </g>
      ))}
      {/* perfect line */}
      <line x1={xToPx(0)} y1={yToPx(0)} x2={xToPx(1)} y2={yToPx(1)} stroke="var(--fg-3)" strokeDasharray="4 4" strokeWidth="1"/>
      {/* calibration curve */}
      <path d={"M " + CALIB.map(b => `${xToPx(b.pred)},${yToPx(b.actual)}`).join(" L ")} fill="none" stroke="var(--amber)" strokeWidth="1.8"/>
      {CALIB.map((b, i) => (
        <circle key={i} cx={xToPx(b.pred)} cy={yToPx(b.actual)} r={3.5} fill="var(--amber)"/>
      ))}
      {/* axis labels */}
      <text x={pad.l + iw/2} y={h - 1} fontSize="10" fill="var(--fg-2)" textAnchor="middle" fontFamily="var(--mono)">predicted P(複)</text>
      <text x={10} y={pad.t + ih/2} fontSize="10" fill="var(--fg-2)" textAnchor="middle" fontFamily="var(--mono)" transform={`rotate(-90 10 ${pad.t + ih/2})`}>actual rate</text>
    </svg>
  );
}

function ROCChart({ w=420, h=260, auc=0.7124 }) {
  const pad = { l:36, r:8, t:8, b:28 };
  const iw = w - pad.l - pad.r, ih = h - pad.t - pad.b;
  const xToPx = x => pad.l + x * iw;
  const yToPx = y => pad.t + (1 - y) * ih;
  // synthetic ROC: y = x^k where k chosen so AUC ≈ target
  // AUC of y=x^k (bowed to top-left) is k/(k+1) → no, bowed top-left means concave
  // simpler: y = 1 - (1-x)^a, AUC = 1 - 1/(a+1) → a = 1/(1-AUC) - 1
  const a = 1/(1-auc) - 1;
  const pts = [];
  for (let i = 0; i <= 50; i++) {
    const x = i/50;
    const y = 1 - Math.pow(1 - x, a);
    pts.push([x, y]);
  }
  return (
    <svg width={w} height={h} style={{display:"block"}}>
      {[0, 0.2, 0.4, 0.6, 0.8, 1].map((g, i) => (
        <g key={i}>
          <line x1={xToPx(g)} y1={pad.t} x2={xToPx(g)} y2={pad.t + ih} stroke="var(--bg-2)"/>
          <line x1={pad.l} y1={yToPx(g)} x2={pad.l + iw} y2={yToPx(g)} stroke="var(--bg-2)"/>
          <text x={xToPx(g)} y={h - 10} fontSize="9" fill="var(--fg-3)" textAnchor="middle" fontFamily="var(--mono)">{g.toFixed(1)}</text>
          <text x={pad.l - 6} y={yToPx(g) + 3} fontSize="9" fill="var(--fg-3)" textAnchor="end" fontFamily="var(--mono)">{g.toFixed(1)}</text>
        </g>
      ))}
      <line x1={xToPx(0)} y1={yToPx(0)} x2={xToPx(1)} y2={yToPx(1)} stroke="var(--fg-3)" strokeDasharray="4 4"/>
      {/* fill under curve */}
      <path d={"M " + xToPx(0) + " " + yToPx(0) + " " + pts.map(p => `L ${xToPx(p[0])},${yToPx(p[1])}`).join(" ") + ` L ${xToPx(1)},${yToPx(0)} Z`} fill="var(--amber)" opacity="0.12"/>
      <path d={"M " + pts.map(p => `${xToPx(p[0])},${yToPx(p[1])}`).join(" L ")} fill="none" stroke="var(--amber)" strokeWidth="1.8"/>
      <text x={pad.l + iw - 8} y={pad.t + ih - 8} fontSize="14" fill="var(--amber)" textAnchor="end" fontFamily="var(--mono)" fontWeight="700">AUC {auc.toFixed(4)}</text>
      <text x={pad.l + iw/2} y={h - 1} fontSize="10" fill="var(--fg-2)" textAnchor="middle" fontFamily="var(--mono)">false positive rate</text>
      <text x={10} y={pad.t + ih/2} fontSize="10" fill="var(--fg-2)" textAnchor="middle" fontFamily="var(--mono)" transform={`rotate(-90 10 ${pad.t + ih/2})`}>true positive rate</text>
    </svg>
  );
}

function ModelScreen() {
  const [runId, setRunId] = useStateDM("v2.04.25");
  const sel = TRAIN_RUNS.find(r => r.id === runId) || TRAIN_RUNS[0];

  return (
    <div style={{display:"flex", flexDirection:"column", flex:1, minHeight:0}}>
      <div style={{display:"flex", borderBottom:"1px solid var(--line)", background:"var(--bg-1)"}}>
        <StatBlock k="DEPLOYED" v="v2.04.25" sub="2026-04-25 23:01" cls="amb"/>
        <StatBlock k="LOG LOSS" v={sel.logloss.toFixed(4)} sub="hold-out 2025-Q4" cls="pos"/>
        <StatBlock k="ROC AUC" v={sel.auc.toFixed(4)} sub="is_place" cls="pos"/>
        <StatBlock k="BRIER" v={sel.brier.toFixed(4)} sub="lower=better"/>
        <StatBlock k="HIT@3" v={(sel.hit3*100).toFixed(2)+"%"} sub="複勝命中率" cls="amb"/>
        <StatBlock k="PRESET" v={sel.preset} sub="AutoGluon"/>
        <StatBlock k="TRAIN TIME" v={(sel.time/60).toFixed(1)+"m"} sub="Modal A10"/>
      </div>

      <div className="term-grid" style={{gridTemplateColumns:"minmax(0,1.2fr) minmax(0,1fr) minmax(0,1fr)", gridTemplateRows:"auto minmax(0,1fr)"}}>
        {/* Training runs */}
        <div className="panel" style={{gridColumn:"1 / span 3"}}>
          <div className="panel-head">
            <span className="title">TRAINING RUNS</span>
            <span className="meta">直近 6 ラン · クリックで詳細 · DEPLOYED = 本番反映中</span>
          </div>
          <div className="panel-body">
            <table className="dt">
              <thead><tr><th className="l">RUN</th><th className="l">DATE</th><th className="l">PRESET</th><th>LOGLOSS</th><th>AUC</th><th>BRIER</th><th>HIT@3</th><th>TIME</th><th>TREND</th><th>STATUS</th></tr></thead>
              <tbody>
                {TRAIN_RUNS.map(r => {
                  const trend = TRAIN_RUNS.slice().reverse().map(x=>1-x.logloss);
                  return (
                    <tr key={r.id} onClick={()=>setRunId(r.id)} style={{background: r.id===runId ? "oklch(0.22 0.02 75 / 0.3)" : "transparent", cursor:"pointer"}}>
                      <td className="l bold amb tnum">{r.id}</td>
                      <td className="l dim tnum">{r.date}</td>
                      <td className="l">{r.preset}</td>
                      <td className="tnum bold">{r.logloss.toFixed(4)}</td>
                      <td className="tnum">{r.auc.toFixed(4)}</td>
                      <td className="tnum dim">{r.brier.toFixed(4)}</td>
                      <td className="tnum amb">{(r.hit3*100).toFixed(2)}</td>
                      <td className="tnum dim">{(r.time/60).toFixed(0)}m</td>
                      <td>{r.id === runId && <SparkDM data={trend} w={80} h={16} color="var(--amber)"/>}</td>
                      <td><span className={"tag " + (r.status==="DEPLOYED" ? "solid-amber" : "")} style={{fontSize:9}}>{r.status}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Leaderboard */}
        <div className="panel">
          <div className="panel-head">
            <span className="title">LEADERBOARD · {runId}</span>
            <span className="meta">AutoGluon ensemble構成 · weight=L2重み</span>
          </div>
          <div className="panel-body">
            <table className="dt">
              <thead><tr><th className="l">MODEL</th><th>LOGLOSS</th><th>AUC</th><th>WEIGHT</th></tr></thead>
              <tbody>
                {LEADERBOARD.map((m, i) => (
                  <tr key={m.model}>
                    <td className="l">
                      <span className="dim tnum" style={{marginRight:6}}>{String(i+1).padStart(2,"0")}</span>
                      <span className={i === 0 ? "amb bold" : ""}>{m.model}</span>
                    </td>
                    <td className={"tnum " + (i === 0 ? "bold" : "dim")}>{m.logloss.toFixed(4)}</td>
                    <td className="tnum">{m.auc.toFixed(4)}</td>
                    <td>
                      <div style={{display:"flex", alignItems:"center", gap:6}}>
                        <BarDM value={m.weight} max={1} color={m.weight > 0 ? "amber" : "amber"} w={50}/>
                        <span className={"tnum " + (m.weight === 0 ? "dim" : "bold")}>{m.weight.toFixed(3)}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Calibration */}
        <div className="panel">
          <div className="panel-head">
            <span className="title">CALIBRATION</span>
            <span className="meta">予測確率 vs 実測命中率 · 10 bins</span>
          </div>
          <div className="panel-body" style={{display:"flex", flexDirection:"column", gap:8}}>
            <CalibrationChart w={420} h={250}/>
            <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:"4px 12px", fontSize:11, fontFamily:"var(--mono)", paddingTop:6, borderTop:"1px dashed var(--bg-3)"}}>
              <span className="dim">ECE (expected calibration error)</span><span className="amb tnum bold">0.0142</span>
              <span className="dim">MCE (max calibration error)</span><span className="tnum">0.0381</span>
              <span className="dim">over/under</span><span>slightly under-confident @ p≥0.5</span>
            </div>
          </div>
        </div>

        {/* Feature importance */}
        <div className="panel">
          <div className="panel-head">
            <span className="title">FEATURE IMPORTANCE</span>
            <span className="meta">Top 18 / 35 · permutation</span>
          </div>
          <div className="panel-body">
            {FEATURE_IMP.map(f => (
              <div key={f.f} style={{display:"grid", gridTemplateColumns:"110px 1fr 50px", gap:8, alignItems:"center", padding:"3px 0", fontFamily:"var(--mono)", fontSize:11}}>
                <span className="bold">{f.f}</span>
                <BarDM value={f.imp} max={0.15} color="amber" w="100%"/>
                <span className="tnum amb bold" style={{textAlign:"right"}}>{(f.imp*100).toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

window.DataScreen = DataScreen;
window.ModelScreen = ModelScreen;
