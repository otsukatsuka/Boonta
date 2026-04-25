// Top-level RACE TERMINAL app: routes between Dashboard / Race Detail / Backtest

const { TODAY, VENUES, RACES, HORSES_TENNOH, STRATEGIES } = window.BOONTA_DATA;

function TopBar({ tab, onTab, clock }) {
  const tabs = [
    { id: "dash", label: "DASH" },
    { id: "race", label: "RACE" },
    { id: "back", label: "BACKTEST" },
    { id: "data", label: "DATA" },
    { id: "model", label: "MODEL" },
  ];
  return (
    <div className="term-topbar">
      <div className="brand">BOONTA · TERM</div>
      {tabs.map(t => (
        <div key={t.id} className={"nav-tab " + (tab === t.id ? "active" : "")} onClick={() => onTab(t.id)}>
          {t.label}
        </div>
      ))}
      <div className="clock">
        <span><span className="dim">JRDB</span> <span style={{color:"var(--green)"}}>SYNC</span></span>
        <span className="dim">|</span>
        <span><span className="dim">MODAL</span> <span style={{color:"var(--green)"}}>READY</span></span>
        <span className="dim">|</span>
        <span><span className="dim">v2.04.25</span></span>
        <span className="live-dot" />
        <span style={{color:"var(--fg-1)"}}>{clock}</span>
      </div>
    </div>
  );
}

function StatusBar({ tab, evThreshold }) {
  return (
    <div className="term-statusbar">
      <span className="seg"><span className="k">CMD</span><span className="v">{tab.toUpperCase()}</span></span>
      <span className="seg"><span className="k">DATE</span><span className="v">2026-04-25</span></span>
      <span className="seg"><span className="k">RACES</span><span className="v">{RACES.length}</span></span>
      <span className="seg"><span className="k">EV-THR</span><span className="v amb">{evThreshold.toFixed(2)}</span></span>
      <span className="seg"><span className="k">PRESET</span><span className="v">best_quality</span></span>
      <span className="seg"><span className="k">FEAT</span><span className="v">35</span></span>
      <span className="seg"><span className="k">MODEL</span><span className="v ok">jrdb_predictor@2026-04-19</span></span>
      <span style={{marginLeft:"auto"}} className="seg"><span className="k">F1</span><span className="v">HELP</span> · <span className="k">/</span><span className="v">SEARCH</span> · <span className="k">G</span><span className="v">GO</span></span>
    </div>
  );
}

// ─────────── DASHBOARD ───────────
function DashboardScreen({ onOpenRace, evThreshold }) {
  const [date, setDate] = useState("2026-04-25");
  const grouped = useMemo(() => {
    const map = {};
    RACES.forEach(r => { (map[r.venue] ||= []).push(r); });
    Object.values(map).forEach(arr => arr.sort((a,b)=>a.race_no-b.race_no));
    return map;
  }, []);

  return (
    <div className="term-grid" style={{ gridTemplateColumns: "minmax(0, 2fr) minmax(0, 1fr)", gridTemplateRows: "auto minmax(0, 1fr)" }}>
      {/* command line */}
      <div style={{ gridColumn: "1 / -1", display:"flex", gap:8, padding:"8px 12px", background:"var(--bg-1)", borderBottom:"1px solid var(--line)" }}>
        <span style={{color:"var(--amber)", fontFamily:"var(--mono)"}}>$ boonta</span>
        <span className="dim">predict</span>
        <span>--date</span>
        <input className="term-input" style={{width:120}} value={date} onChange={e=>setDate(e.target.value)}/>
        <span>--ev-threshold</span>
        <input className="term-input" style={{width:60}} value={evThreshold.toFixed(2)} readOnly/>
        <button className="term-btn primary">RUN</button>
        <span style={{marginLeft:"auto"}} className="dim">↑↓ navigate · ↵ open · ESC back</span>
      </div>

      {/* races table */}
      <Panel title="本日のレース" meta={`${RACES.length} races · 3 tracks`} flush>
        <table className="dt">
          <thead>
            <tr>
              <th className="l">場 / R</th>
              <th className="l">レース名</th>
              <th>距離</th>
              <th>頭</th>
              <th>馬場</th>
              <th>ペース</th>
              <th>本命</th>
              <th>P(複)</th>
              <th>EV単</th>
              <th>EV複</th>
              <th>発走</th>
              <th>SIG</th>
            </tr>
          </thead>
          <tbody>
            {RACES.map(r => {
              const evGood = r.best_ev_tan >= evThreshold;
              return (
              <tr key={r.race_key} className="clickable" onClick={()=>onOpenRace(r.race_key)}>
                <td className="l"><span className="bold">{r.venue}</span> <span className="dim">{r.race_no}R</span></td>
                <td className="l">
                  <span className="bold">{r.name}</span>{" "}
                  <span className={"tag " + (r.grade === "G1" ? "amber" : r.grade === "G2" ? "cyan" : "")}>{r.grade}</span>
                </td>
                <td>{r.surface}{r.distance}</td>
                <td>{r.head_count}</td>
                <td className="dim">{r.condition}/{r.weather}</td>
                <td><span className={"pace-pill " + r.pace}>{r.pace}</span></td>
                <td className="l">
                  <span style={{display:"inline-flex", gap:6, alignItems:"center"}}>
                    <Umaban n={r.ml_top.umaban} waku={Math.ceil(r.ml_top.umaban/2)} sm/>
                    <span>{r.ml_top.name}</span>
                  </span>
                </td>
                <td className="amb tnum bold">{(r.ml_top.prob*100).toFixed(1)}</td>
                <td className={"tnum " + (evGood ? "pos bold" : "dim")}>{r.best_ev_tan.toFixed(2)}{evGood ? " ★" : ""}</td>
                <td className={"tnum " + (r.best_ev_fuku >= evThreshold ? "pos" : "dim")}>{r.best_ev_fuku.toFixed(2)}</td>
                <td className="dim tnum">{r.post_time}</td>
                <td>{evGood ? <span className="tag solid-amber">BUY</span> : r.best_ev_tan >= 0.9 ? <span className="tag amber">WATCH</span> : <span className="tag">SKIP</span>}</td>
              </tr>
            )})}
          </tbody>
        </table>
      </Panel>

      {/* sidebar: today's signals */}
      <div style={{ display:"grid", gridTemplateRows: "auto auto 1fr", gap:1, background:"var(--line)", minHeight:0 }}>
        <Panel title="EV シグナル" meta="ev_threshold">
          <div style={{display:"flex", flexDirection:"column", gap:8}}>
            {RACES.filter(r => r.best_ev_tan >= evThreshold).slice(0,4).map(r => (
              <div key={r.race_key} style={{display:"flex", justifyContent:"space-between", padding:"4px 0", borderBottom:"1px dashed var(--bg-3)"}}>
                <span><span className="bold">{r.venue}{r.race_no}R</span> <span className="dim">/ {r.name}</span></span>
                <span className="pos tnum bold">EV {r.best_ev_tan.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="ペース予想 分布" meta="6 races">
          <div style={{display:"flex", gap:6}}>
            {["H","M","S"].map(p => {
              const c = RACES.filter(r => r.pace === p).length;
              return (
                <div key={p} style={{flex: c || 0.3, padding:"6px 8px", background:"var(--bg-2)", border:`1px solid var(--line)`}}>
                  <div className={"pace-pill " + p}>{p}</div>
                  <div style={{fontSize:18, marginTop:4}} className="bold tnum">{c}</div>
                </div>
              );
            })}
          </div>
        </Panel>
        <Panel title="戦略 KPI (直近 3,453 レース)" meta="2025 backtest" flush>
          <table className="dt">
            <thead><tr><th className="l">戦略</th><th>ROI</th><th>HIT</th></tr></thead>
            <tbody>
              {STRATEGIES.map(s => (
                <tr key={s.id}>
                  <td className="l">{s.label}</td>
                  <td className={"tnum " + (s.roi >= 100 ? "pos bold" : s.roi >= 90 ? "amb" : "dim")}>{s.roi.toFixed(1)}%</td>
                  <td className="tnum dim">{s.hits}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>
    </div>
  );
}

// ─────────── RACE DETAIL ───────────
function RaceDetailScreen({ raceKey, evThreshold, onBack }) {
  const race = RACES.find(r => r.race_key === raceKey) || RACES[0];
  const horses = HORSES_TENNOH; // single set as sample
  const sortedByEv = useMemo(() => [...horses].sort((a,b)=>b.ev_tan-a.ev_tan), [horses]);
  const sortedByProb = useMemo(() => [...horses].sort((a,b)=>b.prob-a.prob), [horses]);

  // bets
  const tansho = sortedByEv.filter(h => h.ev_tan > evThreshold).slice(0,5).map(h=>h.n);
  const fukusho = sortedByEv.filter(h => h.ev_fuku > evThreshold).map(h=>h.n);
  const top3 = sortedByEv.slice(0,3).map(h=>h.n).sort((a,b)=>a-b);
  const top4 = sortedByEv.slice(0,4).map(h=>h.n).sort((a,b)=>a-b);
  const umaren = [];
  for (let i=0;i<top3.length;i++) for (let j=i+1;j<top3.length;j++) umaren.push([top3[i],top3[j]]);
  const sanrenpuku = [];
  for (let i=0;i<top4.length;i++) for (let j=i+1;j<top4.length;j++) for (let k=j+1;k<top4.length;k++) sanrenpuku.push([top4[i],top4[j],top4[k]]);

  // nagashi: axis = top ev_fuku above threshold
  const axis = sortedByEv.find(h => h.ev_fuku > evThreshold);
  const partners = sortedByEv.filter(h => h.n !== (axis && axis.n)).slice(0,5).map(h=>h.n);
  const nagashi = [];
  if (axis) {
    for (let i=0;i<partners.length;i++) for (let j=i+1;j<partners.length;j++) {
      nagashi.push([axis.n, partners[i], partners[j]].sort((a,b)=>a-b));
    }
  }

  return (
    <div style={{display:"grid", gridTemplateRows:"auto minmax(0,1fr)", flex:1, minHeight:0}}>
      {/* race header */}
      <div style={{display:"flex", alignItems:"center", gap:14, padding:"10px 14px", background:"var(--bg-1)", borderBottom:"1px solid var(--line)"}}>
        <button className="term-btn" onClick={onBack}>‹ DASH</button>
        <span className="dim">race_key</span>
        <span style={{color:"var(--amber)"}} className="bold">{race.race_key}</span>
        <span className="dim">|</span>
        <span style={{fontFamily:"var(--display)", fontSize:20, fontWeight:700, letterSpacing:"0.02em"}}>
          {race.venue} {race.race_no}R · {race.name}
        </span>
        <span className={"tag " + (race.grade==="G1"?"solid-amber":"amber")}>{race.grade}</span>
        <span className="dim">{race.surface}{race.distance}m · {race.condition}馬場 · {race.weather}</span>
        <span style={{marginLeft:"auto", display:"flex", gap:14, alignItems:"center"}}>
          <PacePill pace={race.pace} />
          <span className="dim">発走</span><span className="bold">{race.post_time}</span>
          <span className="dim">|</span>
          <span className="dim">頭数</span><span className="bold">{race.head_count}</span>
        </span>
      </div>

      <div className="term-grid" style={{ gridTemplateColumns: "minmax(0, 1.4fr) minmax(0, 1fr)", gridTemplateRows: "auto auto auto" }}>
        {/* horses table */}
        <div style={{gridRow:"1 / span 3"}}>
          <Panel title="出馬 + ML予測 + EV" meta={`${horses.length} horses · sorted by EV単`} flush>
            <table className="dt">
              <thead>
                <tr>
                  <th>馬</th><th>枠</th>
                  <th className="l">馬名 / 騎手</th>
                  <th>脚</th>
                  <th>IDM</th>
                  <th>道</th><th>後</th><th>ゴ</th><th>内外</th>
                  <th>単</th><th>複</th>
                  <th>P(複)</th>
                  <th>EV単</th><th>EV複</th>
                </tr>
              </thead>
              <tbody>
                {sortedByEv.map(h => (
                  <tr key={h.n}>
                    <td className="bold tnum">{h.n}</td>
                    <td><Umaban n={h.n} waku={h.w} sm/></td>
                    <td className="l">
                      <div className="bold">{h.name}</div>
                      <div className="dim" style={{fontSize:10}}>{h.jky} ({h.jky_i})</div>
                    </td>
                    <td>{STYLE_LABEL[h.rs]}</td>
                    <td className="tnum">{h.idm.toFixed(1)}</td>
                    <td className="tnum dim">{h.midp}</td>
                    <td className="tnum dim">{h.latep}</td>
                    <td className={"tnum " + (h.goalp <= 3 ? "amb bold" : "")}>{h.goalp}</td>
                    <td className="dim">{IO_LABEL[h.io]}</td>
                    <td className="tnum">{h.odds.toFixed(1)}</td>
                    <td className="tnum dim">{h.fuku.toFixed(1)}</td>
                    <td className="tnum">
                      <div style={{display:"flex", alignItems:"center", gap:6, justifyContent:"flex-end"}}>
                        <Bar value={h.prob} max={0.6} color="amber" w={36}/>
                        <span className={h.prob >= 0.4 ? "amb bold" : ""}>{(h.prob*100).toFixed(1)}</span>
                      </div>
                    </td>
                    <td className={"tnum bold " + (h.ev_tan >= evThreshold ? "pos" : h.ev_tan >= 0.8 ? "amb" : "dim")}>
                      {h.ev_tan.toFixed(2)}{h.ev_tan >= evThreshold ? " ★" : ""}
                    </td>
                    <td className={"tnum " + (h.ev_fuku >= evThreshold ? "pos" : "dim")}>{h.ev_fuku.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        </div>

        {/* corner positions */}
        <Panel title="位置取り予想 / コーナー" meta="start → mid → late3F → goal">
          <CornerPositions horses={horses} w={520} h={220}/>
        </Panel>

        {/* EV scatter */}
        <Panel title="EV 散布図" meta={`iso EV 線 · 閾値=${evThreshold.toFixed(2)}`}>
          <EVScatter horses={horses} evThreshold={evThreshold} w={520} h={240}/>
        </Panel>

        {/* bets */}
        <Panel title="買い目 (EV ベース)" meta={`ev_threshold=${evThreshold.toFixed(2)}`}>
          <BetsCard tansho={tansho} fukusho={fukusho} umaren={umaren} sanrenpuku={sanrenpuku} nagashi={nagashi} axis={axis ? axis.n : null}/>
        </Panel>
      </div>
    </div>
  );
}

function BetsCard({ tansho, fukusho, umaren, sanrenpuku, nagashi, axis }) {
  const Row = ({ label, code, count, children }) => (
    <div style={{padding:"8px 0", borderBottom:"1px dashed var(--bg-3)"}}>
      <div style={{display:"flex", justifyContent:"space-between", alignItems:"baseline"}}>
        <span><span className="amb bold">{label}</span> <span className="dim" style={{fontSize:10}}>{code}</span></span>
        <span className="dim tnum" style={{fontSize:10}}>{count}点</span>
      </div>
      <div style={{marginTop:4, fontFamily:"var(--mono)"}}>{children}</div>
    </div>
  );
  const nums = (arr) => arr.length ? arr.map(n => <span key={n} className="bold tnum" style={{display:"inline-block", padding:"1px 6px", border:"1px solid var(--line)", marginRight:4, marginBottom:4}}>{n}</span>) : <span className="dim">該当なし</span>;
  const combos = (arr) => arr.length ? arr.map((c, i) => <span key={i} className="tnum" style={{display:"inline-block", padding:"1px 6px", border:"1px solid var(--line)", marginRight:4, marginBottom:4}}>{c.join("-")}</span>) : <span className="dim">該当なし</span>;
  return (
    <div>
      <Row label="単勝" code="TANSHO" count={tansho.length}>{nums(tansho)}</Row>
      <Row label="複勝" code="FUKUSHO" count={fukusho.length}>{nums(fukusho)}</Row>
      <Row label="馬連 BOX" code="UMAREN · top3" count={umaren.length}>{combos(umaren)}</Row>
      <Row label="3連複 BOX" code="SANRENPUKU · top4" count={sanrenpuku.length}>{combos(sanrenpuku)}</Row>
      <Row label={`3連複 軸1頭流し (軸 ${axis ?? "-"})`} code="NAGASHI" count={nagashi.length}>{combos(nagashi)}</Row>
    </div>
  );
}

// ─────────── BACKTEST ───────────
function BacktestScreen({ evThreshold }) {
  const [strategyId, setStrategyId] = useState("ev_tansho");
  const sel = STRATEGIES.find(s => s.id === strategyId);
  const equity = sel.equity;
  const minE = Math.min(...equity.map(p=>p.cum), 0);
  const maxE = Math.max(...equity.map(p=>p.cum), 0);

  return (
    <div className="term-grid" style={{gridTemplateColumns:"minmax(0,1fr) minmax(0,2fr)", gridTemplateRows:"auto 1fr auto"}}>
      <div style={{gridColumn:"1 / -1", display:"flex", gap:8, padding:"8px 12px", background:"var(--bg-1)", borderBottom:"1px solid var(--line)", alignItems:"center"}}>
        <span style={{color:"var(--amber)", fontFamily:"var(--mono)"}}>$ boonta</span>
        <span className="dim">evaluate</span>
        <span>--date-range</span>
        <input className="term-input" style={{width:100}} defaultValue="20250101"/>
        <input className="term-input" style={{width:100}} defaultValue="20251228"/>
        <span>--strategy</span>
        <select className="term-input" value={strategyId} onChange={e=>setStrategyId(e.target.value)} style={{width:200}}>
          {STRATEGIES.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
        </select>
        <span>--ev-threshold</span>
        <input className="term-input" style={{width:60}} value={evThreshold.toFixed(2)} readOnly/>
        <button className="term-btn primary">RUN</button>
        <span className="dim" style={{marginLeft:"auto"}}>est. 5–15 min · iter 3,453 races on Modal</span>
      </div>

      {/* strategy comparison */}
      <Panel title="戦略マトリクス" meta="2025-01 → 2025-12" flush>
        <table className="dt">
          <thead>
            <tr>
              <th className="l">戦略</th>
              <th>KIND</th>
              <th>ROI</th>
              <th>EQUITY</th>
              <th>HITS</th>
              <th>BET RACES</th>
              <th>P&L</th>
            </tr>
          </thead>
          <tbody>
            {STRATEGIES.map(s => {
              const pnl = s.returned - s.invested;
              const minS = Math.min(...s.equity.map(p=>p.cum)), maxS = Math.max(...s.equity.map(p=>p.cum));
              return (
                <tr key={s.id} className="clickable" onClick={()=>setStrategyId(s.id)} style={{background: s.id === strategyId ? "oklch(0.22 0.02 75 / 0.3)" : ""}}>
                  <td className="l bold">{s.label}</td>
                  <td><span className={"tag " + (s.kind === "EV" ? "amber" : "cyan")}>{s.kind}</span></td>
                  <td className={"tnum bold " + (s.roi >= 100 ? "pos" : s.roi >= 90 ? "amb" : s.roi >= 70 ? "" : "neg")}>{s.roi.toFixed(1)}%</td>
                  <td><Sparkline data={s.equity.map(p=>p.cum)} w={120} h={20} color={pnl >= 0 ? "var(--green)" : "var(--red)"}/></td>
                  <td className="tnum dim">{s.hits.toLocaleString()}</td>
                  <td className="tnum dim">{s.bet_races.toLocaleString()} / {s.races.toLocaleString()}</td>
                  <td className={"tnum bold " + (pnl >= 0 ? "pos" : "neg")}>{pnl >= 0 ? "+" : ""}{fmtJPY(pnl)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Panel>

      {/* equity curve */}
      <Panel title={`Equity Curve · ${sel.label}`} meta={`ROI ${sel.roi.toFixed(1)}% · ${sel.bet_races.toLocaleString()} bets`}>
        <EquityCurve points={equity} w={700} h={320}/>
      </Panel>

      <Panel title="Threshold Sensitivity" meta="ev_threshold sweep · ev_tansho">
        <SensitivityTable />
      </Panel>

      <Panel title="戦略サマリー" meta={sel.label}>
        <SummaryStats sel={sel}/>
      </Panel>
    </div>
  );
}

function EquityCurve({ points, w, h }) {
  const padX = 50, padR = 20, padY = 16, padB = 28;
  const inW = w - padX - padR, inH = h - padY - padB;
  const ys = points.map(p => p.cum);
  const minE = Math.min(0, ...ys), maxE = Math.max(0, ...ys);
  const range = maxE - minE || 1;
  const xScale = i => padX + (i / (points.length - 1)) * inW;
  const yScale = v => padY + (1 - (v - minE) / range) * inH;
  const path = points.map((p, i) => `${xScale(i)},${yScale(p.cum)}`).join(" L");
  const zeroY = yScale(0);
  return (
    <svg width={w} height={h} style={{display:"block"}}>
      {[0, 0.25, 0.5, 0.75, 1].map(t => {
        const v = minE + t * range;
        return (
          <g key={t}>
            <line x1={padX} x2={w - padR} y1={padY + (1 - t) * inH} y2={padY + (1 - t) * inH} stroke="var(--bg-3)" strokeDasharray="2 3"/>
            <text x={padX - 6} y={padY + (1 - t) * inH + 3} fill="var(--fg-3)" fontSize="9" textAnchor="end" fontFamily="var(--mono)">{Math.round(v/1000)}k</text>
          </g>
        );
      })}
      <line x1={padX} x2={w - padR} y1={zeroY} y2={zeroY} stroke="var(--fg-3)" strokeWidth="1"/>
      {points.map((p, i) => (
        <text key={i} x={xScale(i)} y={h - 8} fill="var(--fg-3)" fontSize="9" textAnchor="middle" fontFamily="var(--mono)">{p.month.slice(5)}</text>
      ))}
      <path d={"M" + path} fill="none" stroke="var(--amber)" strokeWidth="1.6"/>
      {points.map((p, i) => (
        <circle key={i} cx={xScale(i)} cy={yScale(p.cum)} r="2" fill="var(--amber)"/>
      ))}
    </svg>
  );
}

function SensitivityTable() {
  const rows = [
    { thr: 0.80, races: 2456, roi: 88.4, hits: 412 },
    { thr: 0.90, races: 2114, roi: 92.1, hits: 348 },
    { thr: 1.00, races: 1802, roi: 97.3, hits: 287 },
    { thr: 1.10, races: 1402, roi: 101.8, hits: 218 },
    { thr: 1.20, races: 1054, roi: 104.6, hits: 168 },
    { thr: 1.30, races:  742, roi: 102.2, hits: 112 },
    { thr: 1.50, races:  308, roi:  94.8, hits:  42 },
  ];
  return (
    <table className="dt">
      <thead><tr><th>THR</th><th>BET RACES</th><th>HITS</th><th>ROI</th><th>HEAT</th></tr></thead>
      <tbody>
        {rows.map(r => (
          <tr key={r.thr}>
            <td className="tnum">{r.thr.toFixed(2)}</td>
            <td className="tnum dim">{r.races.toLocaleString()}</td>
            <td className="tnum dim">{r.hits}</td>
            <td className={"tnum bold " + (r.roi >= 100 ? "pos" : r.roi >= 90 ? "amb" : "")}>{r.roi.toFixed(1)}%</td>
            <td><Bar value={r.roi-70} max={40} color={r.roi >= 100 ? "green" : "amber"} w={80}/></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SummaryStats({ sel }) {
  const pnl = sel.returned - sel.invested;
  return (
    <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:12}}>
      <Stat k="戦略" v={sel.label}/>
      <Stat k="種別" v={sel.kind}/>
      <Stat k="レース数" v={sel.races.toLocaleString()}/>
      <Stat k="購入レース数" v={sel.bet_races.toLocaleString()}/>
      <Stat k="投資額" v={fmtJPY(sel.invested)}/>
      <Stat k="回収額" v={fmtJPY(sel.returned)}/>
      <Stat k="P&L" v={(pnl>=0?"+":"")+fmtJPY(pnl)} cls={pnl>=0?"pos":"neg"}/>
      <Stat k="回収率" v={sel.roi.toFixed(1)+"%"} cls={sel.roi>=100?"pos":sel.roi>=90?"amb":""} big/>
      <Stat k="的中数" v={sel.hits.toLocaleString()}/>
      <Stat k="的中率" v={(sel.hits/sel.bet_races*100).toFixed(1)+"%"}/>
    </div>
  );
}
function Stat({ k, v, cls="", big=false }) {
  return (
    <div>
      <div className="dim" style={{fontSize:10, textTransform:"uppercase", letterSpacing:"0.06em"}}>{k}</div>
      <div className={"tnum bold " + cls} style={{fontSize: big ? 22 : 14, fontFamily:"var(--mono)"}}>{v}</div>
    </div>
  );
}

// Wire up TWEAKS panel — only loaded inside the prototype (not the canvas mini-views)
function TweaksPanelWrap({ evThreshold, setEvThreshold }) {
  const TP = window.TweaksPanel;
  const TS = window.TweakSlider;
  const TSec = window.TweakSection;
  if (!TP) return null;
  return (
    <TP title="TWEAKS">
      <TSec title="EV THRESHOLD">
        <TS label="ev_threshold" value={evThreshold} min={0.8} max={1.5} step={0.05}
          onChange={setEvThreshold}/>
        <div className="dim" style={{fontSize:10, marginTop:6}}>
          1.00 = ブレイクイーブン. ↑で厳しめにピック.
        </div>
      </TSec>
    </TP>
  );
}

// ─────────── ROOT ───────────
window.RaceTerminalApp = function RaceTerminalApp({ initialTab = "dash", initialRace = null, showTweaks = true }) {
  const [tab, setTab] = useState(initialTab);
  const [raceKey, setRaceKey] = useState(initialRace || RACES[0].race_key);
  const [evThreshold, setEvThreshold] = useState(1.0);
  const [clock, setClock] = useState(new Date().toLocaleTimeString("ja-JP", { hour12: false }));

  useEffect(() => {
    const t = setInterval(() => setClock(new Date().toLocaleTimeString("ja-JP", { hour12: false })), 1000);
    return () => clearInterval(t);
  }, []);

  const openRace = (k) => { setRaceKey(k); setTab("race"); };

  return (
    <div className="terminal-frame" data-screen-label={tab}>
      <TopBar tab={tab} onTab={setTab} clock={clock}/>
      <div style={{flex:1, display:"flex", flexDirection:"column", minHeight:0}}>
        {tab === "dash" && <DashboardScreen onOpenRace={openRace} evThreshold={evThreshold}/>}
        {tab === "race" && <RaceDetailScreen raceKey={raceKey} evThreshold={evThreshold} onBack={()=>setTab("dash")}/>}
        {tab === "back" && <BacktestScreen evThreshold={evThreshold}/>}
        {tab === "data" && <PlaceholderScreen label="DATA · download / parse"/>}
        {tab === "model" && <PlaceholderScreen label="MODEL · Modal training jobs"/>}
      </div>
      <StatusBar tab={tab} evThreshold={evThreshold}/>
      {showTweaks && <TweaksPanelWrap evThreshold={evThreshold} setEvThreshold={setEvThreshold}/>}
    </div>
  );
};

function PlaceholderScreen({ label }) {
  return (
    <div style={{flex:1, display:"flex", alignItems:"center", justifyContent:"center", color:"var(--fg-3)", fontFamily:"var(--mono)"}}>
      <div style={{textAlign:"center"}}>
        <div style={{fontSize:14, color:"var(--amber)"}}>{label}</div>
        <div style={{marginTop:8, fontSize:11}}>not implemented in this preview</div>
      </div>
    </div>
  );
}
