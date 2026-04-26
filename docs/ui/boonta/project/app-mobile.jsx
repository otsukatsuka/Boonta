// Mobile (iPhone) version of RACE TERMINAL — same data, vertical-stack layout.
const { useState, useEffect, useMemo, useRef } = React;
const { RACES: M_RACES, HORSES_TENNOH: M_HORSES, STRATEGIES: M_STRATS } = window.BOONTA_DATA;
const { Umaban, Bar, PacePill, Sparkline, CornerPositions, STYLE_LONG, STYLE_LABEL, IO_LABEL } = window;

const mobileStyles = {
  frame: { background: "var(--bg-0)", color: "var(--fg-0)", fontFamily: "var(--mono)", fontSize: 12, height: "100%", display: "flex", flexDirection: "column", overflow: "hidden", paddingTop: 50, paddingBottom: 34 },
  topbar: { display:"flex", alignItems:"center", height:36, background:"var(--bg-1)", borderBottom:"1px solid var(--line)", flexShrink:0 },
  brand: { padding:"0 12px", height:"100%", display:"flex", alignItems:"center", background:"var(--amber)", color:"#000", fontFamily:"var(--display)", fontWeight:700, letterSpacing:"0.16em", fontSize:11 },
  scroll: { flex:1, minHeight:0, overflowY:"auto", overflowX:"hidden" },
  tabbar: { display:"flex", height:48, borderTop:"1px solid var(--line)", background:"var(--bg-1)", flexShrink:0 },
  tab: (active) => ({ flex:1, display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", gap:2, color: active ? "var(--amber)" : "var(--fg-3)", fontSize:9, letterSpacing:"0.08em", textTransform:"uppercase", borderTop: active ? "2px solid var(--amber)" : "2px solid transparent", cursor:"pointer", userSelect:"none" }),
};

function MTopbar({ title, sub, onBack }) {
  return (
    <div style={mobileStyles.topbar}>
      {onBack ? (
        <div onClick={onBack} style={{padding:"0 12px", height:"100%", display:"flex", alignItems:"center", color:"var(--amber)", cursor:"pointer", fontSize:14}}>‹</div>
      ) : (
        <div style={mobileStyles.brand}>BOONTA</div>
      )}
      <div style={{padding:"0 10px", flex:1, minWidth:0}}>
        <div style={{fontSize:11, fontWeight:600, whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis"}}>{title}</div>
        {sub && <div style={{fontSize:9, color:"var(--fg-3)", whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis"}}>{sub}</div>}
      </div>
      <div style={{padding:"0 10px", display:"flex", gap:6, alignItems:"center", color:"var(--fg-3)", fontSize:9}}>
        <span className="live-dot" style={{display:"inline-block", width:6, height:6, borderRadius:"50%", background:"var(--green)", boxShadow:"0 0 6px var(--green)"}}/>
        <span>LIVE</span>
      </div>
    </div>
  );
}

function MTabbar({ tab, onTab }) {
  const tabs = [
    { id:"dash", label:"DASH", icon:"▦" },
    { id:"race", label:"RACE", icon:"⏵" },
    { id:"back", label:"BTEST", icon:"≡" },
    { id:"more", label:"MORE", icon:"…" },
  ];
  return (
    <div style={mobileStyles.tabbar}>
      {tabs.map(t => (
        <div key={t.id} onClick={()=>onTab(t.id)} style={mobileStyles.tab(tab===t.id)}>
          <span style={{fontSize:16, fontFamily:"var(--mono)"}}>{t.icon}</span>
          <span>{t.label}</span>
        </div>
      ))}
    </div>
  );
}

function MDash({ onOpen, evThr }) {
  return (
    <div style={{padding:"10px"}}>
      {/* command line strip */}
      <div style={{padding:"8px 10px", background:"var(--bg-1)", border:"1px solid var(--line)", marginBottom:10, fontSize:11}}>
        <div style={{display:"flex", justifyContent:"space-between", color:"var(--fg-3)"}}>
          <span style={{color:"var(--amber)"}}>$ predict --date</span>
          <span style={{color:"var(--fg-1)"}}>2026-04-25</span>
        </div>
        <div style={{display:"flex", justifyContent:"space-between", marginTop:2, color:"var(--fg-3)"}}>
          <span>--ev-threshold</span>
          <span className="amb tnum bold">{evThr.toFixed(2)}</span>
        </div>
      </div>

      {/* mini stats */}
      <div style={{display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:6, marginBottom:10}}>
        {[
          ["RACES", M_RACES.length, ""],
          ["BUY", M_RACES.filter(r=>r.best_ev_tan>=evThr).length, "pos"],
          ["WATCH", M_RACES.filter(r=>r.best_ev_tan>=0.9 && r.best_ev_tan<evThr).length, "amb"],
        ].map(([k,v,c]) => (
          <div key={k} style={{padding:"8px 10px", background:"var(--bg-1)", border:"1px solid var(--line)"}}>
            <div style={{fontSize:9, color:"var(--fg-3)", letterSpacing:"0.1em"}}>{k}</div>
            <div className={"tnum bold "+c} style={{fontSize:20, lineHeight:1.1}}>{v}</div>
          </div>
        ))}
      </div>

      {/* race cards */}
      {M_RACES.map(r => {
        const buy = r.best_ev_tan >= evThr;
        const watch = !buy && r.best_ev_tan >= 0.9;
        return (
          <div key={r.race_key} onClick={()=>onOpen(r.race_key)}
            style={{background:"var(--bg-1)", border:"1px solid var(--line)", marginBottom:8, padding:"10px 12px", cursor:"pointer"}}>
            <div style={{display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:4}}>
              <span>
                <span className="bold" style={{color:"var(--amber)"}}>{r.venue}</span>
                <span> {r.race_no}R</span>
                <span className={"tag " + (r.grade==="G1"?"solid-amber":"amber")} style={{marginLeft:6, fontSize:8}}>{r.grade}</span>
              </span>
              {buy ? <span className="tag solid-amber" style={{fontSize:8}}>BUY</span>
                : watch ? <span className="tag amber" style={{fontSize:8}}>WATCH</span>
                : <span className="tag" style={{fontSize:8}}>SKIP</span>}
            </div>
            <div style={{fontSize:13, fontWeight:600, marginBottom:2}}>{r.name}</div>
            <div style={{fontSize:10, color:"var(--fg-3)", marginBottom:8}}>
              {r.surface}{r.distance}m · {r.condition}/{r.weather} · {r.head_count}頭 · {r.post_time}発走
            </div>
            <div style={{display:"flex", alignItems:"center", gap:8, marginBottom:8}}>
              <Umaban n={r.ml_top.umaban} waku={Math.ceil(r.ml_top.umaban/2)} sm/>
              <span style={{flex:1, fontSize:11, fontWeight:600}}>{r.ml_top.name}</span>
              <span className="amb bold tnum" style={{fontSize:14}}>{(r.ml_top.prob*100).toFixed(1)}%</span>
            </div>
            <div style={{display:"grid", gridTemplateColumns:"36px 1fr 42px", gap:6, alignItems:"center", fontSize:10, marginBottom:3}}>
              <span className="dim">EV単</span>
              <Bar value={r.best_ev_tan} max={2} color={buy?"green":"amber"} w="100%"/>
              <span className={"tnum bold "+(buy?"pos":"amb")} style={{textAlign:"right"}}>{r.best_ev_tan.toFixed(2)}</span>
            </div>
            <div style={{display:"grid", gridTemplateColumns:"36px 1fr 42px", gap:6, alignItems:"center", fontSize:10}}>
              <span className="dim">EV複</span>
              <Bar value={r.best_ev_fuku} max={2} color={r.best_ev_fuku>=evThr?"green":"amber"} w="100%"/>
              <span className={"tnum "+(r.best_ev_fuku>=evThr?"pos bold":"dim")} style={{textAlign:"right"}}>{r.best_ev_fuku.toFixed(2)}</span>
            </div>
            <div style={{display:"flex", justifyContent:"space-between", marginTop:8, paddingTop:6, borderTop:"1px dashed var(--bg-3)"}}>
              <span className={"pace-pill "+r.pace} style={{fontSize:9}}>{r.pace}</span>
              <span className="dim" style={{fontSize:9}}>{r.race_key}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function MRace({ raceKey, evThr, onBack }) {
  const race = M_RACES.find(r=>r.race_key===raceKey) || M_RACES[0];
  const horses = M_HORSES;
  const sortedByEv = [...horses].sort((a,b)=>b.ev_tan-a.ev_tan);
  const top = sortedByEv[0];
  const tansho = sortedByEv.filter(h=>h.ev_tan>evThr).slice(0,5).map(h=>h.n);
  const fukusho = sortedByEv.filter(h=>h.ev_fuku>evThr).map(h=>h.n);
  const top3 = sortedByEv.slice(0,3).map(h=>h.n).sort((a,b)=>a-b);
  const umaren = []; for (let i=0;i<top3.length;i++) for (let j=i+1;j<top3.length;j++) umaren.push([top3[i],top3[j]]);
  const top4 = sortedByEv.slice(0,4).map(h=>h.n).sort((a,b)=>a-b);
  const sanren = []; for (let i=0;i<top4.length;i++) for (let j=i+1;j<top4.length;j++) for (let k=j+1;k<top4.length;k++) sanren.push([top4[i],top4[j],top4[k]]);
  const [section, setSection] = useState("ev");

  return (
    <div style={{padding:"10px 0"}}>
      {/* race header card */}
      <div style={{padding:"10px 12px", background:"var(--bg-1)", borderTop:"1px solid var(--line)", borderBottom:"1px solid var(--line)", marginBottom:10}}>
        <div style={{display:"flex", justifyContent:"space-between", alignItems:"center", fontSize:9, color:"var(--fg-3)", marginBottom:4}}>
          <span>race_key <span style={{color:"var(--amber)"}} className="bold">{race.race_key}</span></span>
          <PacePill pace={race.pace}/>
        </div>
        <div style={{fontFamily:"var(--display)", fontSize:20, fontWeight:800, letterSpacing:"-0.01em"}}>{race.name}</div>
        <div style={{display:"flex", justifyContent:"space-between", marginTop:4, fontSize:10}}>
          <span><span className={"tag "+(race.grade==="G1"?"solid-amber":"amber")} style={{fontSize:9}}>{race.grade}</span> <span className="dim">{race.venue} {race.race_no}R · {race.surface}{race.distance}m</span></span>
          <span className="dim">発走 <span style={{color:"var(--fg-1)"}} className="bold">{race.post_time}</span></span>
        </div>
      </div>

      {/* hero buy signal */}
      <div style={{margin:"0 10px 10px", padding:"12px", background:"var(--bg-1)", border:"1px solid var(--line)"}}>
        <div style={{fontSize:9, color:"var(--fg-3)", letterSpacing:"0.1em", marginBottom:6}}>BUY SIGNAL · 最高EV馬</div>
        <div style={{display:"flex", alignItems:"center", gap:10}}>
          <Umaban n={top.n} waku={top.w}/>
          <div style={{flex:1, minWidth:0}}>
            <div style={{fontSize:14, fontWeight:700, fontFamily:"var(--display)"}}>{top.name}</div>
            <div className="dim" style={{fontSize:10}}>{top.jky} · {STYLE_LONG[top.rs]}</div>
          </div>
          <div style={{textAlign:"right"}}>
            <div className={"tnum bold "+(top.ev_tan>=evThr?"pos":"amb")} style={{fontSize:24, lineHeight:1}}>{top.ev_tan.toFixed(2)}</div>
            <div className="dim" style={{fontSize:9}}>EV単</div>
          </div>
        </div>
        <div style={{display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:6, marginTop:10, paddingTop:8, borderTop:"1px dashed var(--bg-3)", fontSize:10}}>
          <div><div className="dim" style={{fontSize:9}}>P(複)</div><div className="amb bold tnum">{(top.prob*100).toFixed(1)}%</div></div>
          <div><div className="dim" style={{fontSize:9}}>単勝</div><div className="bold tnum">{top.odds.toFixed(1)}</div></div>
          <div><div className="dim" style={{fontSize:9}}>複勝</div><div className="bold tnum">{top.fuku.toFixed(1)}</div></div>
        </div>
      </div>

      {/* section picker */}
      <div style={{display:"flex", margin:"0 10px 10px", border:"1px solid var(--line)", background:"var(--bg-1)"}}>
        {[["ev","EV"],["pos","位置取り"],["bet","買い目"]].map(([id,label]) => (
          <div key={id} onClick={()=>setSection(id)} style={{flex:1, padding:"8px 0", textAlign:"center", fontSize:10, letterSpacing:"0.06em", color: section===id?"#000":"var(--fg-2)", background: section===id?"var(--amber)":"transparent", cursor:"pointer"}}>{label}</div>
        ))}
      </div>

      {section === "ev" && (
        <div style={{margin:"0 10px"}}>
          <div className="dim" style={{fontSize:10, marginBottom:6, letterSpacing:"0.08em"}}>RANKED BY EV単 · {horses.length}頭</div>
          {sortedByEv.map(h => (
            <div key={h.n} style={{display:"grid", gridTemplateColumns:"22px 1fr auto", gap:8, alignItems:"center", padding:"8px 0", borderBottom:"1px solid var(--bg-2)"}}>
              <Umaban n={h.n} waku={h.w} sm/>
              <div style={{minWidth:0}}>
                <div style={{fontSize:12, fontWeight:600, whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis"}}>{h.name}</div>
                <div className="dim" style={{fontSize:9}}>{h.jky} · {STYLE_LABEL[h.rs]} · IDM {h.idm.toFixed(1)} · 単{h.odds.toFixed(1)}</div>
              </div>
              <div style={{textAlign:"right", fontFamily:"var(--mono)"}}>
                <div className={"tnum bold "+(h.ev_tan>=evThr?"pos":h.ev_tan>=0.8?"amb":"dim")} style={{fontSize:13}}>{h.ev_tan.toFixed(2)}{h.ev_tan>=evThr?" ★":""}</div>
                <div className="amb tnum" style={{fontSize:10}}>{(h.prob*100).toFixed(1)}%</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {section === "pos" && (
        <div style={{margin:"0 10px"}}>
          <div className="dim" style={{fontSize:10, marginBottom:6, letterSpacing:"0.08em"}}>位置取り推移 · スタート → 道中 → 後3F → ゴール</div>
          <div style={{background:"var(--bg-1)", border:"1px solid var(--line)", padding:"6px"}}>
            <CornerPositions horses={horses} w={340} h={300}/>
          </div>
          <div style={{marginTop:10}}>
            {horses.filter(h=>h.prob>=0.25).map(h => (
              <div key={h.n} style={{display:"flex", gap:8, alignItems:"center", padding:"6px 0", borderBottom:"1px solid var(--bg-2)", fontSize:11}}>
                <Umaban n={h.n} waku={h.w} sm/>
                <span style={{flex:1}}>{h.name}</span>
                <span className="dim">道中 <span style={{color:"var(--fg-1)"}} className="tnum bold">{h.midp}</span></span>
                <span className="dim">ゴ <span className={(h.goalp<=3?"amb bold":"")+" tnum"}>{h.goalp}</span></span>
                <span className="dim">{IO_LABEL[h.io]}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {section === "bet" && (
        <div style={{margin:"0 10px"}}>
          <div className="dim" style={{fontSize:10, marginBottom:8, letterSpacing:"0.08em"}}>BET LIST · ev_threshold {evThr.toFixed(2)}</div>
          {[
            ["単勝", tansho.map(n=>String(n)), "var(--amber)"],
            ["複勝", fukusho.map(n=>String(n)), "var(--green)"],
            ["馬連 BOX", umaren.map(c=>c.join("-")), "var(--cyan)"],
            ["3連複 BOX", sanren.map(c=>c.join("-")), "var(--cyan)"],
          ].map(([label, items, color]) => (
            <div key={label} style={{padding:"10px 12px", background:"var(--bg-1)", border:"1px solid var(--line)", marginBottom:8}}>
              <div style={{display:"flex", justifyContent:"space-between", marginBottom:6}}>
                <span className="amb bold" style={{fontSize:11}}>{label}</span>
                <span className="dim tnum" style={{fontSize:9}}>{items.length}点</span>
              </div>
              <div>
                {items.length ? items.map((s,i) => (
                  <span key={i} className="bold tnum" style={{display:"inline-block", padding:"3px 8px", border:`1px solid ${color}`, color, marginRight:4, marginBottom:4, fontSize:11}}>{s}</span>
                )) : <span className="dim" style={{fontSize:11}}>該当なし</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MBack({ evThr }) {
  const [sid, setSid] = useState("ev_tansho");
  const sel = M_STRATS.find(s=>s.id===sid);
  return (
    <div style={{padding:"10px"}}>
      <div className="dim" style={{fontSize:10, letterSpacing:"0.08em", marginBottom:6}}>2025-01 → 2025-12 · 3,453 races · ev_threshold {evThr.toFixed(2)}</div>

      {/* strategy list */}
      {M_STRATS.map(s => {
        const pnl = s.returned - s.invested;
        const active = s.id === sid;
        return (
          <div key={s.id} onClick={()=>setSid(s.id)}
            style={{padding:"10px 12px", background: active ? "oklch(0.22 0.02 75 / 0.3)" : "var(--bg-1)", border: active ? "1px solid var(--amber)" : "1px solid var(--line)", marginBottom:6, cursor:"pointer"}}>
            <div style={{display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:4}}>
              <span>
                <span className="bold" style={{fontSize:12}}>{s.label}</span>
                <span className={"tag "+(s.kind==="EV"?"amber":"cyan")} style={{marginLeft:6, fontSize:8}}>{s.kind}</span>
              </span>
              <span className={"tnum bold "+(s.roi>=100?"pos":s.roi>=90?"amb":s.roi>=70?"":"neg")} style={{fontSize:16}}>{s.roi.toFixed(1)}%</span>
            </div>
            <div style={{display:"flex", alignItems:"center", gap:8}}>
              <Sparkline data={s.equity.map(p=>p.cum)} w={140} h={20} color={pnl>=0?"var(--green)":"var(--red)"}/>
              <span className={"tnum "+(pnl>=0?"pos":"neg")} style={{fontSize:10}}>{pnl>=0?"+":""}{Math.round(pnl/1000)}k</span>
              <span className="dim tnum" style={{marginLeft:"auto", fontSize:9}}>{s.hits} hits</span>
            </div>
          </div>
        );
      })}

      {/* selected detail */}
      <div style={{padding:"12px", background:"var(--bg-1)", border:"1px solid var(--line)", marginTop:10}}>
        <div className="dim" style={{fontSize:9, letterSpacing:"0.1em", marginBottom:8}}>SELECTED · {sel.label}</div>
        <div style={{textAlign:"center", paddingBottom:8, borderBottom:"1px dashed var(--bg-3)"}}>
          <div className={"tnum bold "+(sel.roi>=100?"pos":sel.roi>=90?"amb":"")} style={{fontSize:36, lineHeight:1, fontFamily:"var(--mono)"}}>{sel.roi.toFixed(1)}<span style={{fontSize:18}}>%</span></div>
          <div className="dim" style={{fontSize:10, letterSpacing:"0.1em", marginTop:2}}>ROI</div>
        </div>
        <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:"10px 12px", marginTop:10, fontSize:11}}>
          <div><div className="dim" style={{fontSize:9}}>投資額</div><div className="bold tnum">¥{sel.invested.toLocaleString()}</div></div>
          <div><div className="dim" style={{fontSize:9}}>回収額</div><div className="bold tnum">¥{sel.returned.toLocaleString()}</div></div>
          <div><div className="dim" style={{fontSize:9}}>購入レース</div><div className="bold tnum">{sel.bet_races.toLocaleString()}</div></div>
          <div><div className="dim" style={{fontSize:9}}>的中数</div><div className="bold tnum">{sel.hits.toLocaleString()}</div></div>
        </div>
      </div>
    </div>
  );
}

function MMore({ evThr, setEvThr }) {
  return (
    <div style={{padding:"14px"}}>
      <div className="dim" style={{fontSize:10, letterSpacing:"0.1em", marginBottom:10}}>SETTINGS</div>
      <div style={{padding:"14px", background:"var(--bg-1)", border:"1px solid var(--line)", marginBottom:10}}>
        <div style={{display:"flex", justifyContent:"space-between", marginBottom:8}}>
          <span style={{fontSize:11, fontWeight:600}}>EV THRESHOLD</span>
          <span className="amb bold tnum" style={{fontSize:14}}>{evThr.toFixed(2)}</span>
        </div>
        <input type="range" min={0.8} max={1.5} step={0.05} value={evThr}
          onChange={e=>setEvThr(parseFloat(e.target.value))}
          style={{width:"100%", accentColor:"var(--amber)"}}/>
        <div style={{display:"flex", justifyContent:"space-between", fontSize:9, color:"var(--fg-3)", marginTop:4}}>
          <span>0.80</span><span>1.00 (BE)</span><span>1.50</span>
        </div>
        <div className="dim" style={{fontSize:10, marginTop:8, lineHeight:1.5}}>
          1.00 = ブレイクイーブン. ↑で厳しめにピック (買うレースが減る)
        </div>
      </div>

      <div className="dim" style={{fontSize:10, letterSpacing:"0.1em", marginBottom:10, marginTop:18}}>SYSTEM</div>
      <div style={{background:"var(--bg-1)", border:"1px solid var(--line)", fontSize:11}}>
        {[
          ["Model", "jrdb_predictor", "ok"],
          ["Modal", "boonta-ml · READY", "ok"],
          ["JRDB", "SYNC 2026-04-25 06:00", "ok"],
          ["Preset", "best_quality", ""],
          ["Features", "35 (KYI)", ""],
          ["Version", "v2.04.25", ""],
        ].map(([k,v,c]) => (
          <div key={k} style={{display:"flex", justifyContent:"space-between", padding:"10px 12px", borderBottom:"1px solid var(--bg-2)"}}>
            <span className="dim">{k}</span>
            <span className={c==="ok"?"pos":""} style={{fontFamily:"var(--mono)"}}>{v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

window.RaceTerminalMobileApp = function RaceTerminalMobileApp({ initialTab = "dash" } = {}) {
  const [tab, setTab] = useState(initialTab);
  const [raceKey, setRaceKey] = useState(M_RACES[0].race_key);
  const [evThr, setEvThr] = useState(1.0);

  const titles = {
    dash: { t: "本日のレース", s: "2026-04-25 · 6 races" },
    race: { t: M_RACES.find(r=>r.race_key===raceKey)?.name || "Race", s: M_RACES.find(r=>r.race_key===raceKey)?.race_key || "" },
    back: { t: "Backtest", s: "戦略マトリクス · 2025" },
    more: { t: "Settings", s: "EV閾値 / システム情報" },
  };

  return (
    <div style={mobileStyles.frame} data-screen-label={"mobile-"+tab}>
      <MTopbar title={titles[tab].t} sub={titles[tab].s} onBack={tab==="race" ? () => setTab("dash") : null}/>
      <div style={mobileStyles.scroll}>
        {tab === "dash" && <MDash onOpen={(k)=>{setRaceKey(k); setTab("race");}} evThr={evThr}/>}
        {tab === "race" && <MRace raceKey={raceKey} evThr={evThr} onBack={()=>setTab("dash")}/>}
        {tab === "back" && <MBack evThr={evThr}/>}
        {tab === "more" && <MMore evThr={evThr} setEvThr={setEvThr}/>}
      </div>
      <MTabbar tab={tab} onTab={setTab}/>
    </div>
  );
};
