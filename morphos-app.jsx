import { useState, useEffect, useCallback, useRef } from "react";
import * as d3 from "d3";

const API = "http://localhost:8000";
const api = async (path, opts={}) => {
  try {
    const r = await fetch(`${API}${path}`, { headers:{"Content-Type":"application/json"}, ...opts });
    return r.json();
  } catch(e) { return {error: e.message}; }
};
const get  = p    => api(p);
const post = (p,b)=> api(p, {method:"POST", body:JSON.stringify(b)});

// ── Tokens ──────────────────────────────────────────────────────────
const C = {
  bg0:"#070a0f", bg1:"#0c1119", bg2:"#111827", bg3:"#1a2438",
  border:"#1e2d44", border2:"#253552",
  text:"#dde4f0", muted:"#5e7a96", dim:"#2a3d55",
  blue:"#3b82f6", blueDim:"#1a3470",
  amber:"#f5a623", amberDim:"#6b3c0a",
  teal:"#2ccfb8", tealDim:"#0c3832",
  green:"#40d97a", greenDim:"#0d4124",
  red:"#f06060", redDim:"#5c1a1a",
  purple:"#b18bfa", purpleDim:"#311e6e",
};
const mono = `'JetBrains Mono','Fira Code','Cascadia Code',monospace`;
const sans = `'IBM Plex Sans','Sora','Segoe UI',system-ui,sans-serif`;

// ── Shared styles ────────────────────────────────────────────────────
const inputSt = { background:C.bg2, border:`1px solid ${C.border2}`, color:C.text,
  padding:"7px 10px", borderRadius:5, fontSize:11, fontFamily:sans, outline:"none" };
const btnSt = (c=C.blue,d=C.blueDim) => ({
  background:d, border:`1px solid ${c}`, color:C.text,
  padding:"7px 18px", borderRadius:5, cursor:"pointer",
  fontSize:11, fontFamily:sans, fontWeight:700 });
const cardSt = (x={}) => ({ background:C.bg1, border:`1px solid ${C.border}`, borderRadius:8, padding:14, ...x });
const hdSt   = (x={}) => ({ fontSize:9, color:C.muted, letterSpacing:2, textTransform:"uppercase", marginBottom:8, ...x });

// ── TruthBadge ───────────────────────────────────────────────────────
function TruthBadge({degree, modality}) {
  if (degree == null) return null;
  const d = parseFloat(degree);
  const c  = d > 0.8 ? C.green  : d > 0.5 ? C.amber  : C.red;
  const bg = d > 0.8 ? C.greenDim : d > 0.5 ? C.amberDim : C.redDim;
  const m  = (modality || "ACTUAL").slice(0,4);
  return (
    <span style={{background:bg,color:c,padding:"1px 6px",borderRadius:3,
      fontSize:9,fontFamily:mono,letterSpacing:.5,flexShrink:0}}>
      {m}({d.toFixed(3)})
    </span>
  );
}

// ── D3 Graph ─────────────────────────────────────────────────────────
function Graph({morphisms=[], objects=[], w=640, h=360, hlMap=null}) {
  const ref = useRef();
  useEffect(() => {
    if (!ref.current || !objects.length) return;
    const svg = d3.select(ref.current); svg.selectAll("*").remove();
    const nodes = objects.map(id => ({id}));
    const links = morphisms.map(m => ({
      source: m.source_label||m.source, target: m.target_label||m.target,
      label: m.label, inferred: m.is_inferred,
    }));
    svg.append("defs").append("marker").attr("id","arr").attr("viewBox","0 -5 10 10")
      .attr("refX",22).attr("refY",0).attr("markerWidth",5).attr("markerHeight",5)
      .attr("orient","auto").append("path").attr("d","M0,-5L10,0L0,5").attr("fill","#4b6280");
    const sim = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d=>d.id).distance(90))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(w/2, h/2))
      .force("collision", d3.forceCollide(28));
    const g = svg.append("g");
    svg.call(d3.zoom().scaleExtent([.2,5]).on("zoom",e=>g.attr("transform",e.transform)));
    const hlSet = hlMap ? new Set([...Object.keys(hlMap),...Object.values(hlMap)]) : null;
    const line = g.append("g").selectAll("line").data(links).enter().append("line")
      .attr("stroke", d => d.inferred ? C.tealDim : C.border2)
      .attr("stroke-width", d => d.inferred ? 1 : 1.5)
      .attr("stroke-dasharray", d => d.inferred ? "4,3" : "none")
      .attr("marker-end","url(#arr)").attr("opacity",.75);
    const eLbl = g.append("g").selectAll("text").data(links).enter().append("text")
      .text(d=>d.label).attr("font-size","8px").attr("font-family",mono)
      .attr("fill",C.muted).attr("text-anchor","middle").attr("dy",-3);
    const node = g.append("g").selectAll("circle").data(nodes).enter().append("circle")
      .attr("r",9)
      .attr("fill", d => hlSet?.has(d.id) ? C.amberDim : C.bg3)
      .attr("stroke", d => hlSet?.has(d.id) ? C.amber : C.blue)
      .attr("stroke-width", d => hlSet?.has(d.id) ? 2.5 : 1.5)
      .call(d3.drag()
        .on("start",(e,d)=>{if(!e.active)sim.alphaTarget(.3).restart();d.fx=d.x;d.fy=d.y;})
        .on("drag", (e,d)=>{d.fx=e.x;d.fy=e.y;})
        .on("end",  (e,d)=>{if(!e.active)sim.alphaTarget(0);d.fx=null;d.fy=null;}));
    const nLbl = g.append("g").selectAll("text").data(nodes).enter().append("text")
      .text(d=>d.id).attr("font-size","10px").attr("font-family",mono)
      .attr("fill", d => hlSet?.has(d.id) ? C.amber : C.text)
      .attr("text-anchor","middle").attr("dy",-14)
      .attr("font-weight", d => hlSet?.has(d.id) ? "700" : "400");
    sim.on("tick", () => {
      line.attr("x1",d=>d.source.x).attr("y1",d=>d.source.y).attr("x2",d=>d.target.x).attr("y2",d=>d.target.y);
      eLbl.attr("x",d=>(d.source.x+d.target.x)/2).attr("y",d=>(d.source.y+d.target.y)/2);
      node.attr("cx",d=>d.x).attr("cy",d=>d.y);
      nLbl.attr("x",d=>d.x).attr("y",d=>d.y);
    });
    return () => sim.stop();
  }, [morphisms, objects, w, h, hlMap]);
  return <svg ref={ref} width={w} height={h}
    style={{background:C.bg0,borderRadius:8,border:`1px solid ${C.border}`,display:"block"}}/>;
}

// ── ProofNode ─────────────────────────────────────────────────────────
function ProofNode({node, depth=0}) {
  const [open, setOpen] = useState(depth < 3);
  if (!node || node.error) return <div style={{color:C.red,fontSize:11,padding:"4px 0"}}>{node?.error||"Unknown"}</div>;
  const hasKids = node.premises?.length > 0;
  const m = node.truth?.match(/([A-Z]+)\(([0-9.]+)\)/) || [];
  const deg = m[2] ? parseFloat(m[2]) : 1;
  const mod = m[1] || "ACTUAL";
  const ruleLabel = node.rule || (node.is_inferred ? "derived" : "axiom");
  const ruleCol   = node.is_inferred ? C.purple : C.teal;
  const barCol    = depth === 0 ? C.blue : depth === 1 ? C.purple : C.muted;
  return (
    <div style={{marginLeft: depth*18, marginBottom:2}}>
      <div onClick={()=>hasKids&&setOpen(o=>!o)} style={{
        display:"flex", alignItems:"baseline", gap:8, padding:"5px 8px",
        background: depth===0 ? C.bg3 : "transparent",
        borderLeft:`2px solid ${barCol}`,
        borderRadius: depth===0 ? "0 6px 6px 0" : 0,
        cursor: hasKids ? "pointer" : "default", flexWrap:"wrap",
      }}>
        {hasKids && <span style={{color:C.muted,fontSize:9,userSelect:"none"}}>{open?"▾":"▸"}</span>}
        <span style={{fontFamily:mono,fontSize:11,color:C.blue}}>{node.source}</span>
        <span style={{color:C.muted,fontSize:11}}>→</span>
        <span style={{fontFamily:mono,fontSize:11,color:C.amber}}>{node.target}</span>
        <span style={{fontSize:10,color:C.text,marginLeft:4}}>{node.label}</span>
        {node.rel_type && <span style={{fontSize:9,color:C.muted,fontFamily:mono}}>[{node.rel_type}]</span>}
        <TruthBadge degree={deg} modality={mod}/>
        <span style={{fontSize:9,color:ruleCol,fontFamily:mono,marginLeft:4}}>{ruleLabel}</span>
      </div>
      {node.evidence?.length > 0 && (
        <div style={{marginLeft:14,marginTop:2}}>
          {node.evidence.map((ev,i) => (
            <div key={i} style={{fontSize:9,fontFamily:mono,padding:"1px 6px",
              color: ev.direction==="supports" ? C.green : C.red}}>
              {ev.direction==="supports"?"⊕":"⊖"} {ev.label}
              <span style={{color:C.muted}}> str={ev.strength?.toFixed(2)}</span>
            </div>
          ))}
        </div>
      )}
      {open && hasKids && (
        <div style={{marginTop:2}}>
          {node.premises.map((p,i) => <ProofNode key={i} node={p} depth={depth+1}/>)}
        </div>
      )}
    </div>
  );
}

// ── PipelineStep ──────────────────────────────────────────────────────
const STEP_NAMES = ["","Import check","Evidence audit","Auto-compose","Analogy search","Store program","Run tests","Inspect derivations"];
function PipelineStep({n, result, running}) {
  const [open, setOpen] = useState(false);
  const ok      = result?.ok !== false && !result?.error;
  const skipped = result?.skipped;
  const icon  = running?"◌": skipped?"—": ok?"✓":"✗";
  const col   = running?C.amber: skipped?C.muted: ok?C.green:C.red;
  const bg    = running?C.amberDim: skipped?C.bg3: ok?C.greenDim:C.redDim;
  return (
    <div style={{borderBottom:`1px solid ${C.border}`}}>
      <div onClick={()=>result&&setOpen(o=>!o)}
        style={{display:"flex",alignItems:"center",gap:10,padding:"10px 14px",cursor:result?"pointer":"default"}}>
        <span style={{width:20,height:20,borderRadius:"50%",background:bg,border:`1.5px solid ${col}`,
          display:"flex",alignItems:"center",justifyContent:"center",
          fontSize:10,color:col,fontWeight:700,flexShrink:0}}>{icon}</span>
        <span style={{fontSize:9,color:C.muted,fontFamily:mono,width:14}}>{n}</span>
        <span style={{fontSize:12,color:C.text,flex:1}}>{STEP_NAMES[n]}</span>
        {result?.duration_ms!=null && <span style={{fontSize:9,color:C.muted,fontFamily:mono}}>{result.duration_ms.toFixed(0)}ms</span>}
        {result?.best_score!=null  && <TruthBadge degree={result.best_score} modality="SCORE"/>}
        {result && <span style={{fontSize:9,color:C.muted}}>{open?"▴":"▾"}</span>}
      </div>
      {open && result && (
        <div style={{padding:"6px 14px 14px 48px",fontFamily:mono,fontSize:10,color:C.muted}}>
          {n===1 && <><span style={{color:C.blue}}>{result.source}</span> ({result.source_objects} obj) → <span style={{color:C.amber}}>{result.target}</span> ({result.target_objects} obj)</>}
          {n===2 && <><div>Source: <span style={{color:C.text}}>{result.source_evidenced}/{result.source_total}</span> morphisms with evidence</div><div>Target: <span style={{color:C.text}}>{result.target_evidenced}/{result.target_total}</span> morphisms with evidence</div></>}
          {n===3 && <><span style={{color:C.text}}>{result.new_compositions}</span> new · <span style={{color:C.teal}}>{result.stored_to_kernel}</span> stored</>}
          {n===4 && result.object_map && <div>
            <div style={{marginBottom:6,color:C.text}}>method={result.method} · str={result.structural_score?.toFixed(3)??"–"} · sem={result.semantic_score?.toFixed(3)??"–"}{result.partial&&" · partial"}</div>
            {Object.entries(result.object_map).map(([s,t])=>(
              <div key={s} style={{display:"flex",gap:8,padding:"1px 0"}}>
                <span style={{color:C.blue,minWidth:140}}>{s}</span>
                <span style={{color:C.muted}}>↦</span>
                <span style={{color:C.amber}}>{t}</span>
              </div>
            ))}
          </div>}
          {n===4 && !result.object_map && <span style={{color:C.red}}>No analogy found</span>}
          {n===5 && (result.program_id
            ? <span>Program <span style={{color:C.teal}}>{result.program_name}</span> registered · score={result.score?.toFixed(3)}</span>
            : <span style={{color:C.muted}}>{result.message}</span>)}
          {n===6 && (result.skipped
            ? <span style={{color:C.muted}}>Skipped — no program</span>
            : result.total===0
            ? <span style={{color:C.muted}}>No tests registered yet</span>
            : <span>{result.passed}/{result.total} passed</span>)}
          {n===7 && <div>
            <div><span style={{color:C.teal}}>{result.inferred_morphisms}</span> inferred morphisms</div>
            {result.weak_morphisms>0 && <div style={{marginTop:4}}>
              <span style={{color:C.amber}}>⚠ {result.weak_morphisms}</span> morphisms with truth &lt; 0.7
              {result.weak_details?.slice(0,5).map((wm,i)=>(
                <div key={i} style={{paddingLeft:12,color:C.red}}>{wm.label}: {wm.source}→{wm.target} {wm.truth?.toFixed(3)}</div>
              ))}
            </div>}
          </div>}
        </div>
      )}
    </div>
  );
}

// ── BeliefDiff ────────────────────────────────────────────────────────
function BeliefDiff({changes}) {
  if (!changes?.length) return <div style={{color:C.muted,fontSize:11,padding:"8px 0"}}>No propagated changes.</div>;
  return (
    <div>
      <div style={hdSt()}>Propagated to {changes.length} morphism{changes.length!==1?"s":""}</div>
      {changes.map((c,i) => (
        <div key={i} style={{
          display:"flex",alignItems:"center",gap:8,padding:"4px 8px",marginBottom:2,
          background:C.bg2,borderRadius:4,borderLeft:`2px solid ${c.delta>0?C.green:C.red}`,
          fontSize:10,fontFamily:mono,flexWrap:"wrap",
        }}>
          <span style={{color:c.is_inferred?C.purple:C.teal,fontSize:9}}>{c.is_inferred?"derived":"direct"}</span>
          <span style={{color:C.blue}}>{c.source}</span>
          <span style={{color:C.muted}}>→</span>
          <span style={{color:C.amber}}>{c.target}</span>
          <span style={{flex:1,color:C.text,overflow:"hidden",textOverflow:"ellipsis"}}>{c.label}</span>
          <span style={{color:C.muted}}>{c.truth_before}</span>
          <span style={{color:C.muted}}>→</span>
          <span style={{color:c.delta>0?C.green:C.red}}>{c.truth_after}</span>
          <span style={{color:c.delta>0?C.green:C.red}}>{c.delta>0?"▲":"▼"}{Math.abs(c.delta).toFixed(3)}</span>
        </div>
      ))}
    </div>
  );
}


// ════════════════════════════════════════════════════════════════
// TOPOLOGY TAB — Categorical topology analysis
// ════════════════════════════════════════════════════════════════
function TopoTab({domains}) {
  const [mode,setMode]       = useState("report");
  const [dom1,setDom1]       = useState("");
  const [dom2,setDom2]       = useState("");
  const [maxDim,setMaxDim]   = useState(3);
  const [tNorm,setTNorm]     = useState("godel");
  const [minPers,setMinPers] = useState(0.0);
  const [result,setResult]   = useState(null);
  const [loading,setLoading] = useState(false);
  const [error,setError]     = useState(null);

  const MODES = ["report","homology","persistent","groupoid","yoneda","limits","metric","compare"];
  const MODE_LABELS = {
    report:"Full Report",homology:"Homology",persistent:"Persistence",
    groupoid:"π₀ π₁",yoneda:"Yoneda",limits:"Limits",metric:"Metric",compare:"Compare"
  };

  const run = async () => {
    setLoading(true); setResult(null); setError(null);
    try {
      let r;
      if (mode==="report") {
        r = await post("/api/topology/report",{domain_name:dom1,max_dim:maxDim,t_norm:tNorm,min_persistence:minPers});
      } else if (mode==="homology") {
        r = await get(`/api/topology/${encodeURIComponent(dom1)}/homology?max_dim=${maxDim}`);
      } else if (mode==="persistent") {
        r = await post("/api/topology/persistent-homology",{domain_name:dom1,max_dim:maxDim,min_persistence:minPers});
      } else if (mode==="groupoid") {
        r = await get(`/api/topology/${encodeURIComponent(dom1)}/fundamental-groupoid`);
      } else if (mode==="yoneda") {
        r = await get(`/api/topology/${encodeURIComponent(dom1)}/yoneda`);
      } else if (mode==="limits") {
        r = await get(`/api/topology/${encodeURIComponent(dom1)}/limits`);
      } else if (mode==="metric") {
        r = await get(`/api/topology/${encodeURIComponent(dom1)}/metric-enrichment?t_norm=${tNorm}`);
      } else if (mode==="compare") {
        r = await post("/api/topology/compare",{domain1:dom1,domain2:dom2,max_dim:maxDim});
      }
      setResult(r);
    } catch(e) { setError(e.message); }
    setLoading(false);
  };

  const domSel = (val, setter) => (
    <select value={val} onChange={e=>setter(e.target.value)}
      style={{...inputSt,width:160,marginRight:8}}>
      <option value="">— domain —</option>
      {domains.map(d=><option key={d.name} value={d.name}>{d.name}</option>)}
    </select>
  );

  const renderBetti = (betti) => (
    <div style={{display:"flex",gap:12,flexWrap:"wrap",marginTop:4}}>
      {Object.entries(betti).map(([n,b])=>(
        <div key={n} style={{background:C.bg2,border:`1px solid ${C.border2}`,
          borderRadius:6,padding:"4px 10px",textAlign:"center"}}>
          <div style={{fontSize:9,color:C.muted}}>β<sub>{n}</sub></div>
          <div style={{fontSize:18,fontWeight:700,color:b>0?C.blue:C.muted}}>{b}</div>
        </div>
      ))}
    </div>
  );

  const renderPairs = (pairs) => {
    if (!pairs||!pairs.length) return <div style={{color:C.muted,fontSize:10}}>No pairs above threshold</div>;
    const byDim = {};
    pairs.forEach(p=>{(byDim[p.dim]||(byDim[p.dim]=[])).push(p);});
    return Object.entries(byDim).map(([dim,ps])=>(
      <div key={dim} style={{marginBottom:8}}>
        <div style={hdSt({marginBottom:4})}>H<sub>{dim}</sub> — {ps.length} pair(s)</div>
        {ps.slice(0,10).map((p,i)=>(
          <div key={i} style={{display:"flex",gap:12,fontSize:10,padding:"3px 0",
            borderBottom:`1px solid ${C.border}`}}>
            <span style={{color:C.green}}>born τ={p.birth_truth}</span>
            <span style={{color:C.red}}>dies τ={p.essential?"never":p.death_truth}</span>
            <span style={{color:p.persistence>0.2?C.blue:C.muted}}>
              pers={p.essential?"∞":p.persistence}
            </span>
            {p.essential&&<span style={{color:C.gold,fontSize:9}}>ESSENTIAL</span>}
          </div>
        ))}
      </div>
    ));
  };

  const renderComponents = (comps) => (
    <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
      {comps.map((c,i)=>(
        <div key={i} style={cardSt({padding:"4px 8px",fontSize:10})}>
          {c.join(", ")}
        </div>
      ))}
    </div>
  );

  return (
    <div style={{display:"flex",flexDirection:"column",height:"calc(100vh-120px)",overflowY:"auto",padding:"0 4px"}}>
      <div style={{...cardSt(),padding:12,marginBottom:12,flexShrink:0}}>
        <div style={{display:"flex",gap:6,flexWrap:"wrap",marginBottom:10}}>
          {MODES.map(m=>(
            <button key={m} onClick={()=>{setMode(m);setResult(null);}}
              style={{...btnSt(m===mode?C.blue:C.bg3, m===mode?C.blueDim:C.border2),
                color:m===mode?C.text:C.muted,fontSize:10,padding:"3px 10px"}}>
              {MODE_LABELS[m]}
            </button>
          ))}
        </div>
        <div style={{display:"flex",gap:8,flexWrap:"wrap",alignItems:"center"}}>
          {domSel(dom1, setDom1)}
          {mode==="compare"&&domSel(dom2, setDom2)}
          <div style={{display:"flex",alignItems:"center",gap:4,fontSize:10,color:C.muted}}>
            dim≤
            <input type="number" min={1} max={4} value={maxDim}
              onChange={e=>setMaxDim(+e.target.value)}
              style={{...inputSt,width:40}} />
          </div>
          {(mode==="metric"||mode==="report")&&(
            <select value={tNorm} onChange={e=>setTNorm(e.target.value)}
              style={{...inputSt,width:120}}>
              <option value="godel">Gödel (min)</option>
              <option value="product">Product (×)</option>
              <option value="lukasiewicz">Łukasiewicz</option>
            </select>
          )}
          {(mode==="persistent"||mode==="report")&&(
            <div style={{display:"flex",alignItems:"center",gap:4,fontSize:10,color:C.muted}}>
              min-pers≥
              <input type="number" min={0} max={1} step={0.05} value={minPers}
                onChange={e=>setMinPers(+e.target.value)}
                style={{...inputSt,width:50}} />
            </div>
          )}
          <button onClick={run} disabled={!dom1||loading}
            style={btnSt(C.blue,C.blueDim)}>
            {loading?"Computing…":"Run ∿"}
          </button>
        </div>
      </div>

      {error&&<div style={cardSt({color:C.red,marginBottom:8})}>{error}</div>}

      {result&&(()=>{
        if (mode==="report") return (
          <div style={{display:"flex",flexDirection:"column",gap:10}}>
            {/* Header */}
            <div style={cardSt({padding:12})}>
              <div style={hdSt({marginBottom:6})}>Category summary</div>
              <div style={{fontSize:11}}>{result.n_objects} objects · {result.n_morphisms} morphisms</div>
            </div>

            {/* Homology */}
            {result.homology&&!result.homology.error&&(
              <div style={cardSt({padding:12})}>
                <div style={hdSt({marginBottom:6})}>Homology H*(C)</div>
                {renderBetti(result.homology.betti_numbers)}
                <div style={{fontSize:10,color:C.muted,marginTop:6}}>{result.homology.interpretation}</div>
              </div>
            )}

            {/* Fundamental groupoid */}
            {result.fundamental_groupoid&&!result.fundamental_groupoid.error&&(
              <div style={cardSt({padding:12})}>
                <div style={hdSt({marginBottom:6})}>Fundamental groupoid</div>
                <div style={{fontSize:12,fontWeight:700,marginBottom:4,color:C.blue}}>
                  {result.fundamental_groupoid.homotopy_type}
                </div>
                <div style={{fontSize:10,color:C.muted,marginBottom:6}}>
                  π₀: {result.fundamental_groupoid.n_components} component(s) ·
                  π₁ rank: {result.fundamental_groupoid.pi1_rank}
                </div>
                {renderComponents(result.fundamental_groupoid.pi0)}
              </div>
            )}

            {/* Persistent homology sample */}
            {result.persistent_homology&&!result.persistent_homology.error&&(
              <div style={cardSt({padding:12})}>
                <div style={hdSt({marginBottom:6})}>Persistence diagram ({result.persistent_homology.pairs?.length||0} pairs)</div>
                {renderPairs((result.persistent_homology.pairs||[]).slice(0,12))}
              </div>
            )}

            {/* Isomorphisms */}
            {result.isomorphisms&&(
              <div style={cardSt({padding:12})}>
                <div style={hdSt({marginBottom:6})}>Isomorphism structure</div>
                <div style={{fontSize:11}}>
                  {result.isomorphisms.n_isomorphisms} strict isomorphism(s)
                  · {result.isomorphisms.isomorphism_classes_strict?.length||0} iso class(es)
                </div>
              </div>
            )}

            {/* Metric */}
            {result.metric_enrichment&&!result.metric_enrichment.error&&(
              <div style={cardSt({padding:12})}>
                <div style={hdSt({marginBottom:6})}>Metric enrichment ({result.metric_enrichment.t_norm})</div>
                <div style={{fontSize:11}}>{result.metric_enrichment.interpretation}</div>
                <div style={{fontSize:10,color:C.muted,marginTop:4}}>
                  Triangle violations: {result.metric_enrichment.n_triangle_violations} ·
                  Symmetry: {result.metric_enrichment.symmetry_degree}
                </div>
              </div>
            )}
          </div>
        );

        if (mode==="homology") return (
          <div style={cardSt({padding:14})}>
            <div style={hdSt({marginBottom:8})}>Homology of N({result.domain})</div>
            {renderBetti(result.betti_numbers)}
            <div style={{fontSize:11,marginTop:10}}>
              χ(C) = {result.euler_characteristic} ·
              {result.is_connected?" Connected":" Disconnected"}
            </div>
            <div style={{marginTop:10,fontSize:10,color:C.muted}}>
              <div style={hdSt({marginBottom:4})}>Nerve complex</div>
              {Object.entries(result.nerve.simplices_by_dim||{}).map(([d,n])=>(
                <div key={d}>dim {d}: {n} simplex{n!==1?"es":""}</div>
              ))}
            </div>
          </div>
        );

        if (mode==="persistent") return (
          <div style={cardSt({padding:14})}>
            <div style={hdSt({marginBottom:8})}>Persistence diagram — {result.domain}</div>
            <div style={{display:"flex",gap:12,marginBottom:10}}>
              {Object.entries(result.betti_numbers||{}).map(([n,b])=>(
                <div key={n} style={{textAlign:"center"}}>
                  <div style={{fontSize:9,color:C.muted}}>β{n}</div>
                  <div style={{fontSize:16,fontWeight:700,color:b>0?C.blue:C.muted}}>{b}</div>
                </div>
              ))}
            </div>
            {renderPairs(result.pairs||[])}
            <div style={{fontSize:10,color:C.muted,marginTop:6}}>
              Computed in {result.computation_ms}ms
            </div>
          </div>
        );

        if (mode==="groupoid") return (
          <div style={cardSt({padding:14})}>
            <div style={hdSt({marginBottom:8})}>Fundamental groupoid Π₁({result.domain})</div>
            <div style={{fontSize:14,fontWeight:700,color:C.blue,marginBottom:8}}>
              {result.homotopy_type}
            </div>
            <div style={{fontSize:11,marginBottom:10}}>
              π₀: {result.n_components} component(s) &nbsp;|&nbsp; π₁ rank: {result.pi1_rank}
            </div>
            <div style={hdSt({marginBottom:6})}>Connected components (τ=0)</div>
            {renderComponents(result.pi0)}
            <div style={{marginTop:12}}>
              <div style={hdSt({marginBottom:6})}>Graded components by truth threshold</div>
              {Object.entries(result.graded_components||{}).map(([t,comps])=>(
                <div key={t} style={{marginBottom:8}}>
                  <div style={{fontSize:9,color:C.muted,marginBottom:2}}>τ ≥ {t}:</div>
                  <div style={{display:"flex",gap:4,flexWrap:"wrap"}}>
                    {comps.map((c,i)=>(
                      <span key={i} style={{fontSize:9,background:C.bg2,
                        border:`1px solid ${C.border}`,borderRadius:3,padding:"1px 5px"}}>
                        {"{"+c.join(",")+"}"}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );

        if (mode==="yoneda") return (
          <div style={cardSt({padding:14})}>
            <div style={hdSt({marginBottom:8})}>Yoneda embedding y: {result.domain||dom1} → [Cᵒᵖ, [0,1]]</div>
            <div style={{fontSize:11,marginBottom:10}}>
              Matrix rank: <strong>{result.matrix_rank}</strong>/{result.n_objects} —
              {result.is_full_rank?" Fully faithful (objects distinguishable)":" Rank-deficient (duplicate hom-profiles)"}
            </div>
            <div style={hdSt({marginBottom:6})}>Representable presheaf norms ‖y(A)‖</div>
            <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
              {Object.entries(result.row_norms||{}).map(([obj,norm])=>(
                <div key={obj} style={{...cardSt(),padding:"4px 8px",fontSize:10}}>
                  <div style={{color:C.muted,fontSize:9}}>{obj}</div>
                  <div style={{fontWeight:700,color:C.blue}}>{norm}</div>
                </div>
              ))}
            </div>
          </div>
        );

        if (mode==="limits") return (
          <div style={cardSt({padding:14})}>
            <div style={hdSt({marginBottom:8})}>Limits & Colimits in {result.domain}</div>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:10}}>
              <div style={cardSt({padding:10})}>
                <div style={{fontSize:10,color:C.muted,marginBottom:4}}>Terminal object (limit)</div>
                <div style={{fontSize:13,fontWeight:700}}>{result.terminal_object?.apex||"—"}</div>
                <div style={{fontSize:9,color:C.muted}}>degree {result.terminal_object?.degree}</div>
              </div>
              <div style={cardSt({padding:10})}>
                <div style={{fontSize:10,color:C.muted,marginBottom:4}}>Initial object (colimit)</div>
                <div style={{fontSize:13,fontWeight:700}}>{result.initial_object?.apex||"—"}</div>
                <div style={{fontSize:9,color:C.muted}}>degree {result.initial_object?.degree}</div>
              </div>
            </div>
            <div style={hdSt({marginBottom:6})}>Sample products A × B</div>
            {(result.products||[]).map((p,i)=>(
              <div key={i} style={{fontSize:10,padding:"3px 0",borderBottom:`1px solid ${C.border}`}}>
                {p.a} × {p.b} = <strong>{p.apex||"?"}</strong>
                <span style={{color:C.muted,marginLeft:8}}>deg {p.degree}</span>
              </div>
            ))}
          </div>
        );

        if (mode==="metric") return (
          <div style={cardSt({padding:14})}>
            <div style={hdSt({marginBottom:8})}>Lawvere metric enrichment ({result.t_norm})</div>
            <div style={{fontSize:12,marginBottom:8,fontWeight:500}}>
              {result.interpretation}
            </div>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8,marginBottom:10}}>
              <div style={cardSt({padding:8})}>
                <div style={{fontSize:9,color:C.muted}}>Identity axiom</div>
                <div style={{fontSize:13,color:result.identity_axiom_ok?C.green:C.red}}>
                  {result.identity_axiom_ok?"✓ OK":"✗ Violated"}
                </div>
              </div>
              <div style={cardSt({padding:8})}>
                <div style={{fontSize:9,color:C.muted}}>Composition axiom (△)</div>
                <div style={{fontSize:13,color:result.composition_axiom_ok?C.green:C.red}}>
                  {result.composition_axiom_ok?"✓ OK":`✗ ${result.n_triangle_violations} violations`}
                </div>
              </div>
              <div style={cardSt({padding:8})}>
                <div style={{fontSize:9,color:C.muted}}>Symmetry degree</div>
                <div style={{fontSize:13,color:result.symmetry_degree>0.8?C.green:C.gold}}>
                  {result.symmetry_degree}
                </div>
              </div>
              <div style={cardSt({padding:8})}>
                <div style={{fontSize:9,color:C.muted}}>Metric type</div>
                <div style={{fontSize:11}}>
                  {result.is_symmetric_metric?"Symmetric (undirected)":"Lawvere (directed)"}
                </div>
              </div>
            </div>
            {result.triangle_violations_sample?.length>0&&(
              <>
                <div style={hdSt({marginBottom:4})}>Sample violations</div>
                {result.triangle_violations_sample.map((v,i)=>(
                  <div key={i} style={{fontSize:9,color:C.red,padding:"2px 0"}}>
                    {v.a}→{v.b}→{v.c}: {v.composed}>{v.hac} (Δ={v.violation})
                  </div>
                ))}
              </>
            )}
          </div>
        );

        if (mode==="compare") return (
          <div style={cardSt({padding:14})}>
            <div style={hdSt({marginBottom:8})}>Topological comparison</div>
            <div style={{fontSize:12,marginBottom:10}}>
              {result.domain1} vs {result.domain2}
            </div>
            <div style={{marginBottom:10}}>
              <div style={hdSt({marginBottom:6})}>Bottleneck distances W∞</div>
              {Object.entries(result.bottleneck_distances||{}).map(([k,v])=>(
                <div key={k} style={{display:"flex",justifyContent:"space-between",
                  fontSize:11,padding:"4px 0",borderBottom:`1px solid ${C.border}`}}>
                  <span>{k.replace("bottleneck_dim","H")}</span>
                  <span style={{color:v<0.1?C.green:v<0.3?C.gold:C.red,fontWeight:700}}>
                    {v===null?"N/A":v}
                  </span>
                </div>
              ))}
            </div>
            <div style={{fontSize:11,color:C.blue,marginTop:8}}>{result.interpretation}</div>
          </div>
        );

        return <pre style={{fontSize:10,color:C.muted,whiteSpace:"pre-wrap"}}>{JSON.stringify(result,null,2)}</pre>;
      })()}
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
// APP
// ════════════════════════════════════════════════════════════════
export default function App() {
  const [tab,setTab]           = useState("explore");
  const [domains,setDomains]   = useState([]);
  const [sel,setSel]           = useState(null);
  const [selData,setSelData]   = useState(null);
  const [datasets,setDatasets] = useState({});
  const [stats,setStats]       = useState({});
  const [programs,setPrograms] = useState([]);
  const [connected,setConnected] = useState(false);

  // Search
  const [src,setSrc]=useState(""); const [tgt,setTgt]=useState(""); const [method,setMethod]=useState("csp");
  const [searchRes,setSearchRes]=useState(null); const [searching,setSearching]=useState(false);

  // Pipeline
  const [pSrc,setPSrc]=useState(""); const [pTgt,setPTgt]=useState(""); const [pMeth,setPMeth]=useState("csp");
  const [pRes,setPRes]=useState(null); const [pRunning,setPRunning]=useState(false);

  // Explain
  const [xId,setXId]=useState(""); const [xDom,setXDom]=useState(""); const [xSrc,setXSrc]=useState(""); const [xTgt,setXTgt]=useState("");
  const [xRes,setXRes]=useState(null); const [xLoading,setXLoading]=useState(false); const [xMode,setXMode]=useState("id");

  // Belief
  const [bMid,setBMid]=useState(""); const [bLabel,setBLabel]=useState(""); const [bDir,setBDir]=useState("contradicts"); const [bStr,setBStr]=useState("0.8");
  const [bRes,setBRes]=useState(null); const [bLoading,setBLoading]=useState(false);

  // REPL
  const [ri,setRi]=useState(""); const [rh,setRh]=useState([{t:"sys",x:"MORPHOS v3 · type 'help' for commands\nExamples: pipeline music math · compose grammar · search celtic → types"}]);
  const replEnd = useRef();
  const addR = e => setRh(h=>[...h,e]);

  const refresh = useCallback(async () => {
    const r=await get("/api/domains"); if(r.domains){setDomains(r.domains);setConnected(true);}
    const d=await get("/api/datasets"); if(d.datasets) setDatasets(d.datasets);
    const h=await get("/health"); if(h.store) setStats(h.store);
    const p=await get("/api/programs"); if(p.programs) setPrograms(p.programs);
  }, []);
  useEffect(()=>{refresh();},[refresh]);

  const loadDomain = useCallback(async name => {
    setSel(name);
    const d = await get(`/api/domains/${name}`);
    if (d.id) {
      const [m,c] = await Promise.all([get(`/api/domains/${d.id}/morphisms`),get(`/api/domains/${d.id}/concepts`)]);
      setSelData({...d, morphisms:m.morphisms||[], concepts:c.concepts||[]});
    }
  },[]);
  useEffect(()=>{if(sel)loadDomain(sel);},[sel]);
  useEffect(()=>{replEnd.current?.scrollIntoView({behavior:"smooth"});},[rh]);

  const doImport = async name => { await post(`/api/import/dataset/${name}`,{}); await refresh(); };

  const doSearch = async () => {
    if(!src||!tgt) return; setSearching(true); setSearchRes(null);
    setSearchRes(await post("/api/search",{source_domain:src,target_domain:tgt,method,max_results:5}));
    setSearching(false);
  };

  const doPipeline = async () => {
    if(!pSrc||!pTgt) return; setPRunning(true); setPRes(null);
    setPRes(await post("/api/pipeline",{source_domain:pSrc,target_domain:pTgt,method:pMeth}));
    setPRunning(false); await refresh();
  };

  const doExplain = async () => {
    setXLoading(true); setXRes(null);
    if (xMode==="id") {
      if (!xId.trim()) { setXLoading(false); return; }
      setXRes({type:"morphism", data:await get(`/api/explain/${xId.trim()}`)});
    } else {
      if (!xDom||!xSrc||!xTgt) { setXLoading(false); return; }
      setXRes({type:"path", data:await get(`/api/explain/${xDom}/path?source=${encodeURIComponent(xSrc)}&target=${encodeURIComponent(xTgt)}`)});
    }
    setXLoading(false);
  };

  const doBelief = async () => {
    if (!bMid||!bLabel) return; setBLoading(true); setBRes(null);
    setBRes(await post("/api/belief/update",{morphism_id:bMid,label:bLabel,direction:bDir,strength:parseFloat(bStr)||.8,show_propagation:true}));
    setBLoading(false); if(sel) loadDomain(sel);
  };

  const doRepl = async () => {
    if (!ri.trim()) return;
    const input=ri.trim(); addR({t:"usr",x:input}); setRi("");
    const r=await post("/api/compile/execute",{query:input});
    if (r.error) { addR({t:"err",x:r.error}); return; }
    const lines=[];
    if (r.action) lines.push(`action: ${r.action}  conf: ${(r.confidence||0).toFixed(2)}`);
    if (r.result) {
      const res=r.result;
      if (res.error) { addR({t:"err",x:res.error}); return; }
      if (res.object_map) {
        lines.push("Analogy found:");
        Object.entries(res.object_map).forEach(([s,t])=>lines.push(`  ${s.padEnd(24)} ↦ ${t}`));
        if (res.best_score!=null) lines.push(`score: ${res.best_score.toFixed(3)}`);
      } else if (res.new_compositions!=null) {
        lines.push(`Composed: ${res.new_compositions} new · ${res.stored_to_kernel} stored`);
      } else if (res.new_inferences!=null) {
        lines.push(`Inferred: ${res.new_inferences} via ${res.rule}`);
      } else if (res.speculated!=null) {
        lines.push(`Speculated: ${res.speculated} morphisms`);
      } else {
        const s=JSON.stringify(res,null,2); lines.push(s.length>600?s.slice(0,600)+"\n…":s);
      }
    } else { lines.push(`(${r.action} — use the dedicated tab for interactive results)`); }
    addR({t:"res",x:lines.join("\n")});
    if (["compose","infer","map","speculate"].includes(r.action)||r.result?.program_id) await refresh();
  };

  // ── Proof tab state ────────────────────────────────
  const [prMid,setPrMid]=useState(""); const [prRes,setPrRes]=useState(null); const [prLoading,setPrLoading]=useState(false);
  const [prMode,setPrMode]=useState("check");
  const [prDepRec,setPrDepRec]=useState(false);
  const [prESrc,setPrESrc]=useState(""); const [prETgt,setPrETgt]=useState(""); const [prEMap,setPrEMap]=useState(""); const [prEName,setPrEName]=useState("");
  const [prAuditDom,setPrAuditDom]=useState("");

  const doProof = async () => {
    setPrLoading(true); setPrRes(null);
    if (prMode==="check") {
      if(!prMid.trim()){setPrLoading(false);return;}
      setPrRes(await get(`/api/proof/${prMid.trim()}/check`));
    } else if (prMode==="normalize") {
      if(!prMid.trim()){setPrLoading(false);return;}
      setPrRes(await get(`/api/proof/${prMid.trim()}/normalize`));
    } else if (prMode==="dependents") {
      if(!prMid.trim()){setPrLoading(false);return;}
      setPrRes(await get(`/api/morphisms/${prMid.trim()}/dependents?recursive=${prDepRec}`));
    } else if (prMode==="extract") {
      try {
        const map = JSON.parse(prEMap||"{}");
        setPrRes(await post("/api/extract/common-core",{source_domain:prESrc,target_domain:prETgt,object_map:map,new_domain_name:prEName}));
        await refresh();
      } catch(e){setPrRes({error:"Invalid JSON in object map: "+e.message});}
    } else if (prMode==="audit") {
      if(!prAuditDom){setPrLoading(false);return;}
      setPrRes(await get(`/api/proof/audit/${encodeURIComponent(prAuditDom)}`));
    }
    setPrLoading(false);
  };

  const TABS = ["explore","search","pipeline","explain","belief","proof","topo","repl","memory","import"];
  const TAB_LABELS = {explore:"Explore",search:"Search",pipeline:"Pipeline",explain:"Explain",belief:"Belief ∂",proof:"Proof ⊢",topo:"Topology ∿",repl:"REPL",memory:"Memory",import:"Import"};

  const graphW = typeof window!=="undefined" ? Math.min(740,window.innerWidth-210) : 680;

  return (
    <div style={{display:"flex",flexDirection:"column",height:"100vh",background:C.bg0,color:C.text,fontFamily:sans,fontSize:12}}>
      {/* Header */}
      <div style={{display:"flex",alignItems:"center",padding:"0 16px",height:44,
        background:C.bg1,borderBottom:`1px solid ${C.border}`,flexShrink:0,gap:12}}>
        <span style={{fontFamily:mono,fontSize:13,fontWeight:700,color:C.teal,letterSpacing:-.5}}>MORPHOS</span>
        <span style={{fontSize:9,color:C.muted,fontFamily:mono}}>reasoning os v3</span>
        <div style={{flex:1}}/>
        {[["dom",stats.domains],["morph",stats.morphisms],["deriv",stats.derivations],["prog",stats.programs]].map(([k,v])=>(
          <span key={k} style={{fontSize:9,fontFamily:mono,color:C.muted}}>
            <span style={{color:C.text}}>{v??0}</span> {k}
          </span>
        ))}
        <span style={{width:7,height:7,borderRadius:"50%",background:connected?C.green:C.red,flexShrink:0}}
          title={connected?"API connected":"Not connected"}/>
      </div>

      <div style={{display:"flex",flex:1,overflow:"hidden"}}>
        {/* Sidebar */}
        <div style={{width:176,background:C.bg1,borderRight:`1px solid ${C.border}`,display:"flex",flexDirection:"column",flexShrink:0}}>
          <div style={{padding:"8px 0",borderBottom:`1px solid ${C.border}`}}>
            {TABS.map(t=>(
              <div key={t} onClick={()=>setTab(t)} style={{
                padding:"7px 14px",cursor:"pointer",fontSize:11,
                color:tab===t?C.text:C.muted,
                background:tab===t?C.bg3:"transparent",
                borderLeft:`2px solid ${tab===t?C.blue:"transparent"}`,
              }}>{TAB_LABELS[t]}</div>
            ))}
          </div>
          <div style={{padding:"10px 8px 4px",fontSize:9,color:C.muted,letterSpacing:2,textTransform:"uppercase"}}>Domains</div>
          <div style={{overflowY:"auto",flex:1}}>
            {domains.map(d=>(
              <div key={d.id} onClick={()=>{setTab("explore");setSel(d.name);}} style={{
                padding:"5px 14px",cursor:"pointer",fontSize:11,
                color:sel===d.name?C.teal:C.text,
                background:sel===d.name?"#0d1e2e":"transparent",
                borderLeft:`2px solid ${sel===d.name?C.teal:"transparent"}`,
                overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",
              }}>{d.name}</div>
            ))}
            {!domains.length&&<div style={{padding:12,fontSize:10,color:C.dim}}>No domains. Import first.</div>}
          </div>
        </div>

        {/* Content */}
        <div style={{flex:1,overflowY:"auto",padding:22}}>

          {/* ── EXPLORE ── */}
          {tab==="explore" && selData && (
            <div>
              <div style={{display:"flex",alignItems:"baseline",gap:10,marginBottom:4}}>
                <h2 style={{fontSize:16,margin:0}}>{selData.name}</h2>
                <span style={{fontSize:10,color:C.muted,fontFamily:mono}}>v{selData.version}</span>
              </div>
              <p style={{fontSize:10,color:C.muted,marginBottom:14}}>
                {selData.concepts?.length} objects · {selData.morphisms?.length} morphisms · {selData.morphisms?.filter(m=>m.is_inferred).length||0} inferred
              </p>
              <Graph objects={selData.concepts?.map(c=>c.label)||[]} morphisms={selData.morphisms||[]} w={graphW} h={380}/>
              <div style={{marginTop:14,display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
                <div style={cardSt()}>
                  <h3 style={hdSt()}>Objects ({selData.concepts?.length})</h3>
                  <div style={{display:"flex",flexWrap:"wrap",gap:4}}>
                    {selData.concepts?.map(c=>(
                      <span key={c.label} style={{background:C.bg2,padding:"2px 7px",borderRadius:3,fontSize:10}}>{c.label}</span>
                    ))}
                  </div>
                </div>
                <div style={cardSt()}>
                  <h3 style={hdSt()}>Morphisms</h3>
                  <div style={{maxHeight:210,overflowY:"auto"}}>
                    {selData.morphisms?.slice(0,40).map((m,i)=>(
                      <div key={i} style={{padding:"3px 0",fontSize:10,borderBottom:`1px solid ${C.border}`,
                        display:"flex",gap:6,alignItems:"center",flexWrap:"wrap"}}>
                        <span style={{color:C.blue,fontFamily:mono,minWidth:88}}>{m.label}</span>
                        <span style={{color:C.muted,flex:1}}>{m.source_label}→{m.target_label}</span>
                        <TruthBadge degree={m.truth_degree} modality={m.truth_modality}/>
                        {m.is_inferred&&<span style={{fontSize:8,color:C.purple}}>inferred</span>}
                        <span title="Click to explain this morphism"
                          onClick={()=>{setXId(m.id);setTab("explain");setXMode("id");}}
                          style={{fontSize:8,color:C.dim,cursor:"pointer",marginLeft:"auto",fontFamily:mono,textDecoration:"underline dotted"}}>
                          {m.id?.slice(0,8)}…
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
          {tab==="explore"&&!selData&&<div style={{color:C.muted,fontSize:13,paddingTop:60,textAlign:"center"}}>Select a domain from the sidebar</div>}

          {/* ── SEARCH ── */}
          {tab==="search"&&(
            <div>
              <h2 style={{fontSize:15,marginBottom:12}}>Analogy Search</h2>
              <div style={{display:"flex",gap:8,alignItems:"center",marginBottom:16,flexWrap:"wrap"}}>
                <select value={src} onChange={e=>setSrc(e.target.value)} style={{...inputSt,flex:1}}>
                  <option value="">Source domain...</option>
                  {domains.map(d=><option key={d.id} value={d.name}>{d.name}</option>)}
                </select>
                <span style={{color:C.blue,fontSize:18,fontWeight:700}}>→</span>
                <select value={tgt} onChange={e=>setTgt(e.target.value)} style={{...inputSt,flex:1}}>
                  <option value="">Target domain...</option>
                  {domains.map(d=><option key={d.id} value={d.name}>{d.name}</option>)}
                </select>
                <select value={method} onChange={e=>setMethod(e.target.value)} style={{...inputSt,width:110}}>
                  {["csp","scalable","embedding","exact"].map(m=><option key={m}>{m}</option>)}
                </select>
                <button onClick={doSearch} disabled={searching} style={btnSt()}>{searching?"Searching…":"Search"}</button>
              </div>
              {searchRes?.results?.length>0&&searchRes.results[0].score>0?(()=>{
                const b=searchRes.results[0];
                return (
                  <div style={cardSt()}>
                    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
                      <h3 style={{margin:0,fontSize:12}}>Structural Analogy · {searchRes.method}</h3>
                      <div style={{display:"flex",gap:8,alignItems:"center"}}>
                        {b.structural_score!=null&&<span style={{fontSize:9,color:C.muted,fontFamily:mono}}>str={b.structural_score.toFixed(3)} sem={b.semantic_score?.toFixed(3)??"–"}</span>}
                        <TruthBadge degree={b.score} modality="SCORE"/>
                      </div>
                    </div>
                    {Object.entries(b.object_map).map(([s,t])=>(
                      <div key={s} style={{display:"flex",padding:"4px 0",borderBottom:`1px solid ${C.border}`,fontSize:11,gap:10}}>
                        <span style={{color:C.blue,minWidth:160,fontFamily:mono}}>{s}</span>
                        <span style={{color:C.muted}}>↦</span>
                        <span style={{color:C.amber,fontFamily:mono}}>{t}</span>
                      </div>
                    ))}
                    {searchRes.results.length>1&&<div style={{fontSize:10,color:C.muted,marginTop:8}}>+{searchRes.results.length-1} alternative mapping(s)</div>}
                  </div>
                );
              })():searchRes?<div style={cardSt({color:C.muted})}>No structural analogy found.</div>:null}
            </div>
          )}

          {/* ── PIPELINE ── */}
          {tab==="pipeline"&&(
            <div>
              <h2 style={{fontSize:15,marginBottom:4}}>Reasoning Pipeline</h2>
              <p style={{fontSize:11,color:C.muted,marginBottom:16}}>Canonical 7-step workflow — from raw domains to audited conclusion.</p>
              <div style={{display:"flex",gap:8,alignItems:"center",marginBottom:20,flexWrap:"wrap"}}>
                <select value={pSrc} onChange={e=>setPSrc(e.target.value)} style={{...inputSt,flex:1}}>
                  <option value="">Source domain...</option>
                  {domains.map(d=><option key={d.id} value={d.name}>{d.name}</option>)}
                </select>
                <span style={{color:C.blue,fontSize:18,fontWeight:700}}>→</span>
                <select value={pTgt} onChange={e=>setPTgt(e.target.value)} style={{...inputSt,flex:1}}>
                  <option value="">Target domain...</option>
                  {domains.map(d=><option key={d.id} value={d.name}>{d.name}</option>)}
                </select>
                <select value={pMeth} onChange={e=>setPMeth(e.target.value)} style={{...inputSt,width:110}}>
                  {["csp","embedding","scalable"].map(m=><option key={m}>{m}</option>)}
                </select>
                <button onClick={doPipeline} disabled={pRunning||!pSrc||!pTgt} style={btnSt()}>
                  {pRunning?"Running…":"Run Pipeline"}
                </button>
              </div>
              {pRunning&&<div style={{color:C.amber,fontSize:11,fontFamily:mono,marginBottom:12}}>◌ Executing pipeline…</div>}
              {pRes&&!pRes.error&&(()=>{
                const steps=pRes.steps||{};
                return (
                  <div>
                    <div style={cardSt({marginBottom:14,display:"flex",gap:20,alignItems:"center",flexWrap:"wrap"})}>
                      <span><span style={{color:C.muted}}>Steps: </span><span>{pRes.steps_completed}/{pRes.total_steps}</span></span>
                      <span><span style={{color:C.muted}}>Analogy: </span><TruthBadge degree={pRes.summary?.best_score} modality="SCORE"/></span>
                      {pRes.program_id&&<span style={{fontSize:10,color:C.teal,fontFamily:mono}}>program: {pRes.program_id.slice(0,12)}…</span>}
                      <span style={{fontSize:10,color:C.muted,fontFamily:mono,marginLeft:"auto"}}>{pRes.total_duration_ms?.toFixed(0)}ms total</span>
                    </div>
                    <div style={cardSt({padding:0,overflow:"hidden"})}>
                      {[1,2,3,4,5,6,7].map(n=>{
                        const key=Object.keys(steps).find(k=>k.startsWith(`step_${n}_`));
                        return <PipelineStep key={n} n={n} result={key?steps[key]:null} running={false}/>;
                      })}
                    </div>
                  </div>
                );
              })()}
              {pRes?.error&&<div style={cardSt({color:C.red})}>{pRes.error}</div>}
              {!pRes&&!pRunning&&<div style={{color:C.muted,fontSize:11}}>Select source and target, then run the pipeline.</div>}
            </div>
          )}

          {/* ── EXPLAIN ── */}
          {tab==="explain"&&(
            <div>
              <h2 style={{fontSize:15,marginBottom:4}}>Proof Explorer</h2>
              <p style={{fontSize:11,color:C.muted,marginBottom:14}}>Trace any morphism to its axioms and evidence. Click an ID shortcode in the Explore tab to jump here.</p>
              <div style={{display:"flex",gap:0,marginBottom:14,background:C.bg2,borderRadius:6,padding:3,width:"fit-content"}}>
                {[["id","By morphism ID"],["path","By path"]].map(([m,l])=>(
                  <button key={m} onClick={()=>setXMode(m)} style={{
                    background:xMode===m?C.bg3:"transparent", border:"none",
                    color:xMode===m?C.text:C.muted, padding:"5px 14px",
                    borderRadius:4,cursor:"pointer",fontSize:11,fontFamily:sans,fontWeight:xMode===m?600:400,
                  }}>{l}</button>
                ))}
              </div>
              {xMode==="id"&&(
                <div style={{display:"flex",gap:8,marginBottom:16}}>
                  <input value={xId} onChange={e=>setXId(e.target.value)} placeholder="Morphism UUID — click ID in Explore tab"
                    style={{...inputSt,flex:1,fontFamily:mono}} onKeyDown={e=>e.key==="Enter"&&doExplain()}/>
                  <button onClick={doExplain} disabled={xLoading} style={btnSt()}>{xLoading?"…":"Explain"}</button>
                </div>
              )}
              {xMode==="path"&&(
                <div style={{display:"flex",gap:8,marginBottom:16,flexWrap:"wrap"}}>
                  <select value={xDom} onChange={e=>setXDom(e.target.value)} style={{...inputSt,width:180}}>
                    <option value="">Domain...</option>
                    {domains.map(d=><option key={d.id} value={d.name}>{d.name}</option>)}
                  </select>
                  <input value={xSrc} onChange={e=>setXSrc(e.target.value)} placeholder="Source concept" style={{...inputSt,flex:1}}/>
                  <span style={{color:C.blue,fontSize:16,padding:"7px 0"}}>→</span>
                  <input value={xTgt} onChange={e=>setXTgt(e.target.value)} placeholder="Target concept" style={{...inputSt,flex:1}}/>
                  <button onClick={doExplain} disabled={xLoading} style={btnSt()}>{xLoading?"…":"Explain"}</button>
                </div>
              )}
              <div style={{display:"flex",gap:16,marginBottom:12,fontSize:9,fontFamily:mono,color:C.muted}}>
                <span><span style={{color:C.teal}}>teal</span>=axiom</span>
                <span><span style={{color:C.purple}}>purple</span>=derived</span>
                <span><span style={{color:C.green}}>⊕</span> supports</span>
                <span><span style={{color:C.red}}>⊖</span> contradicts</span>
                <span>▸ click node to expand premises</span>
              </div>
              {xRes?.type==="morphism"&&(
                <div style={cardSt()}><ProofNode node={xRes.data} depth={0}/></div>
              )}
              {xRes?.type==="path"&&(
                <div>
                  {!xRes.data?.explanations?.length&&<div style={{color:C.muted,fontSize:11}}>No morphism found for that path.</div>}
                  {xRes.data?.explanations?.map((node,i)=>(
                    <div key={i} style={cardSt({marginBottom:8})}><ProofNode node={node} depth={0}/></div>
                  ))}
                </div>
              )}
              {xRes?.data?.error&&<div style={cardSt({color:C.red})}>{xRes.data.error}</div>}
            </div>
          )}

          {/* ── BELIEF ── */}
          {tab==="belief"&&(
            <div>
              <h2 style={{fontSize:15,marginBottom:4}}>Belief Revision</h2>
              <p style={{fontSize:11,color:C.muted,marginBottom:16}}>Add evidence to a morphism and watch truth values propagate through the derivation graph.</p>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:14}}>
                <div>
                  <div style={hdSt({display:"block",marginBottom:4})}>Morphism ID</div>
                  <input value={bMid} onChange={e=>setBMid(e.target.value)} placeholder="UUID — click ID in Explore tab"
                    style={{...inputSt,width:"100%",fontFamily:mono,boxSizing:"border-box"}}/>
                </div>
                <div>
                  <div style={hdSt({display:"block",marginBottom:4})}>Evidence Label</div>
                  <input value={bLabel} onChange={e=>setBLabel(e.target.value)} placeholder="e.g. experiment_A"
                    style={{...inputSt,width:"100%",boxSizing:"border-box"}}/>
                </div>
                <div>
                  <div style={hdSt({display:"block",marginBottom:4})}>Direction</div>
                  <select value={bDir} onChange={e=>setBDir(e.target.value)} style={{...inputSt,width:"100%"}}>
                    <option value="contradicts">⊖ contradicts (weakens)</option>
                    <option value="supports">⊕ supports (strengthens)</option>
                  </select>
                </div>
                <div>
                  <div style={hdSt({display:"block",marginBottom:4})}>Strength (0–1)</div>
                  <input type="number" min="0" max="1" step="0.05" value={bStr} onChange={e=>setBStr(e.target.value)}
                    style={{...inputSt,width:"100%",boxSizing:"border-box"}}/>
                </div>
              </div>
              <button onClick={doBelief} disabled={bLoading||!bMid||!bLabel}
                style={{...btnSt(bDir==="contradicts"?C.red:C.green,bDir==="contradicts"?C.redDim:C.greenDim),marginBottom:16}}>
                {bLoading?"Updating…":`Apply ${bDir==="contradicts"?"⊖":"⊕"} Evidence`}
              </button>
              {bRes&&!bRes.error&&(
                <div>
                  {bRes.morphism&&(
                    <div style={cardSt({marginBottom:12})}>
                      <div style={hdSt()}>Updated morphism</div>
                      <div style={{display:"flex",gap:10,alignItems:"center",fontSize:11,fontFamily:mono,flexWrap:"wrap"}}>
                        <span style={{color:C.blue}}>{bRes.morphism.source_label}</span>
                        <span style={{color:C.muted}}>→</span>
                        <span style={{color:C.amber}}>{bRes.morphism.target_label}</span>
                        <span>{bRes.morphism.label}</span>
                        <TruthBadge degree={bRes.morphism.truth_degree} modality={bRes.morphism.truth_modality}/>
                      </div>
                    </div>
                  )}
                  <div style={cardSt()}><BeliefDiff changes={bRes.propagated_changes}/></div>
                </div>
              )}
              {bRes?.error&&<div style={cardSt({color:C.red})}>{bRes.error}</div>}
            </div>
          )}

          {/* ── PROOF SYSTEM ── */}
          {tab==="proof"&&(
            <div>
              <h2 style={{fontSize:15,marginBottom:4}}>Proof System ⊢</h2>
              <p style={{fontSize:11,color:C.muted,marginBottom:14}}>Check derivations, normalize proof terms, trace dependents, and extract categorical common cores.</p>

              {/* Mode selector */}
              <div style={{display:"flex",gap:0,marginBottom:16,background:C.bg2,borderRadius:6,padding:3,width:"fit-content",flexWrap:"wrap"}}>
                {[["check","Check Proof"],["normalize","Normalize"],["dependents","Dependents"],["extract","Extract Core"],["audit","Audit Domain"]].map(([m,l])=>(
                  <button key={m} onClick={()=>{setPrMode(m);setPrRes(null);}} style={{
                    background:prMode===m?C.bg3:"transparent",border:"none",
                    color:prMode===m?C.text:C.muted,padding:"5px 12px",
                    borderRadius:4,cursor:"pointer",fontSize:11,fontFamily:sans,fontWeight:prMode===m?600:400,
                  }}>{l}</button>
                ))}
              </div>

              {/* check / normalize / dependents: morphism ID input */}
              {["check","normalize","dependents"].includes(prMode)&&(
                <div style={{display:"flex",gap:8,alignItems:"center",marginBottom:14,flexWrap:"wrap"}}>
                  <input value={prMid} onChange={e=>setPrMid(e.target.value)}
                    placeholder="Morphism UUID — click ID in Explore tab"
                    style={{...inputSt,flex:1,fontFamily:mono}}
                    onKeyDown={e=>e.key==="Enter"&&doProof()}/>
                  {prMode==="dependents"&&(
                    <label style={{fontSize:10,color:C.muted,display:"flex",alignItems:"center",gap:4,cursor:"pointer"}}>
                      <input type="checkbox" checked={prDepRec} onChange={e=>setPrDepRec(e.target.checked)}/>
                      recursive (full closure)
                    </label>
                  )}
                  <button onClick={doProof} disabled={prLoading} style={btnSt()}>
                    {prLoading?"…":prMode==="check"?"Verify":prMode==="normalize"?"Normalize":prMode==="dependents"?"Trace":prMode==="audit"?"Audit":"Extract"}
                  </button>
                </div>
              )}

              {/* extract: domain + map input */}
              {prMode==="extract"&&(
                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:14}}>
                  <div>
                    <div style={hdSt({display:"block",marginBottom:4})}>Source domain</div>
                    <select value={prESrc} onChange={e=>setPrESrc(e.target.value)} style={{...inputSt,width:"100%"}}>
                      <option value="">Select...</option>
                      {domains.map(d=><option key={d.id} value={d.name}>{d.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <div style={hdSt({display:"block",marginBottom:4})}>Target domain</div>
                    <select value={prETgt} onChange={e=>setPrETgt(e.target.value)} style={{...inputSt,width:"100%"}}>
                      <option value="">Select...</option>
                      {domains.map(d=><option key={d.id} value={d.name}>{d.name}</option>)}
                    </select>
                  </div>
                  <div style={{gridColumn:"1/-1"}}>
                    <div style={hdSt({display:"block",marginBottom:4})}>Object map (JSON) — from Search or Pipeline result</div>
                    <textarea value={prEMap} onChange={e=>setPrEMap(e.target.value)}
                      placeholder={'{"source_obj": "target_obj", ...}'}
                      style={{...inputSt,width:"100%",height:80,resize:"vertical",fontFamily:mono,boxSizing:"border-box"}}/>
                  </div>
                  <div>
                    <div style={hdSt({display:"block",marginBottom:4})}>New domain name (optional)</div>
                    <input value={prEName} onChange={e=>setPrEName(e.target.value)}
                      placeholder="auto-named if empty"
                      style={{...inputSt,width:"100%",boxSizing:"border-box"}}/>
                  </div>
                  <div style={{display:"flex",alignItems:"flex-end"}}>
                    <button onClick={doProof} disabled={prLoading||!prESrc||!prETgt} style={btnSt(C.teal,C.tealDim)}>
                      {prLoading?"Extracting…":"Extract Common Core"}
                    </button>
                  </div>
                </div>
              )}

              {/* audit: domain selector */}
              {prMode==="audit"&&(
                <div style={{display:"flex",gap:8,marginBottom:14}}>
                  <select value={prAuditDom} onChange={e=>setPrAuditDom(e.target.value)} style={{...inputSt,flex:1}}>
                    <option value="">Select domain to audit...</option>
                    {domains.map(d=><option key={d.id} value={d.name}>{d.name}</option>)}
                  </select>
                  <button onClick={doProof} disabled={prLoading||!prAuditDom} style={btnSt()}>
                    {prLoading?"Auditing…":"Audit Proofs"}
                  </button>
                </div>
              )}

              {/* Results */}
              {prRes&&!prRes.error&&(()=>{
                // check_proof result
                if ("valid" in prRes && "rule" in prRes) {
                  const ok = prRes.valid;
                  return (
                    <div style={cardSt({borderLeft:`3px solid ${ok?C.green:C.red}`})}>
                      <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:10}}>
                        <span style={{fontSize:18,color:ok?C.green:C.red}}>{ok?"✓":"✗"}</span>
                        <span style={{fontSize:13,fontWeight:700}}>{ok?"Valid proof":"Invalid proof"}</span>
                        <span style={{fontSize:10,color:C.muted,fontFamily:mono}}>{prRes.rule}</span>
                        <span style={{fontSize:10,color:C.muted}}>{prRes.premises} premise{prRes.premises!==1?"s":""}</span>
                        {prRes.conclusion&&<span style={{fontSize:10,color:C.teal,fontFamily:mono}}>{prRes.conclusion}</span>}
                        {prRes.truth_degree!=null&&<TruthBadge degree={prRes.truth_degree} modality="ACTUAL"/>}
                      </div>
                      {prRes.errors?.length>0&&(
                        <div>
                          {prRes.errors.map((e,i)=>(
                            <div key={i} style={{fontSize:11,color:C.red,padding:"2px 0",fontFamily:mono}}>⚠ {e}</div>
                          ))}
                        </div>
                      )}
                      {ok&&<div style={{fontSize:10,color:C.muted}}>All premises exist and chain is structurally valid.</div>}
                    </div>
                  );
                }
                // normalize result
                if ("canonical" in prRes) {
                  return (
                    <div style={cardSt()}>
                      <div style={hdSt()}>Canonical Proof Term (beta-normal form)</div>
                      <pre style={{fontFamily:mono,fontSize:11,color:C.teal,whiteSpace:"pre-wrap",wordBreak:"break-all",margin:0}}>
                        {prRes.canonical}
                      </pre>
                      <div style={{fontSize:10,color:C.muted,marginTop:8}}>
                        This form is associativity-invariant — two derivations of the same conclusion via different groupings produce the same string. Suitable as a proof deduplication key.
                      </div>
                    </div>
                  );
                }
                // dependents result
                if ("dependents" in prRes) {
                  return (
                    <div style={cardSt()}>
                      <div style={{display:"flex",justifyContent:"space-between",marginBottom:10}}>
                        <div>
                          <span style={{fontFamily:mono,color:C.blue}}>{prRes.source}</span>
                          <span style={{color:C.muted,margin:"0 4px"}}>→</span>
                          <span style={{fontFamily:mono,color:C.amber}}>{prRes.target}</span>
                          <span style={{color:C.muted,marginLeft:8,fontSize:10}}>{prRes.morphism_label}</span>
                        </div>
                        <span style={{fontSize:11,color:C.muted}}>{prRes.count} dependent{prRes.count!==1?"s":""}{prRes.recursive?" (recursive)":""}</span>
                      </div>
                      {prRes.dependents.length===0&&<div style={{color:C.muted,fontSize:11}}>No morphisms depend on this one.</div>}
                      {prRes.dependents.map((d,i)=>(
                        <div key={i} style={{display:"flex",alignItems:"center",gap:8,padding:"4px 0",
                          borderBottom:`1px solid ${C.border}`,fontSize:10,fontFamily:mono,flexWrap:"wrap"}}>
                          <span style={{color:C.purple,fontSize:8}}>derived</span>
                          <span style={{color:C.blue}}>{d.source_label}</span>
                          <span style={{color:C.muted}}>→</span>
                          <span style={{color:C.amber}}>{d.target_label}</span>
                          <span style={{flex:1,color:C.text}}>{d.label}</span>
                          <TruthBadge degree={d.truth_degree} modality={d.truth_modality}/>
                          <span title="Click to check this morphism's proof"
                            onClick={()=>{setPrMid(d.id);setPrMode("check");setPrRes(null);}}
                            style={{fontSize:8,color:C.dim,cursor:"pointer",fontFamily:mono,textDecoration:"underline dotted"}}>
                            {d.id?.slice(0,8)}…
                          </span>
                        </div>
                      ))}
                    </div>
                  );
                }
                // extract_common_core result
                if ("extracted" in prRes) {
                  return (
                    <div style={cardSt({borderLeft:`3px solid ${prRes.extracted?C.teal:C.muted}`})}>
                      {prRes.extracted?(
                        <>
                          <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:12}}>
                            <span style={{fontSize:18,color:C.teal}}>⊗</span>
                            <span style={{fontSize:13,fontWeight:700}}>Core extracted: <span style={{color:C.teal}}>{prRes.core_domain_name}</span></span>
                            <span style={{fontSize:11,color:C.muted}}>{prRes.invariant_morphisms} invariant morphism{prRes.invariant_morphisms!==1?"s":""}</span>
                          </div>
                          <div style={{fontSize:10,color:C.muted,marginBottom:10}}>{prRes.description}</div>
                          <div style={hdSt()}>Preserved structure</div>
                          {prRes.morphisms.map((m,i)=>(
                            <div key={i} style={{display:"flex",gap:8,padding:"3px 0",fontSize:10,fontFamily:mono,
                              borderBottom:`1px solid ${C.border}`}}>
                              <span style={{color:C.blue,minWidth:100}}>{m.source}</span>
                              <span style={{color:C.muted}}>→</span>
                              <span style={{color:C.amber,minWidth:100}}>{m.target}</span>
                              <span style={{color:C.text,flex:1}}>{m.label}</span>
                              <TruthBadge degree={m.truth_degree} modality="PROB"/>
                            </div>
                          ))}
                          <div style={{fontSize:10,color:C.muted,marginTop:8}}>{prRes.note}</div>
                        </>
                      ):(
                        <div style={{color:C.muted}}>{prRes.message}</div>
                      )}
                    </div>
                  );
                }
                // audit result
                if ("proof_integrity" in prRes) {
                  const pct = (prRes.proof_integrity*100).toFixed(0);
                  const col = prRes.proof_integrity > 0.9 ? C.green : prRes.proof_integrity > 0.7 ? C.amber : C.red;
                  return (
                    <div>
                      <div style={cardSt({display:"flex",gap:20,alignItems:"center",marginBottom:12,flexWrap:"wrap"})}>
                        <span style={{fontSize:28,fontWeight:800,color:col,fontFamily:mono}}>{pct}%</span>
                        <div>
                          <div style={{fontSize:11}}>Proof integrity · <span style={{color:col}}>{prRes.valid}/{prRes.total_derived}</span> valid</div>
                          <div style={{fontSize:10,color:C.muted}}>{prRes.invalid} invalid derivation{prRes.invalid!==1?"s":""} in {prRes.domain}</div>
                        </div>
                      </div>
                      {prRes.invalid_details?.length>0&&(
                        <div style={cardSt({padding:0,overflow:"hidden"})}>
                          <div style={{padding:"10px 14px",borderBottom:`1px solid ${C.border}`,fontSize:10,color:C.muted,letterSpacing:1,textTransform:"uppercase"}}>Invalid proofs</div>
                          {prRes.invalid_details.map((inv,i)=>(
                            <div key={i} style={{padding:"8px 14px",borderBottom:`1px solid ${C.border}`}}>
                              <div style={{display:"flex",gap:8,marginBottom:4,fontSize:11}}>
                                <span style={{color:C.red}}>✗</span>
                                <span style={{fontFamily:mono}}>{inv.conclusion}</span>
                                <span style={{color:C.muted,fontSize:10}}>{inv.label}</span>
                                <span style={{color:C.muted,fontSize:10,marginLeft:"auto",fontFamily:mono}}>{inv.rule}</span>
                              </div>
                              {inv.errors.map((e,j)=>(
                                <div key={j} style={{fontSize:10,color:C.red,paddingLeft:16,fontFamily:mono}}>⚠ {e}</div>
                              ))}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                }
                return <pre style={{fontSize:10,color:C.muted,whiteSpace:"pre-wrap"}}>{JSON.stringify(prRes,null,2)}</pre>;
              })()}
              {prRes?.error&&<div style={cardSt({color:C.red})}>{prRes.error}</div>}
            </div>
          )}


          {/* ── TOPOLOGY ── */}
          {tab==="topo"&&(
            <TopoTab domains={domains} />
          )}

          {/* ── REPL ── */}
          {tab==="repl"&&(
            <div style={{display:"flex",flexDirection:"column",height:"calc(100vh - 120px)"}}>
              <h2 style={{fontSize:15,marginBottom:6,flexShrink:0}}>Natural Language REPL</h2>
              <div style={{flex:1,background:C.bg0,border:`1px solid ${C.border}`,borderRadius:8,
                padding:12,overflowY:"auto",fontSize:11,marginBottom:8,fontFamily:mono}}>
                {rh.map((e,i)=>(
                  <div key={i} style={{marginBottom:6}}>
                    {e.t==="usr"&&<div><span style={{color:C.blue}}>λ </span><span>{e.x}</span></div>}
                    {e.t==="sys"&&<div style={{color:C.dim,whiteSpace:"pre-wrap"}}>{e.x}</div>}
                    {e.t==="res"&&<div style={{color:C.green,whiteSpace:"pre-wrap",paddingLeft:10,borderLeft:`2px solid ${C.greenDim}`}}>{e.x}</div>}
                    {e.t==="err"&&<div style={{color:C.red,whiteSpace:"pre-wrap"}}>✗ {e.x}</div>}
                  </div>
                ))}
                <div ref={replEnd}/>
              </div>
              <div style={{display:"flex",gap:6,flexShrink:0}}>
                <span style={{color:C.blue,padding:"7px 0",fontSize:14,fontFamily:mono}}>λ</span>
                <input value={ri} onChange={e=>setRi(e.target.value)} onKeyDown={e=>{if(e.key==="Enter")doRepl();}}
                  placeholder="compose grammar · infer grammar · pipeline music math · search celtic → types"
                  style={{...inputSt,flex:1,fontFamily:mono}}/>
                <button onClick={doRepl} style={btnSt()}>Run</button>
              </div>
            </div>
          )}

          {/* ── MEMORY ── */}
          {tab==="memory"&&(
            <div>
              <h2 style={{fontSize:15,marginBottom:12}}>Kernel Memory</h2>
              <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:10,marginBottom:20}}>
                {[["Domains",stats.domains,C.blue],["Morphisms",stats.morphisms,C.purple],
                  ["Derivations",stats.derivations,C.teal],["Evidence",stats.evidence,C.amber],
                  ["Programs",stats.programs,C.green],["Tasks",stats.tasks,C.muted]].map(([l,v,c])=>(
                  <div key={l} style={cardSt({textAlign:"center"})}>
                    <div style={{fontSize:28,fontWeight:800,color:c,fontFamily:mono}}>{v??0}</div>
                    <div style={hdSt({marginBottom:0})}>{l}</div>
                  </div>
                ))}
              </div>
              {programs.length>0&&(
                <div style={cardSt()}>
                  <h3 style={hdSt()}>Registered Programs</h3>
                  {programs.map((p,i)=>(
                    <div key={i} style={{display:"flex",justifyContent:"space-between",alignItems:"center",
                      padding:"7px 0",borderBottom:`1px solid ${C.border}`,fontSize:11,gap:10}}>
                      <span style={{fontFamily:mono}}>{p.name}</span>
                      <span style={{color:C.muted,fontSize:9}}>v{p.version}</span>
                      <span style={{color:C.muted,fontSize:10,flex:1,textAlign:"center"}}>{p.source_domain}→{p.target_domain}</span>
                      <TruthBadge degree={p.score} modality="SCORE"/>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── IMPORT ── */}
          {tab==="import"&&(
            <div>
              <h2 style={{fontSize:15,marginBottom:12}}>Import Datasets</h2>
              <button onClick={async()=>{for(const n of Object.keys(datasets))await doImport(n);}}
                style={{...btnSt(),marginBottom:20}}>
                Import All ({Object.keys(datasets).length})
              </button>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:8}}>
                {Object.entries(datasets).map(([name,info])=>{
                  const loaded=domains.some(d=>d.name===name);
                  return (
                    <div key={name} style={cardSt({borderColor:loaded?C.greenDim:C.border,background:loaded?"#0a1c10":C.bg1})}>
                      <div style={{fontSize:11,marginBottom:4}}>{name}</div>
                      <div style={{fontSize:9,color:C.muted,fontFamily:mono}}>{info.objects} obj · {info.morphisms} morph</div>
                      {loaded
                        ?<span style={{display:"inline-block",marginTop:8,fontSize:9,color:C.green}}>✓ Loaded</span>
                        :<button onClick={()=>doImport(name)} style={{marginTop:8,background:C.bg3,border:`1px solid ${C.border2}`,
                          color:C.text,padding:"3px 10px",borderRadius:3,cursor:"pointer",fontSize:10,fontFamily:sans}}>Import</button>}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
