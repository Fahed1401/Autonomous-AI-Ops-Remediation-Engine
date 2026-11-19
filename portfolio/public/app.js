"use strict";

const $ = (id) => document.getElementById(id);
const state = { data: null, health: null, runbook: null, page: "overview", severity: "All", search: "",
                selected: null, plan: null, approvalToken: null, busy: false };
const labels = {overview:"Overview", incidents:"Incidents",remediation:"Remediation lab",runbooks:"Knowledge base",audit:"Audit trail",health:"System health"};
const escapeHTML = (raw) => String(raw ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const severityClass = (s) => "sev-" + String(s).toLowerCase().replace(/[^a-z]/g, "");
const statusClass = (s) => "status-" + String(s).toLowerCase().replace(/[^a-z]/g, "");
const timeText = (t) => { const d = new Date(t); return Number.isNaN(d.valueOf()) ? "—" : d.toLocaleString(undefined,{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"}); };
const resultText = (x) => escapeHTML(x).slice(0, 2000);

async function api(path, body) {
  if (window.SentinelOpsDemoAPI) return window.SentinelOpsDemoAPI(path, body);
  const opts = { headers: {"Accept": "application/json"}, cache:"no-store" };
  if (body !== undefined) { opts.method="POST"; opts.headers["Content-Type"]="application/json"; opts.body=JSON.stringify(body); }
  const response = await fetch(path, opts);
  let data; try {data = await response.json();} catch {throw new Error("Invalid server response");}
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
function toast(message, error=false) {
  const el = document.createElement("div"); el.className = "toast" + (error?" error":"");
  const x=document.createElement("button");x.textContent="×";x.setAttribute("aria-label","Dismiss notification");x.addEventListener("click",()=>el.remove());
  const t=document.createElement("span");t.textContent=message;el.append(x,t);$("toast-stack").prepend(el);
  while($("toast-stack").children.length > 3) $("toast-stack").lastChild.remove();
}
function setBusy(value) {state.busy=value; ["generate-plan","approve-plan","execute-plan"].forEach(id=>{if($(id)) $(id).disabled=value || (id==="approve-plan"&&(!state.plan||state.approvalToken)) || (id==="execute-plan"&&!state.approvalToken);});}
function badgeSeverity(s) {return `<span class="sev-badge ${severityClass(s)}">${escapeHTML(s)}</span>`;}
function badgeStatus(s) {return `<span class="status-badge ${statusClass(s)}">${escapeHTML(s)}</span>`;}
function changePage(name) {
  if (!labels[name]) return;
  state.page=name;
  document.querySelectorAll(".page").forEach(el=>el.classList.toggle("active",el.id===`page-${name}`));
  document.querySelectorAll(".nav-link").forEach(el=>{const active=el.dataset.page===name;el.classList.toggle("active",active);if(active)el.setAttribute("aria-current","page");else el.removeAttribute("aria-current");});
  $("breadcrumb").textContent=labels[name];
  closeMenu();window.scrollTo({top:0,behavior:"instant"});
  if(name==="runbooks") loadRunbook(); if(name==="health") loadHealth();
}
function closeMenu(){$("sidebar").classList.remove("mobile-open");$("mobile-overlay").classList.add("hidden");}
function incidentRow(item, extended=false) {
  const btn=`<button class="table-arrow" data-detail="${escapeHTML(item.id)}" aria-label="Inspect ${escapeHTML(item.id)}">↗</button>`;
  const main=`<td><span class="item-title">${escapeHTML(item.title)}</span><span class="item-sub">${escapeHTML(item.id)} · ${escapeHTML(item.service)}</span></td>`;
  return `<tr>${main}<td>${badgeSeverity(item.severity)}</td><td><span class="monospace">${escapeHTML(item.resource)}</span></td><td>${badgeStatus(item.status)}</td><td>${escapeHTML(timeText(item.observed))}</td><td>${extended ? `<button class="link-button" data-detail="${escapeHTML(item.id)}">Investigate ↗</button>` : btn}</td></tr>`;
}
function renderOverview() {
  const d=state.data;if(!d)return;
  $("demo-banner").classList.toggle("hidden", !d.demo_notice);
  $("nav-count").textContent=d.summary.active;
  $("env-pill").textContent=d.mode==="demo"?"BROWSER-ONLY DEMO":"LOCALSTACK MODE";
  $("side-mode").textContent=d.mode==="demo"?"STATIC PORTFOLIO DEMO":"LOCALSTACK ENVIRONMENT";
  const ratio=d.summary.total?Math.round(100*d.summary.resolved/d.summary.total):100;
  document.querySelector(".posture-top .small-label").textContent="INCIDENT RESOLUTION INDEX";
  $("posture-score").innerHTML=`${ratio}<span>/ 100</span>`;
  $("posture-fill").style.width=ratio+"%";
  $("posture-copy").textContent=d.summary.active ? `${d.summary.active} incident${d.summary.active===1?"":"s"} still active` : "All tracked incidents resolved";
  $("posture-caption").textContent="Resolved / total · not a risk score";
  const items=[
    {label:"Total incidents",value:d.summary.total,foot:"Tracked in the current environment",cls:"blue",symbol:"◇"},
    {label:"Active alerts",value:d.summary.active,foot:"Require triage or follow-up",cls:"purple",symbol:"⚑"},
    {label:"Critical threats",value:d.summary.critical,foot:"Unresolved critical severity",cls:"red",symbol:"!"},
    {label:"Resolved",value:d.summary.resolved,foot:"Closed incidents",cls:"green",symbol:"✓"}
  ];
  $("stat-grid").innerHTML=items.map(x=>`<div class="stat-card"><div class="stat-head"><span>${escapeHTML(x.label)}</span><span class="stat-icon ${x.cls}">${x.symbol}</span></div><div class="stat-number">${x.value}</div><div class="stat-foot">${escapeHTML(x.foot)}</div></div>`).join("");
  const total=Math.max(d.summary.total,1);
  $("severity-chart").innerHTML=d.severity_distribution.map(x=>`<div class="dist-row"><span class="dist-label">${escapeHTML(x.severity)}</span><div class="dist-track"><span class="${escapeHTML(x.severity.toLowerCase())}-bar"></span></div><span class="dist-count">${x.count}</span></div>`).join("");
  document.querySelectorAll("#severity-chart .dist-track span").forEach((bar,i)=>{bar.style.width=(100*d.severity_distribution[i].count/total)+"%";});
  $("severity-total").textContent=d.summary.total+" incidents";
  $("recent-incidents").innerHTML=d.incidents.slice(0,5).map(x=>incidentRow(x)).join("")||`<tr><td colspan="6">No incidents. Generate an alert to begin.</td></tr>`;
}
function renderIncidents(){
  if(!state.data)return;
  const q=state.search.trim().toLowerCase();
  const incidents=state.data.incidents.filter(x=>(state.severity==="All"||x.severity===state.severity)&&(!q||[x.id,x.title,x.description,x.service,x.resource].join(" ").toLowerCase().includes(q)));
  $("all-incidents").innerHTML=incidents.map(x=>incidentRow(x,true)).join("");
  $("no-incidents").classList.toggle("hidden",incidents.length!==0);
}
function renderAudit(){
  if(!state.data)return;
  $("audit-table").innerHTML=state.data.audit.map(x=>`<tr><td>${escapeHTML(timeText(x.timestamp))}</td><td><span class="item-title">${escapeHTML(x.action.replaceAll("_"," "))}</span><span class="item-sub">${escapeHTML(x.event_id)}</span></td><td class="monospace">${escapeHTML(x.resource)}</td><td>${badgeStatus(x.outcome==="failed"?"Open": x.outcome==="denied"?"Investigating":"Resolved")}</td><td title="${escapeHTML(x.detail)}">${escapeHTML(x.detail)}</td></tr>`).join("")||`<tr><td colspan="5">No audit events.</td></tr>`;
}
function renderTargetSelector(){
  if(!state.data)return;
  const actionable=state.data.incidents.filter(x=>x.actionable&&x.status!=="Resolved");
  if(!actionable.some(x=>x.id===state.selected))state.selected=actionable[0]?.id||null;
  $("target-select").innerHTML=actionable.length?actionable.map(x=>`<option value="${escapeHTML(x.id)}">${escapeHTML(x.id)} · ${escapeHTML(x.title)}</option>`).join(""):`<option value="">No active playbook targets</option>`;
  $("target-select").value=state.selected||"";
  const incident=actionable.find(x=>x.id===state.selected);
  $("target-summary").innerHTML=incident?`<div><strong>Target resource:</strong> <span class="monospace">${escapeHTML(incident.resource)}</span></div><div><strong>Risk:</strong> ${badgeSeverity(incident.severity)} · ${escapeHTML(incident.service)}</div><div>${escapeHTML(incident.description)}</div>`:"No actionable incidents remain. Reset the demo to repeat the workflow.";
  $("generate-plan").disabled=!incident||state.busy;
}
function resetPlan(){state.plan=null;state.approvalToken=null;$("plan-output").innerHTML=`<div class="placeholder-illustration">⌘</div><strong>No plan generated</strong><p>Select an incident and generate a deterministic, runbook-grounded plan.</p>`;$("plan-output").className="placeholder-block";$("approval-hint").textContent="Generate a plan to see the exact phrase.";$("approval-phrase").value="";$("approval-phrase").disabled=true;$("approve-check").checked=false;$("approve-check").disabled=true;$("approve-plan").disabled=true;$("execute-plan").disabled=true;$("execution-result").replaceChildren();$("runbook-source").textContent="Runbook retrieval happens during analysis.";}
function renderPlan(plan){
  $("plan-output").className="plan-detail";
  $("plan-output").innerHTML=`<div class="plan-state"><strong class="plan-operation">${escapeHTML(plan.title)}</strong><span class="tag tag-safe">AWAITING APPROVAL</span></div><p class="plan-info">${escapeHTML(plan.description)}</p><div class="diff-grid"><div class="diff-box before"><span>BEFORE · EXPOSED</span><code>${escapeHTML(plan.change.before)}</code></div><div class="diff-box after"><span>AFTER · SECURE</span><code>${escapeHTML(plan.change.after)}</code></div></div><p class="input-label">PROPOSED EXECUTION SEQUENCE</p><ol class="plan-steps">${plan.steps.map(x=>`<li>${escapeHTML(x)}</li>`).join("")}</ol><p class="plan-source"><strong>Context:</strong> ${escapeHTML(plan.ai_summary.source)} — ${escapeHTML(plan.ai_summary.text)}</p>`;
  $("approval-hint").textContent=plan.approval_phrase;
  $("approval-phrase").disabled=false;$("approve-check").disabled=false;$("approve-plan").disabled=false;
  $("runbook-source").textContent=`${plan.runbook.title} · ${plan.runbook.source}`;
}
function openIncident(id){
  const x=state.data?.incidents.find(x=>x.id===id); if(!x)return;
  $("drawer-content").innerHTML=`<p class="drawer-eyebrow">INCIDENT DETAILS / ${escapeHTML(x.id)}</p><h2 id="drawer-title" class="drawer-heading">${escapeHTML(x.title)}</h2><div>${badgeSeverity(x.severity)} ${badgeStatus(x.status)}</div><p class="drawer-desc">${escapeHTML(x.description)}</p><p class="drawer-section">INCIDENT METADATA</p><div class="drawer-meta"><div><label>RESOURCE</label><strong>${escapeHTML(x.resource)}</strong></div><div><label>SERVICE</label><strong>${escapeHTML(x.service)}</strong></div><div><label>DETECTED</label><strong>${escapeHTML(timeText(x.observed))}</strong></div><div><label>SOURCE</label><strong>${escapeHTML(x.origin)}</strong></div><div><label>OBSERVED IP</label><strong>${escapeHTML(x.ip)}</strong></div><div><label>PLAYBOOK</label><strong>${x.actionable?"SSH ingress remediation":"Manual investigation"}</strong></div></div><p class="drawer-section">RECOMMENDED NEXT ACTION</p><p class="drawer-desc">${x.actionable&&x.status!=="Resolved"?"Generate a scoped remediation proposal, verify the runbook, and explicitly approve the exact rule change.":"This incident has no active automated remediation playbook. Review and triage manually."}</p>${x.actionable&&x.status!=="Resolved"?`<button class="button button-primary button-full" data-remediate="${escapeHTML(x.id)}">Start remediation ↗</button>`:""}`;
  $("drawer-backdrop").classList.remove("hidden");$("detail-drawer").classList.remove("hidden");$("drawer-close").focus();
}
function closeDrawer(){$("drawer-backdrop").classList.add("hidden");$("detail-drawer").classList.add("hidden");}
async function loadOverview(){
  try {state.data=await api("/api/overview");renderOverview();renderIncidents();renderAudit();renderTargetSelector();}
  catch(e){toast(`Dashboard is unavailable: ${e.message}`,true);}
}
async function loadRunbook(){
  try{state.runbook=await api("/api/runbooks");$("kb-title").textContent=state.runbook.title;$("kb-source").textContent=state.runbook.source;
    $("kb-mode").textContent=state.runbook.mode==="rag"?"CHROMADB RAG":state.runbook.mode==="fallback"?"LOCAL FALLBACK":"UNAVAILABLE";
    $("kb-body").textContent=state.runbook.body||"No SOP found. Add company_docs/SOP_SentinelOps_Demo.md.";}
  catch(e){toast(e.message,true);}
}
async function loadHealth(){
  try{state.health=await api("/api/health");const items=[
    ["Control plane",state.health.api,"Runs entirely in this browser"],["Environment",state.health.mode,"No production AWS credentials"],
    ["Approval gate",state.health.approval_gate,"Simulated one-use approvals"],["AWS production",state.health.aws_production,"No cloud backend exposed"],
    ["Model inference",state.health.llm,"Live inference is disabled here"],["Runbook retrieval",state.health.retrieval,"Bundled example Markdown SOP"]];
    $("health-grid").innerHTML=items.map(([name,val,help])=>`<div class="health-card"><span class="health-label">${escapeHTML(name)}</span><strong><span class="health-icon"></span>${escapeHTML(val)}</strong><small>${escapeHTML(help)}</small></div>`).join("");
    $("reset-demo").disabled=state.health.mode!=="demo";
  }catch(e){toast(e.message,true);}
}
async function generatePlan(){
  if(state.busy||!state.selected)return;
  resetPlan();setBusy(true);
  try {const plan=await api("/api/analyze",{incident_id:state.selected});state.plan=plan;renderPlan(plan);await loadOverview();toast("A new read-only remediation plan is ready for review.");}
  catch(e){toast(e.message,true);}
  finally{setBusy(false);}
}
async function authorizePlan(){
  if(state.busy||!state.plan)return;
  setBusy(true);
  try{const result=await api("/api/approve",{plan_id:state.plan.id,confirmation:$("approval-phrase").value,acknowledged:$("approve-check").checked});
    state.approvalToken=result.approval_token;$("execute-plan").disabled=false;$("approve-plan").disabled=true;
    $("execution-result").innerHTML=`<div class="result-notice">Approval granted for one execution. Token expires in ${result.expires_in_seconds} seconds.</div>`;
    await loadOverview();toast("Plan-specific approval issued. No change has been executed yet.");}
  catch(e){toast(e.message,true);$("execution-result").innerHTML=`<div class="result-notice error">${resultText(e.message)}</div>`;}
  finally{setBusy(false);}
}
async function executePlan(){
  if(state.busy||!state.plan||!state.approvalToken)return;
  const token=state.approvalToken;state.approvalToken=null;setBusy(true);
  try {const result=await api("/api/execute",{plan_id:state.plan.id,approval_token:token});
    $("execution-result").innerHTML=`<div class="result-notice"><strong>${result.simulation?"Simulated":"LocalStack"} remediation ${result.verified?"verified":"not verified"}.</strong><div>${resultText(result.message)}</div></div>`;
    $("plan-output").querySelector(".tag")?.replaceChildren(document.createTextNode("VERIFIED"));
    await loadOverview();toast(result.message);}
  catch(e){$("execution-result").innerHTML=`<div class="result-notice error">${resultText(e.message)}</div>`;toast(e.message,true);await loadOverview();}
  finally{setBusy(false);$("approve-plan").disabled=true;$("execute-plan").disabled=true;}
}
function downloadAudit(){if(!state.data)return;const rows=[["timestamp","event_id","action","resource","outcome","detail"],...state.data.audit.map(x=>[x.timestamp,x.event_id,x.action,x.resource,x.outcome,x.detail])];
  const csv=rows.map(x=>x.map(v=>'"'+String(v??"").replaceAll('"','""')+'"').join(",")).join("\r\n");
  const blob=new Blob([csv],{type:"text/csv;charset=utf-8"});const url=URL.createObjectURL(blob);const link=document.createElement("a");link.href=url;link.download="sentinelops-audit.csv";link.click();URL.revokeObjectURL(url);toast("Audit CSV exported.");}
function bindEvents(){
  document.querySelectorAll("[data-page]").forEach(el=>el.addEventListener("click",()=>changePage(el.dataset.page)));
  document.querySelectorAll("[data-action=go-remediation]").forEach(el=>el.addEventListener("click",()=>changePage("remediation")));
  document.addEventListener("click",e=>{const detail=e.target.closest("[data-detail]");if(detail)openIncident(detail.dataset.detail);
    const rem=e.target.closest("[data-remediate]");if(rem){state.selected=rem.dataset.remediate;resetPlan();renderTargetSelector();closeDrawer();changePage("remediation");}});
  $("severity-filters").addEventListener("click",e=>{const t=e.target.closest("[data-severity]");if(!t)return;state.severity=t.dataset.severity;document.querySelectorAll(".filter-pill").forEach(b=>b.classList.toggle("selected",b===t));renderIncidents();});
  $("incident-search").addEventListener("input",e=>{state.search=e.target.value;renderIncidents();});
  $("target-select").addEventListener("change",e=>{state.selected=e.target.value;resetPlan();renderTargetSelector();});
  $("generate-plan").addEventListener("click",generatePlan);$("approve-plan").addEventListener("click",authorizePlan);$("execute-plan").addEventListener("click",executePlan);
  ["refresh-btn","refresh-incidents"].forEach(id=>$(id).addEventListener("click",()=>{loadOverview();toast("Incident data refreshed.");}));
  $("reload-runbook").addEventListener("click",loadRunbook);$("health-refresh").addEventListener("click",loadHealth);
  ["export-audit","export-report"].forEach(id=>$(id).addEventListener("click",downloadAudit));
  $("reset-demo").addEventListener("click",async()=>{try{await api("/api/reset",{});resetPlan();await loadOverview();toast("Simulation restored. Prior approvals invalidated.");}catch(e){toast(e.message,true);}});
  $("about-mode").addEventListener("click",()=>changePage("health"));
  $("drawer-close").addEventListener("click",closeDrawer);$("drawer-backdrop").addEventListener("click",closeDrawer);
  document.addEventListener("keydown",e=>{if(e.key==="Escape")closeDrawer();});
  $("menu-toggle").addEventListener("click",()=>{$("sidebar").classList.add("mobile-open");$("mobile-overlay").classList.remove("hidden");});
  $("mobile-overlay").addEventListener("click",closeMenu);
  $("theme-toggle").addEventListener("click",()=>{const next=document.documentElement.dataset.theme==="dark"?"light":"dark";document.documentElement.dataset.theme=next;try{localStorage.setItem("sentinelops-theme",next);}catch{}});
}
async function init(){
  try {const stored=localStorage.getItem("sentinelops-theme");if(["light","dark"].includes(stored))document.documentElement.dataset.theme=stored;}catch{}
  bindEvents();resetPlan();await loadOverview();
}
init();
