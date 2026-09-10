(() => {
  const path=(location.pathname||'').toLowerCase();
  const isBallot=path.endsWith('ballot.html');
  const isPrimaryResults=path.endsWith('primary-results.html');
  const norm=s=>String(s||'').toLowerCase().replace(/[^a-z0-9 ]+/g,' ').replace(/\b(jr|sr|ii|iii|iv)\b/g,' ').replace(/\s+/g,' ').trim();
  const partyCode=p=>{p=String(p||'').toUpperCase();if(p.startsWith('DEM'))return'DEM';if(p.startsWith('REP'))return'REP';return p;};
  const style=document.createElement('style');
  style.textContent=`
    .riep-search-status{display:inline-flex;margin-top:8px;padding:5px 8px;border-radius:999px;font:800 10px/1.1 'Instrument Sans',system-ui,sans-serif;letter-spacing:.04em;text-transform:uppercase}
    .riep-search-status.lost{background:#eceff3;color:#4b5563;border:1px solid #cbd2da}.riep-search-status.rep{background:#fff0f1;color:#b83d45;border:1px solid #f0c7cb}.riep-search-status.dem{background:#edf4ff;color:#215ed8;border:1px solid #cbdcf8}.riep-search-status.ind{background:#f1f3f5;color:#505a67;border:1px solid #cfd5dc}.riep-search-status.unopposed{background:#eef8f5;color:#126b5f;border:1px solid #c8e6dd}.riep-search-status.pending{background:#fff7df;color:#9a5a00;border:1px solid #f0d79a}
    .riep-recount-range{background:#fff7df!important;color:#9a5a00!important;border-color:#f0d79a!important}.riep-called{background:#eaf2ff!important;color:#294fa3!important;border-color:#cbdcf8!important}
    .race-card .candidate-row.riep-called-winner{background:#172554!important;color:#fff!important;border-radius:14px;padding:14px 14px!important;margin:8px 0 10px;border-top:0!important}
    .race-card .candidate-row.riep-called-winner *{color:#fff!important}.race-card .candidate-row.riep-called-winner .progress{background:rgba(255,255,255,.24)!important}.race-card .candidate-row.riep-called-winner .progress span{background:#fff!important}
    .riep-result-focus{outline:4px solid rgba(46,107,255,.22);outline-offset:4px;scroll-margin-top:24px}.riep-candidate-focus{outline:3px solid rgba(255,255,255,.5);outline-offset:-3px}
  `;
  document.head.appendChild(style);
  let statuses=new Map(), financeByName=new Map(), financeById=new Map(), contestedByCandidate=new Map(), resultRaces=[];
  function statusClass(s){if(s.election_status==='primary_pending')return'pending';if(s.election_status==='lost_primary')return'lost';if(s.unopposed_general)return'unopposed';if(s.party==='REP')return'rep';if(s.party==='DEM')return'dem';return'ind';}
  function candidateBox(el){return el.closest('.hero-search-match,.candidate-card,.candidate-result,.result-card,.result-item,.candidate-item,.candidate-row,article,li')||el.parentElement?.parentElement||el.parentElement;}
  function primaryTarget(r,name){return `/primary-results.html?chamber=${encodeURIComponent(r.chamber)}&district=${encodeURIComponent(r.district||r.district_number)}&party=${encodeURIComponent(partyCode(r.party))}&candidate=${encodeURIComponent(name)}`;}
  function decorateSearch(root=document){
    if(!root.querySelectorAll)return;
    root.querySelectorAll('.hero-search-match-name').forEach(el=>{
      const name=el.textContent.trim(), s=statuses.get(norm(name)), box=el.closest('.hero-search-match')||candidateBox(el); if(!box)return;
      if(s){const parent=el.parentElement;if(parent&&!parent.querySelector('.riep-search-status')){const b=document.createElement('span');b.className=`riep-search-status ${statusClass(s)}`;b.textContent=s.status_label;parent.appendChild(b);}}
      const race=contestedByCandidate.get(norm(name));
      if(race){const target=primaryTarget(race,name);const view=box.querySelector('.hero-search-action.primary')||[...box.querySelectorAll('a')].find(a=>/view race|candidate|result/i.test(a.textContent||''));if(view){view.href=target;view.textContent='View primary results';}box.dataset.cardHref=target;box.setAttribute('aria-label',`View ${name} primary results`);}
      const route=financeByName.get(norm(name)); if(route){const actions=box.querySelector('.hero-search-match-actions');if(actions){let a=actions.querySelector('a.finance');if(!a){a=document.createElement('a');a.className='hero-search-action finance';a.textContent='Campaign finance';actions.appendChild(a);}a.href=route;}}
    });
  }
  function routeFinance(root=document){
    if(!root.querySelectorAll)return;
    root.querySelectorAll('a[href*="finance.html?candidate="]').forEach(a=>{try{const id=new URL(a.href,location.href).searchParams.get('candidate'),r=financeById.get(id);if(r)a.href=r;}catch(e){}});
    root.querySelectorAll('.candidate-name,[data-candidate-name],.hero-search-match-name,h2,h3,h4').forEach(el=>{const route=financeByName.get(norm(el.textContent));if(!route)return;const box=candidateBox(el);if(!box)return;const a=[...box.querySelectorAll('a')].find(x=>/campaign finance/i.test(x.textContent||''));if(a)a.href=route;});
  }
  function cleanBallotFinance(root=document){if(!isBallot||!root.querySelectorAll)return;root.querySelectorAll('.riep-finance-supplement,.independent-finance-summary,[data-riep-finance-summary]').forEach(n=>n.remove());}
  function findRaceCard(r){const title=`${String(r.chamber).toLowerCase()==='house'?'House':'Senate'} District ${Number(r.district||r.district_number)}`;return [...document.querySelectorAll('.race-card')].find(c=>{const h=c.querySelector('h3');if(!h||!h.textContent.includes(title))return false;const pill=c.querySelector('.party-pill');return !pill||norm(pill.textContent).includes(norm(String(r.party||'').replace('DEM','Democratic').replace('REP','Republican')));});}
  function decoratePrimaryResults(){
    if(!isPrimaryResults)return;
    resultRaces.forEach(r=>{const cs=(r.candidates||[]).filter(c=>Number.isFinite(Number(c.votes)));if(cs.length<2)return;const sorted=[...cs].sort((a,b)=>Number(b.votes)-Number(a.votes));const total=sorted.reduce((a,c)=>a+Number(c.votes||0),0),diff=Number(sorted[0].votes)-Number(sorted[1].votes),threshold=Math.min(total*.02,200),recount=diff<threshold,card=findRaceCard(r);if(!card)return;
      const badge=card.querySelector('.race-status');if(badge){badge.textContent=recount?'RECOUNT RANGE':'CALLED';badge.classList.remove('riep-called','riep-recount-range');badge.classList.add(recount?'riep-recount-range':'riep-called');}
      card.querySelectorAll('.candidate-row').forEach(row=>row.classList.remove('riep-called-winner'));
      if(!recount){const winner=norm(sorted[0].name);const row=[...card.querySelectorAll('.candidate-row')].find(x=>norm(x.querySelector('.candidate-name')?.textContent)===winner);if(row)row.classList.add('riep-called-winner');}
    });
    const q=new URLSearchParams(location.search),ch=q.get('chamber'),d=Number(q.get('district')||0),candidate=q.get('candidate');if(ch&&d){const r=resultRaces.find(x=>String(x.chamber).toLowerCase()===String(ch).toLowerCase()&&Number(x.district||x.district_number)===d&&(!q.get('party')||partyCode(x.party)===partyCode(q.get('party'))));const card=r&&findRaceCard(r);if(card){card.classList.add('riep-result-focus');if(candidate){const row=[...card.querySelectorAll('.candidate-row')].find(x=>norm(x.querySelector('.candidate-name')?.textContent)===norm(candidate));if(row)row.classList.add('riep-candidate-focus');}setTimeout(()=>card.scrollIntoView({behavior:'smooth',block:'center'}),100);}}
  }
  function decorate(root=document){decorateSearch(root);routeFinance(root);cleanBallotFinance(root);if(root===document)decoratePrimaryResults();}
  Promise.all([
    fetch('/data/post_primary_status_2026.json?v=20260910f',{cache:'no-store'}).then(r=>r.json()),
    fetch('/data/independent_finance_index_2026.json?v=20260910f',{cache:'no-store'}).then(r=>r.json()),
    fetch('/data/candidate_finance_2026.json?v=20260910f',{cache:'no-store'}).then(r=>r.json()),
    fetch('/data/primary_results_2026.json?v=20260910f',{cache:'no-store'}).then(r=>r.json())
  ]).then(([s,ind,fin,res])=>{
    (s.candidates||[]).forEach(x=>statuses.set(norm(x.name),x));
    (fin.directory||[]).forEach(x=>{if(x.slug){const u=`/finance.html?slug=${encodeURIComponent(x.slug)}`;financeByName.set(norm(x.candidate_name),u);financeById.set(x.candidate_id,u);}});
    (ind.candidates||[]).forEach(x=>{financeByName.set(norm(x.name),x.url);financeById.set(x.candidate_id,x.url);});
    resultRaces=res.races||[];resultRaces.forEach(r=>(r.candidates||[]).forEach(c=>contestedByCandidate.set(norm(c.name),r)));
    decorate(document);new MutationObserver(()=>decorate(document)).observe(document.body,{childList:true,subtree:true});
  }).catch(e=>console.warn('RIEP supplemental 2026 layer:',e));
})();
