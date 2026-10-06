(() => {
"use strict";
const dataURL = new URL("positions.json", document.currentScript.src);
const esc = v => String(v).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const color = r => r.party === "DEM" ? "#2266a5" : "#ba453d";
const x = v => 35 + (v + 1.2) / 2.4 * 630;
const fmt = v => Number(v).toFixed(3);
async function init(root) {
try {
 const response=await fetch(dataURL); if(!response.ok) throw Error("Voting data unavailable");
 const data=await response.json(), compact=root.dataset.compact==="true";
 let period="combined", selected=new URLSearchParams(location.search).get("candidate") || root.dataset.candidate || "John Burke", query="";
 root.innerHTML='<div class="vp-controls"><label>Reporting period<select data-period><option value="combined">2025–2026 combined</option><option value="2025">2025 only</option><option value="2026">2026 only</option></select></label>'+(compact?'':'<label>Highlight a senator<input type="search" data-search placeholder="Search by name" autocomplete="off"></label>')+'</div><div class="vp-key"><span><i class="vp-dot dem"></i>Democrat</span><span><i class="vp-dot rep"></i>Republican</span></div><p class="vp-count" data-count aria-live="polite"></p><div data-chart></div><div class="vp-selected" data-selected aria-live="polite"></div>'+(compact?'<a class="vp-action" data-explore>Explore all senators →</a>':'<div class="vp-table-wrap"><table class="vp-table"><caption class="vp-note">Select a name to highlight its position. Light lines show ±1 bootstrap standard error for the combined fit.</caption><thead><tr><th scope="col">Senator · district</th><th scope="col">Position (−1 to +1)</th><th scope="col">Estimate</th><th scope="col">Votes used</th></tr></thead><tbody data-rows></tbody></table></div>')+'<p class="vp-note">Vertical spacing separates overlapping dots; the model has one dimension. Experimental voting-pattern measure. Higher is not better. Annual models are separately scaled; changes between periods are not calibrated ideological movement. Coverage ends June 11, 2026.</p>';
 function render(){
 const rows=data.periods[period].slice().sort((a,b)=>a.position-b.position||a.name.localeCompare(b.name));
 const matches=r=>!query||r.name.toLowerCase().includes(query), chosen=rows.find(r=>r.name===selected);
 root.querySelector("[data-count]").textContent=rows.length+" senators · "+data.period_counts[period]+" divided votes"+(query?" · "+rows.filter(matches).length+" matching names highlighted":"");
 let svg='<svg class="vp-chart" viewBox="0 0 700 175" role="group" aria-label="Senate voting positions. Selected senator: '+esc(selected)+'"><line x1="35" x2="665" y1="128" y2="128" stroke="#a8bfdf"/>';
 for(const tick of [-1,-.5,0,.5,1]) svg+='<line x1="'+x(tick)+'" x2="'+x(tick)+'" y1="42" y2="132" stroke="#dae4ef"/><text x="'+x(tick)+'" y="153" text-anchor="middle">'+tick+'</text>';
 rows.filter(r=>r.name!==selected).concat(rows.filter(r=>r.name===selected)).forEach((r,i)=>{const active=r.name===selected;svg+='<circle class="vp-point" data-name="'+esc(r.name)+'" cx="'+x(r.position)+'" cy="'+(55+(i%3)*23)+'" r="'+(active?8:5)+'" fill="'+color(r)+'" opacity="'+(matches(r)?(active?1:.55):.12)+'" stroke="'+(active?"#805a16":"#fff")+'" stroke-width="'+(active?3:1)+'" role="button" tabindex="0" aria-label="Select '+esc(r.name)+', position '+fmt(r.position)+'"><title>'+esc(r.name)+' · '+fmt(r.position)+'</title></circle>';});
 root.querySelector("[data-chart]").innerHTML=svg+'</svg><div class="vp-axis-caption"><span>Negative end</span><span>Positive end · de la Cruz anchor</span></div>';
 root.querySelector("[data-selected]").innerHTML=chosen?'<h3>'+esc(chosen.name)+' · Senate District '+chosen.district+'</h3><p><strong>Voting position: '+fmt(chosen.position)+'</strong> · '+chosen.recorded_votes_used+' recorded votes used</p><p>'+(chosen.bootstrap_standard_error===null?'Standard errors are not available for this annual fit.':'Bootstrap standard error: '+fmt(chosen.bootstrap_standard_error)+'. Light lines show one standard error, not a 95% confidence interval.')+'</p><p>This compares voting patterns within the Senate. It does not grade legislative performance.</p>':'<h3>'+esc(selected)+'</h3><p>No estimate is available for this senator in the selected period. Famiglietti took office after the 2025 sittings in this dataset; missing votes are not assigned as Nay.</p>';
 if(compact) root.querySelector("[data-explore]").href=new URL("index.html", dataURL).href+"?candidate="+encodeURIComponent(selected);
 else root.querySelector("[data-rows]").innerHTML=rows.map(r=>{
 const se=r.bootstrap_standard_error,bar=se===null?"":'<line x1="'+x(r.position-se)+'" x2="'+x(r.position+se)+'" y1="14" y2="14" stroke="'+color(r)+'" opacity=".35" stroke-width="5"/>';
 return '<tr class="'+(r.name===selected?"is-selected ":"")+(!matches(r)?"is-muted":"")+'"><th scope="row"><button class="vp-select" data-name="'+esc(r.name)+'" aria-pressed="'+(r.name===selected)+'">'+esc(r.name)+' · '+r.district+'</button></th><td><svg class="vp-row-axis" viewBox="0 0 700 28" aria-hidden="true"><line x1="'+x(-1)+'" x2="'+x(1)+'" y1="14" y2="14" stroke="#dae4ef"/>'+bar+'<circle cx="'+x(r.position)+'" cy="14" r="6" fill="'+color(r)+'"/></svg></td><td>'+fmt(r.position)+'</td><td>'+r.recorded_votes_used+'</td></tr>';
 }).join("");
 }
 root.querySelector("[data-period]").addEventListener("change",e=>{period=e.target.value;render();});
 root.querySelector("[data-search]")?.addEventListener("input",e=>{query=e.target.value.trim().toLowerCase();render();});
 function select(e){const t=e.target.closest("[data-name]");if(!t)return;selected=t.dataset.name;const button=t.tagName.toLowerCase()==="button";render();if(button)[...root.querySelectorAll("button[data-name]")].find(b=>b.dataset.name===selected)?.focus();}
 root.addEventListener("click",select);
 root.addEventListener("keydown",e=>{if(e.target.matches("circle[data-name]")&&(e.key==="Enter"||e.key===" ")){e.preventDefault();select(e);[...root.querySelectorAll("circle[data-name]")].find(c=>c.dataset.name===selected)?.focus();}});
 render();
}catch(e){root.innerHTML='<p class="vp-error" role="alert">The voting-pattern preview could not load. Please refresh this page or try again later.</p>';console.error(e);}
}
document.querySelectorAll("[data-voting-widget]").forEach(init);
})();
