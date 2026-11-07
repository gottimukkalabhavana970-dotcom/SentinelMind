let alerts = [], selectedId = null, chart = null;
const $ = id => document.getElementById(id);
async function api(path, options={}) {
  const res = await fetch(path, {headers:{"Content-Type":"application/json"}, ...options});
  if (!res.ok) throw new Error((await res.json()).detail || "Request failed");
  return res.json();
}
function esc(s=""){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
async function load(){
  try{
    [alerts] = await Promise.all([api("/api/alerts")]);
    if(!selectedId || !alerts.some(a=>a.id===selectedId)) selectedId=alerts[0]?.id||null;
    render(); await loadMetrics(); await loadPatterns();
  }catch(e){$("alertList").innerHTML=`<p class="muted">Could not load API: ${esc(e.message)}. Is the server running?</p>`;}
}
function render(){
  $("alertCount").textContent=`${alerts.length} alerts`;
  $("alertList").innerHTML=alerts.map(a=>`<div class="alert ${a.id===selectedId?"selected":""}" data-id="${esc(a.id)}">
    <div class="alert-top"><span class="alert-name">${esc(a.rule_name)}</span><span class="severity ${esc(a.severity)}">${esc(a.severity)}</span></div>
    <div class="alert-meta">${esc(a.id)} · ${esc(a.host)} · ${esc(a.source_ip)}</div>
    <div class="alert-meta">${a.analyst_verdict?`✓ ${esc(a.analyst_verdict)}`:"● Pending review"}</div></div>`).join("");
  document.querySelectorAll(".alert").forEach(el=>el.addEventListener("click",()=>{selectedId=el.dataset.id;render();}));
  renderDetail();
}
function renderDetail(){
  const a=alerts.find(x=>x.id===selectedId);
  if(!a){$("detail").innerHTML='<div class="empty">No alerts available.</div>';return;}
  const r=a.analysis;
  $("detail").innerHTML=`<div class="recommend"><div><div class="small">RECOMMENDATION</div><div class="verdict">${esc(r?.verdict||"Not analyzed")}</div></div><div class="confidence">${r?`${r.confidence}% heuristic confidence`:"—"}</div></div>
    <div class="explanation">${esc(r?.explanation||"Submit this alert for triage using the API or reset demo.")}</div>
    <div class="factors"><b>Alert evidence</b><br>Rule: ${esc(a.rule_name)}<br>Severity: ${esc(a.severity)}<br>Source IP: ${esc(a.source_ip)}<br>Host / user: ${esc(a.host)} / ${esc(a.user)}<br>Details: ${esc(a.details)}</div>
    <div class="memory-box"><h3>HINDSIGHT RECALL · ${esc(r?.memory_mode||"Memory not queried")}</h3>${(r?.memories||[]).length?(r.memories||[]).map(m=>`<div class="memory-item">${esc(m.text)}</div>`).join(""):"No similar prior verdicts retrieved for this alert."}<p class="small">Memories are supporting evidence, not proof of safety.</p></div>`;
  $("feedback").innerHTML=a.analyst_verdict?`<p>Recorded verdict: <b>${esc(a.analyst_verdict)}</b></p><p class="muted">${esc(a.analyst_reason||"")}</p>`:
  `<textarea id="reason" placeholder="Why are you choosing this verdict? Add the evidence you checked."></textarea><div class="actions">
    <button onclick="submitVerdict('Likely benign')">Likely benign</button>
    <button class="btn-review" onclick="submitVerdict('Needs review')">Needs review</button>
    <button class="btn-escalate" onclick="submitVerdict('Escalate')">Escalate</button></div>`;
}
async function submitVerdict(verdict){
  const reason=$("reason")?.value||"Reviewed during demo";
  try{await api("/api/verdict",{method:"POST",body:JSON.stringify({alert_id:selectedId,verdict,reason})});await load();}
  catch(e){alert(e.message);}
}
async function loadMetrics(){
  const m=await api("/api/metrics");
  $("total").textContent=m.total_alerts;$("reviewed").textContent=m.reviewed_alerts;
  $("pending").textContent=m.pending_alerts;$("rate").textContent=m.review_rate+"%";
  const labels=alerts.slice().reverse().map((a,i)=>a.analyst_verdict?i+1:null).filter(x=>x!==null);
  const points=alerts.slice().reverse().map((a,i)=>a.analyst_verdict?i+1:null);
  const ctx=$("learningChart");
  if(chart)chart.destroy();
  chart=new Chart(ctx,{type:"line",data:{labels:alerts.slice().reverse().map((a,i)=>i+1),datasets:[{label:"Reviewed alert",data:points,spanGaps:false,tension:.25,borderWidth:2}]},
    options:{plugins:{legend:{labels:{color:"#91a3bc"}}},scales:{x:{ticks:{color:"#91a3bc"},grid:{color:"#263650"},title:{display:true,text:"Alert sequence",color:"#91a3bc"}},y:{min:0,max:alerts.length,ticks:{color:"#91a3bc"},grid:{color:"#263650"},title:{display:true,text:"Review marker",color:"#91a3bc"}}}}});
}
async function loadPatterns(){try{const p=await api("/api/patterns");$("patterns").textContent=`Memory mode: ${p.mode}\n\n${p.summary}`;}catch(e){$("patterns").textContent=e.message;}}
$("resetBtn").addEventListener("click",async()=>{if(confirm("Reset the live demo alert list? Saved memory will not be deleted.")){await api("/api/demo/reset",{method:"POST"});selectedId=null;load();}});
load();
