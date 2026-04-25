// Variation B: NEO TRADING — denser, ribbon-driven, big number tape
// Reuses BOONTA_DATA + components.jsx primitives, but layouts are remixed.

const { TODAY: NEO_TODAY, RACES: NEO_RACES, HORSES_TENNOH: NEO_HORSES, STRATEGIES: NEO_STRATS } = window.BOONTA_DATA;

function NeoTicker() {
  // scrolling tape of EV/ROI signals
  const items = [
    ...NEO_RACES.map(r => `${r.venue}${r.race_no}R · ${r.name} · EV単 ${r.best_ev_tan.toFixed(2)} · P(複) ${(r.ml_top.prob*100).toFixed(1)}%`),
    ...NEO_STRATS.map(s => `${s.label.toUpperCase()} · ROI ${s.roi.toFixed(1)}% · HITS ${s.hits.toLocaleString()}`),
  ];
  const txt = items.join("   ◆   ");
  return (
    <div style={{height:24, background:"oklch(0.1 0.005 240)", borderBottom:"1px solid var(--line)", display:"flex", alignItems:"center", overflow:"hidden", fontFamily:"var(--mono)", fontSize:11, color:"var(--fg-1)"}}>
      <span style={{padding:"0 12px", background:"var(--cyan)", color:"oklch(0.1 0 0)", height:"100%", display:"flex", alignItems:"center", letterSpacing:"0.12em", fontWeight:700}}>TAPE</span>
      <div style={{flex:1, overflow:"hidden", whiteSpace:"nowrap", maskImage:"linear-gradient(90deg, transparent, #000 4%, #000 96%, transparent)"}}>
        <div style={{display:"inline-block", paddingLeft:"100%", animation:"neo-marquee 80s linear infinite"}}>
          {txt}   ◆   {txt}
        </div>
      </div>
      <style>{`@keyframes neo-marquee { from { transform: translateX(0); } to { transform: translateX(-100%); } }`}</style>
    </div>
  );
}

function NeoBigStat({ k, v, sub, cls="" }) {
  return (
    <div style={{padding:"10px 14px", borderRight:"1px solid var(--line)", flex:1, minWidth:0}}>
      <div style={{fontSize:10, color:"var(--fg-3)", textTransform:"uppercase", letterSpacing:"0.1em"}}>{k}</div>
      <div className={"tnum bold " + cls} style={{fontFamily:"var(--mono)", fontSize:24, lineHeight:"1.1", marginTop:2}}>{v}</div>
      {sub && <div style={{fontSize:10, color:"var(--fg-3)", marginTop:2}}>{sub}</div>}
    </div>
  );
}

function NeoDashboard({ onOpenRace, evThreshold }) {
  const buy = NEO_RACES.filter(r => r.best_ev_tan >= evThreshold).length;
  const watch = NEO_RACES.filter(r => r.best_ev_tan >= 0.9 && r.best_ev_tan < evThreshold).length;
  const skip = NEO_RACES.length - buy - watch;
  const totalProb = NEO_RACES.reduce((s,r)=>s+r.ml_top.prob,0)/NEO_RACES.length;

  return (
    <div style={{display:"flex", flexDirection:"column", flex:1, minHeight:0}}>
      <NeoTicker/>
      {/* big stat strip */}
      <div style={{display:"flex", borderBottom:"1px solid var(--line)", background:"var(--bg-1)"}}>
        <NeoBigStat k="DATE" v="2026-04-25" sub="JST"/>
        <NeoBigStat k="RACES" v={NEO_RACES.length} sub="3 tracks"/>
        <NeoBigStat k="BUY" v={buy} sub={`EV ≥ ${evThreshold.toFixed(2)}`} cls="pos"/>
        <NeoBigStat k="WATCH" v={watch} sub="EV ≥ 0.90" cls="amb"/>
        <NeoBigStat k="SKIP" v={skip} sub="EV < 0.90" cls="dim"/>
        <NeoBigStat k="ML AVG P" v={(totalProb*100).toFixed(1)+"%"} sub="本命平均"/>
        <NeoBigStat k="EV-THR" v={evThreshold.toFixed(2)} sub="break-even=1.00" cls="amb"/>
      </div>

      <div className="term-grid" style={{gridTemplateColumns:"minmax(0,1fr) minmax(0,1fr) minmax(0,1fr)", gridTemplateRows:"minmax(0,1fr) minmax(0,1fr)"}}>
        {NEO_RACES.map(r => {
          const buy = r.best_ev_tan >= evThreshold;
          return (
            <div key={r.race_key} className="panel" style={{cursor:"pointer"}} onClick={()=>onOpenRace(r.race_key)}>
              <div className="panel-head">
                <span><span className="bold" style={{color:"var(--amber)"}}>{r.venue}</span> <span>{r.race_no}R</span> <span className="dim">/ {r.name}</span></span>
                <span style={{display:"flex", gap:6}}>
                  <span className={"tag " + (r.grade==="G1"?"solid-amber":"amber")}>{r.grade}</span>
                  {buy && <span className="tag solid-amber">BUY</span>}
                </span>
              </div>
              <div className="panel-body">
                <div style={{display:"flex", justifyContent:"space-between", marginBottom:8}}>
                  <span className="dim" style={{fontSize:10}}>{r.surface}{r.distance}m · {r.condition}/{r.weather} · {r.head_count}頭</span>
                  <span className="dim tnum">{r.post_time}</span>
                </div>
                <div style={{display:"flex", gap:10, alignItems:"center", marginBottom:10}}>
                  <Umaban n={r.ml_top.umaban} waku={Math.ceil(r.ml_top.umaban/2)}/>
                  <div style={{flex:1}}>
                    <div className="bold">{r.ml_top.name}</div>
                    <div className="dim" style={{fontSize:10}}>本命 / ML予測</div>
                  </div>
                  <div style={{textAlign:"right"}}>
                    <div className="amb bold tnum" style={{fontSize:18, fontFamily:"var(--mono)"}}>{(r.ml_top.prob*100).toFixed(1)}%</div>
                    <div className="dim" style={{fontSize:10}}>P(複)</div>
                  </div>
                </div>
                {/* EV bars */}
                <div style={{display:"grid", gridTemplateColumns:"40px 1fr 50px", gap:6, alignItems:"center", fontSize:11, marginBottom:4}}>
                  <span className="dim">EV単</span>
                  <Bar value={r.best_ev_tan} max={2} color={buy ? "green" : "amber"} w="100%"/>
                  <span className={"tnum bold " + (buy ? "pos" : "amb")} style={{textAlign:"right"}}>{r.best_ev_tan.toFixed(2)}</span>
                </div>
                <div style={{display:"grid", gridTemplateColumns:"40px 1fr 50px", gap:6, alignItems:"center", fontSize:11}}>
                  <span className="dim">EV複</span>
                  <Bar value={r.best_ev_fuku} max={2} color={r.best_ev_fuku >= evThreshold ? "green" : "amber"} w="100%"/>
                  <span className={"tnum " + (r.best_ev_fuku >= evThreshold ? "pos bold" : "dim")} style={{textAlign:"right"}}>{r.best_ev_fuku.toFixed(2)}</span>
                </div>
                <div style={{marginTop:10, paddingTop:8, borderTop:"1px dashed var(--bg-3)", display:"flex", justifyContent:"space-between"}}>
                  <PacePill pace={r.pace}/>
                  <span className="dim" style={{fontSize:10}}>{r.race_key}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

window.NeoDashboard = NeoDashboard;
window.NeoTicker = NeoTicker;

// Variation B App
window.RaceTerminalNeoApp = function RaceTerminalNeoApp() {
  const [tab, setTab] = useState("dash");
  const [raceKey, setRaceKey] = useState(NEO_RACES[0].race_key);
  const [evThreshold, setEvThreshold] = useState(1.0);
  const [clock, setClock] = useState(new Date().toLocaleTimeString("ja-JP", { hour12: false }));
  useEffect(() => {
    const t = setInterval(() => setClock(new Date().toLocaleTimeString("ja-JP", { hour12: false })), 1000);
    return () => clearInterval(t);
  }, []);
  const openRace = (k) => { setRaceKey(k); setTab("race"); };
  return (
    <div className="terminal-frame" data-screen-label={"neo-"+tab}>
      <TopBar tab={tab} onTab={setTab} clock={clock}/>
      <div style={{flex:1, display:"flex", flexDirection:"column", minHeight:0}}>
        {tab === "dash" && <NeoDashboard onOpenRace={openRace} evThreshold={evThreshold}/>}
        {tab === "race" && <RaceDetailScreen raceKey={raceKey} evThreshold={evThreshold} onBack={()=>setTab("dash")}/>}
        {tab === "back" && <BacktestScreen evThreshold={evThreshold}/>}
        {(tab === "data" || tab === "model") && <PlaceholderScreen label={tab.toUpperCase()}/>}
      </div>
      <StatusBar tab={tab} evThreshold={evThreshold}/>
    </div>
  );
};
