// Variation C — RADAR: bold, more visual.
// Race detail re-imagined as a track-overhead radar; dashboard as a constellation grid.

const { RACES: RAD_RACES, HORSES_TENNOH: RAD_HORSES, STRATEGIES: RAD_STRATS } = window.BOONTA_DATA;

// Big dial: track overhead with positions at 4 stages mapped to a curved track.
function TrackRadar({ horses, w=560, h=420 }) {
  const cx = w/2, cy = h/2 + 30;
  // 4 nested ellipses (start, mid, late, goal). Goal at innermost.
  const stages = [
    { key:"start", label:"START",  rx: 230, ry: 150, get: h => h.n },
    { key:"mid",   label:"道中",    rx: 195, ry: 125, get: h => h.midp },
    { key:"late",  label:"後3F",    rx: 160, ry: 100, get: h => h.latep },
    { key:"goal",  label:"GOAL",   rx: 125, ry: 78, get: h => h.goalp },
  ];
  const N = horses.length;
  // angles span -200° to 20° (going around the curve)
  const aStart = -Math.PI * 1.05, aEnd = Math.PI * 0.05;
  const angle = (rank) => aStart + ((rank - 1) / (N - 1)) * (aEnd - aStart);

  // ranking per stage
  const ranked = stages.map(s => {
    const arr = [...horses].sort((a,b)=>s.get(a)-s.get(b));
    const map = {};
    arr.forEach((h,i)=>{ map[h.n] = i+1; });
    return map;
  });

  return (
    <svg width={w} height={h} style={{display:"block"}}>
      {/* track lanes */}
      {stages.map((s, i) => (
        <ellipse key={s.key} cx={cx} cy={cy} rx={s.rx} ry={s.ry}
          fill="none" stroke={i === 3 ? "var(--amber-dim)" : "var(--line)"}
          strokeWidth={i === 3 ? 1.6 : 1}
          strokeDasharray={i === 0 ? "" : i === 3 ? "" : "3 4"}/>
      ))}
      {/* stage labels */}
      {stages.map(s => (
        <text key={s.key} x={cx} y={cy - s.ry - 4} fill="var(--fg-3)" fontSize="10"
          textAnchor="middle" fontFamily="var(--mono)" letterSpacing="0.1em">{s.label}</text>
      ))}
      {/* center text */}
      <text x={cx} y={cy + 8} fill="var(--amber)" fontSize="14"
        textAnchor="middle" fontFamily="var(--display)" fontWeight="700" letterSpacing="0.15em">FINISH</text>
      {/* horses */}
      {horses.map(h => {
        // path through 4 stages
        const pts = stages.map((s, i) => {
          const a = angle(ranked[i][h.n]);
          return { x: cx + s.rx * Math.cos(a), y: cy + s.ry * Math.sin(a) };
        });
        const pathD = "M " + pts.map(p => `${p.x},${p.y}`).join(" L ");
        const color = h.prob >= 0.4 ? "var(--amber)" : h.prob >= 0.25 ? "var(--cyan)" : "var(--fg-3)";
        const op = h.prob >= 0.4 ? 1 : h.prob >= 0.25 ? 0.6 : 0.25;
        const w_ = h.prob >= 0.4 ? 2 : 1;
        return (
          <g key={h.n} opacity={op}>
            <path d={pathD} fill="none" stroke={color} strokeWidth={w_}/>
            {pts.map((p, i) => (
              <circle key={i} cx={p.x} cy={p.y} r={i === 3 ? 4 : 2.5} fill={color}/>
            ))}
            {/* label at goal */}
            <text x={pts[3].x} y={pts[3].y - 7} fill={color} fontSize="10"
              fontFamily="var(--mono)" fontWeight="700" textAnchor="middle">{h.n}</text>
          </g>
        );
      })}
    </svg>
  );
}

// Big number EV gauge
function EVGauge({ value, threshold=1.0, w=200, h=200, label="EV" }) {
  const cx = w/2, cy = h/2 + 12;
  const r = 78;
  // arc from 135° to 405°
  const start = Math.PI * 0.75, end = Math.PI * 2.25;
  const valNorm = Math.min(1, Math.max(0, value/2));
  const valAngle = start + valNorm * (end - start);
  const thrAngle = start + Math.min(1, threshold/2) * (end - start);
  const arc = (a1, a2) => {
    const x1 = cx + r * Math.cos(a1), y1 = cy + r * Math.sin(a1);
    const x2 = cx + r * Math.cos(a2), y2 = cy + r * Math.sin(a2);
    const large = (a2 - a1) > Math.PI ? 1 : 0;
    return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
  };
  const good = value >= threshold;
  return (
    <svg width={w} height={h} style={{display:"block"}}>
      <path d={arc(start, end)} fill="none" stroke="var(--bg-3)" strokeWidth="6" strokeLinecap="butt"/>
      <path d={arc(start, valAngle)} fill="none" stroke={good ? "var(--green)" : "var(--amber)"} strokeWidth="6" strokeLinecap="butt"/>
      {/* threshold tick */}
      <line x1={cx + (r-10)*Math.cos(thrAngle)} y1={cy + (r-10)*Math.sin(thrAngle)}
            x2={cx + (r+10)*Math.cos(thrAngle)} y2={cy + (r+10)*Math.sin(thrAngle)}
            stroke="var(--amber)" strokeWidth="2"/>
      <text x={cx} y={cy + 4} textAnchor="middle" fontSize="36" fontFamily="var(--mono)" fontWeight="700"
        fill={good ? "var(--green)" : "var(--amber)"}>{value.toFixed(2)}</text>
      <text x={cx} y={cy - 24} textAnchor="middle" fontSize="11" fontFamily="var(--mono)"
        fill="var(--fg-3)" letterSpacing="0.15em">{label}</text>
      <text x={cx} y={cy + 28} textAnchor="middle" fontSize="9" fontFamily="var(--mono)"
        fill="var(--fg-3)">THR {threshold.toFixed(2)}</text>
    </svg>
  );
}

function RadarRaceDetail({ raceKey, evThreshold, onBack }) {
  const race = RAD_RACES.find(r => r.race_key === raceKey) || RAD_RACES[0];
  const horses = RAD_HORSES;
  const sortedByEv = [...horses].sort((a,b)=>b.ev_tan-a.ev_tan);
  const top = sortedByEv[0];
  const tansho = sortedByEv.filter(h=>h.ev_tan>evThreshold).slice(0,5).map(h=>h.n);
  const fukusho = sortedByEv.filter(h=>h.ev_fuku>evThreshold).map(h=>h.n);

  return (
    <div style={{display:"grid", gridTemplateRows:"auto minmax(0,1fr)", flex:1, minHeight:0}}>
      {/* hero header */}
      <div style={{padding:"14px 18px", background:"linear-gradient(180deg, oklch(0.18 0.01 240), var(--bg-1))", borderBottom:"1px solid var(--line)"}}>
        <div style={{display:"flex", alignItems:"center", gap:14}}>
          <button className="term-btn" onClick={onBack}>‹ DASH</button>
          <span className="dim" style={{fontFamily:"var(--mono)", fontSize:10}}>race_key</span>
          <span style={{color:"var(--amber)", fontFamily:"var(--mono)"}} className="bold">{race.race_key}</span>
          <span style={{marginLeft:"auto", display:"flex", gap:14, alignItems:"center"}}>
            <PacePill pace={race.pace}/>
            <span className="dim" style={{fontFamily:"var(--mono)", fontSize:10}}>POST</span>
            <span style={{fontFamily:"var(--mono)"}}>{race.post_time}</span>
          </span>
        </div>
        <div style={{marginTop:8, display:"flex", alignItems:"baseline", gap:14}}>
          <span style={{fontFamily:"var(--display)", fontSize:36, fontWeight:800, letterSpacing:"-0.01em"}}>{race.name}</span>
          <span className={"tag " + (race.grade==="G1"?"solid-amber":"amber")} style={{fontSize:11}}>{race.grade}</span>
          <span style={{color:"var(--fg-2)"}}>{race.venue} {race.race_no}R · {race.surface}{race.distance}m · {race.condition}馬場</span>
        </div>
      </div>

      <div className="term-grid" style={{gridTemplateColumns:"minmax(0,1.2fr) minmax(0,1fr)", gridTemplateRows:"minmax(0,1fr) auto"}}>
        {/* radar */}
        <div className="panel" style={{gridRow:"1 / span 2"}}>
          <div className="panel-head"><span className="title">TRACK RADAR</span><span className="meta">トラック俯瞰 · 全馬の予想軌跡</span></div>
          <div className="panel-body" style={{display:"flex", justifyContent:"center", alignItems:"center", padding:"20px"}}>
            <TrackRadar horses={horses} w={620} h={460}/>
          </div>
        </div>

        {/* hero card: BUY signal */}
        <div className="panel">
          <div className="panel-head"><span className="title">BUY SIGNAL</span><span className="meta">最高EV馬</span></div>
          <div className="panel-body" style={{display:"flex", gap:14, alignItems:"center"}}>
            <Umaban n={top.n} waku={top.w}/>
            <div style={{flex:1}}>
              <div style={{fontFamily:"var(--display)", fontSize:22, fontWeight:700}}>{top.name}</div>
              <div className="dim" style={{fontSize:11, fontFamily:"var(--mono)"}}>{top.jky} · {STYLE_LONG[top.rs]} · IDM {top.idm.toFixed(1)}</div>
              <div style={{display:"flex", gap:14, marginTop:6, fontFamily:"var(--mono)", fontSize:11}}>
                <span>P(複) <span className="amb bold">{(top.prob*100).toFixed(1)}%</span></span>
                <span>単勝 <span>{top.odds.toFixed(1)}</span></span>
                <span>複勝 <span>{top.fuku.toFixed(1)}</span></span>
              </div>
            </div>
            <EVGauge value={top.ev_tan} threshold={evThreshold} w={170} h={150} label="EV単"/>
          </div>
        </div>

        {/* Bets compact */}
        <div className="panel">
          <div className="panel-head"><span className="title">BUY LIST</span><span className="meta">ev_threshold {evThreshold.toFixed(2)}</span></div>
          <div className="panel-body">
            <div style={{display:"grid", gridTemplateColumns:"60px 1fr", gap:"8px 12px", alignItems:"center", fontFamily:"var(--mono)", fontSize:12}}>
              <span className="amb bold">単勝</span>
              <span>{tansho.length ? tansho.map(n => <span key={n} className="bold tnum" style={{display:"inline-block", padding:"2px 8px", border:"1px solid var(--amber-dim)", color:"var(--amber)", marginRight:4}}>{n}</span>) : <span className="dim">該当なし</span>}</span>
              <span className="amb bold">複勝</span>
              <span>{fukusho.length ? fukusho.map(n => <span key={n} className="bold tnum" style={{display:"inline-block", padding:"2px 8px", border:"1px solid var(--green-dim)", color:"var(--green)", marginRight:4}}>{n}</span>) : <span className="dim">該当なし</span>}</span>
              <span className="amb bold">3連複軸</span>
              <span>軸 <span className="bold tnum" style={{padding:"2px 8px", background:"var(--amber)", color:"oklch(0.15 0 0)"}}>{top.n}</span> 流し → {sortedByEv.slice(1,6).map(h=>h.n).join(", ")}</span>
            </div>
            <table className="dt" style={{marginTop:12}}>
              <thead><tr><th>馬</th><th className="l">馬名</th><th>P(複)</th><th>EV単</th><th>EV複</th></tr></thead>
              <tbody>
                {sortedByEv.slice(0,8).map(h => (
                  <tr key={h.n}>
                    <td><Umaban n={h.n} waku={h.w} sm/></td>
                    <td className="l">{h.name}</td>
                    <td className="tnum amb">{(h.prob*100).toFixed(1)}</td>
                    <td className={"tnum bold " + (h.ev_tan >= evThreshold ? "pos" : h.ev_tan >= 0.8 ? "amb" : "dim")}>{h.ev_tan.toFixed(2)}</td>
                    <td className={"tnum " + (h.ev_fuku >= evThreshold ? "pos bold" : "dim")}>{h.ev_fuku.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

window.RaceTerminalRadarApp = function RaceTerminalRadarApp() {
  const [tab, setTab] = useState("race");
  const [raceKey, setRaceKey] = useState(RAD_RACES[0].race_key);
  const [evThreshold, setEvThreshold] = useState(1.0);
  const [clock, setClock] = useState(new Date().toLocaleTimeString("ja-JP", { hour12: false }));
  useEffect(() => {
    const t = setInterval(() => setClock(new Date().toLocaleTimeString("ja-JP", { hour12: false })), 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="terminal-frame" data-screen-label={"radar-"+tab}>
      <TopBar tab={tab} onTab={setTab} clock={clock}/>
      <div style={{flex:1, display:"flex", flexDirection:"column", minHeight:0}}>
        {tab === "dash" && <DashboardScreen onOpenRace={(k)=>{setRaceKey(k); setTab("race");}} evThreshold={evThreshold}/>}
        {tab === "race" && <RadarRaceDetail raceKey={raceKey} evThreshold={evThreshold} onBack={()=>setTab("dash")}/>}
        {tab === "back" && <BacktestScreen evThreshold={evThreshold}/>}
        {(tab === "data" || tab === "model") && <PlaceholderScreen label={tab.toUpperCase()}/>}
      </div>
      <StatusBar tab={tab} evThreshold={evThreshold}/>
    </div>
  );
};
