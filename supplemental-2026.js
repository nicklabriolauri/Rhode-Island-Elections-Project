(() => {
  const path=(location.pathname||'').toLowerCase();
  const isBallot=path.endsWith('/ballot.html')||path.endsWith('ballot.html');
  const isPrimaryResults=path.endsWith('/primary-results.html')||path.endsWith('primary-results.html');
  const norm=s=>String(s||'').toLowerCase().replace(/[^a-z0-9 ]+/g,' ').replace(/\b(jr|sr|ii|iii|iv)\b/g,' ').replace(/\s+/g,' ').trim();
  const style=document.createElement('style');
  style.textContent=`
    .riep-search-status{display:inline-flex;margin-top:8px;padding:5px 8px;border-radius:999px;font:800 10px/1.1 'Instrument Sans',system-ui,sans-serif;letter-spacing:.04em;text-transform:uppercase}
    .riep-search-status.lost{background:#eceff3;color:#4b5563;border:1px solid #cbd2da}.riep-search-status.rep{background:#fff0f1;color:#b83d45;border:1px solid #f0c7cb}.riep-search-status.dem{background:#edf4ff;color:#215ed8;border:1px solid #cbdcf8}.riep-search-status.ind{background:#f1f3f5;color:#505a67;border:1px solid #cfd5dc}.riep-search-status.unopposed{background:#eef8f5;color:#126b5f;border:1px solid #c8e6dd}.riep-search-status.pending{background:#fff7df;color:#9a5a00;border:1px solid #f0d79a}
    .riep-recount-range{background:#fff7df!important;color:#9a5a00!important;border-color:#f0d79a!important}.riep-called{background:#eaf2ff!important;color:#294fa3!important;border-color:#cbdcf8!important}
    .riep-result-focus{outline:4px solid rgba(46,107,255,.18);outline-offset:4px;scroll-margin-top:24px}
  `;
  document.head.appendChild(style);
  let statuses=new Map(), financeRoutes=new Map(), contested=new Map(), resultRaces=[];
  function statusClass(s){if(s.election_status==='primary_pending')return'pending';if(s.election_status==='lost_primary')return'lost';if(s.unopposed_general)return'unopposed';if(s.party==='REP')return'rep';if(s.party==='DEM')return'dem';return'ind';}
  function raceKey(chamber,district,party){return `${String(chamber).toLowerCase()}|${Number(district)}|${String(party||'').toUpperCase()}`;}
  function candidateBox(el){return el.closest('.hero-search-match,.candidate-card,.candidate-result,.result-card,.result-item,article,li')||el.parentElement?.parentElement||el.parentElement;}
  function decorateSearch(root=document){
    if(!root.querySelectorAll)return;
    root.querySelectorAll('.hero-search-match-name').forEach(el=>{
      const s=statuses.get(norm(el.textContent)); if(!s)return;
      const parent=el.parentElement;
      if(parent&&!parent.querySelector('.riep-search-status')){const badge=document.createElement('span');badge.className=`riep-search-status ${statusClass(s)}`;badge.textContent=s.status_label;parent.appendChild(badge);}
      const box=candidateBox(el); if(!box)return;
      const key=raceKey(s.chamber,s.district,s.party); if(contested.has(key)){
        const target=`/primary-results.html?chamber=${encodeURIComponent(s.chamber)}&district=${encodeURIComponent(s.district)}&party=${encodeURIComponent(s.party)}`;
        const actions=[...box.querySelectorAll('a')];
        const view=actions.find(a=>/view race|candidate|result/i.test(a.textContent||''))||actions[0];
        if(view){view.href=target;view.textContent='View primary results';}
      }
    });
  }
  function routeFinance(root=document){
    if(!root.querySelectorAll)return;
    root.querySelectorAll('.candidate-name,[data-candidate-name],.hero-search-match-name,h2,h3,h4,strong').forEach(el=>{
      const route=financeRoutes.get(norm(el.textContent)); if(!route)return;
      const box=candidateBox(el); if(!box)return;
      [...box.querySelectorAll('a')].filter(a=>/campaign finance/i.test(a.textContent||'')).forEach(a=>a.href=route.url);
    });
  }
  function cleanBallotFinance(root=document){
    if(!isBallot||!root.querySelectorAll)return;
    root.querySelectorAll('.riep-finance-supplement').forEach(n=>n.remove());
    root.querySelectorAll('[class*="finance"]').forEach(n=>{if(!n.matches('a,button')&&!/campaign finance/i.test(n.textContent||''))n.style.display='none';});
  }
  function decoratePrimaryResults(){
    if(!isPrimaryResults)return;
    const cards=[...document.querySelectorAll('section,article,.race-card,.result-card,div')].filter(el=>/(State )?(House|Senate) District \d+/i.test((el.querySelector?.('h1,h2,h3,h4')?.textContent)||''));
    resultRaces.forEach(r=>{
      const chamber=String(r.chamber||'').toLowerCase(); const district=Number(r.district||r.district_number||0); const party=String(r.party||'').toUpperCase();
      const cs=(r.candidates||[]).filter(c=>Number.isFinite(Number(c.votes))); if(cs.length<2)return;
      const sorted=[...cs].sort((a,b)=>Number(b.votes)-Number(a.votes)); const total=sorted.reduce((a,c)=>a+Number(c.votes||0),0); const diff=Number(sorted[0].votes)-Number(sorted[1].votes); const threshold=Math.min(total*.02,200); const inRecount=diff<threshold;
      const card=cards.find(c=>{const h=c.querySelector?.('h1,h2,h3,h4');const t=h?.textContent||'';return new RegExp(`${chamber==='house'?'House':'Senate'}\\s+District\\s+${district}\\b`,'i').test(t);});
      if(!card)return;
      const badge=[...card.querySelectorAll('span,div')].find(x=>/too close to call|called/i.test((x.textContent||'').trim())&&x.children.length===0);
      if(badge){badge.textContent=inRecount?'RECOUNT RANGE':'CALLED';badge.classList.add(inRecount?'riep-recount-range':'riep-called');}
      if(!inRecount){const winner=norm(sorted[0].name);[...card.querySelectorAll('strong,b,h3,h4,div,span')].forEach(x=>{if(norm(x.textContent)===winner&&x.children.length===0){const row=x.closest('li,.candidate-row,.result-row,div');if(row&&!row.querySelector('.riep-search-status')){const b=document.createElement('span');b.className='riep-search-status dem';b.textContent='Winner';row.appendChild(b);}}});}
    });
    const q=new URLSearchParams(location.search); const ch=q.get('chamber'),d=Number(q.get('district')||0),p=(q.get('party')||'').toUpperCase();
    if(ch&&d){const card=cards.find(c=>{const h=c.querySelector?.('h1,h2,h3,h4');return new RegExp(`${ch.toLowerCase()==='house'?'House':'Senate'}\\s+District\\s+${d}\\b`,'i').test(h?.textContent||'');});if(card){card.classList.add('riep-result-focus');setTimeout(()=>card.scrollIntoView({behavior:'smooth',block:'start'}),150);}}
  }
  function decorate(root=document){decorateSearch(root);routeFinance(root);cleanBallotFinance(root);if(root===document)decoratePrimaryResults();}
  Promise.all([
    fetch('/data/post_primary_status_2026.json?v=20260910d',{cache:'no-store'}).then(r=>r.json()),
    fetch('/data/independent_finance_index_2026.json?v=20260910b',{cache:'no-store'}).then(r=>r.json()),
    fetch('/data/primary_results_2026.json?v=20260910',{cache:'no-store'}).then(r=>r.json())
  ]).then(([s,f,r])=>{
    (s.candidates||[]).forEach(x=>statuses.set(norm(x.name),x));
    (f.candidates||[]).forEach(x=>financeRoutes.set(norm(x.name),x));
    resultRaces=r.races||[]; resultRaces.forEach(x=>{if(x.contested!==false)contested.set(raceKey(x.chamber,x.district||x.district_number,x.party),x);});
    decorate(document);
    new MutationObserver(ms=>ms.forEach(m=>m.addedNodes.forEach(n=>{if(n.nodeType===1)decorate(n)}))).observe(document.body,{childList:true,subtree:true});
  }).catch(e=>console.warn('RIEP supplemental 2026 layer:',e));
})();
