(() => {
  const STATUS_URL = 'data/post_primary_status_2026.json?v=20260910b';
  const path = (location.pathname || '').toLowerCase();
  const isBallot = path.endsWith('/ballot.html') || path.endsWith('ballot.html');
  const norm = s => String(s||'').toLowerCase().replace(/[^a-z0-9 ]+/g,' ').replace(/\b(jr|sr|ii|iii|iv)\b/g,' ').replace(/\s+/g,' ').trim();
  const style = document.createElement('style');
  style.textContent = `
    .riep-lost-primary{background:#f4f5f7!important;border-color:#c8d0da!important;filter:grayscale(.15)}
    .riep-lost-primary>:not(.riep-status){opacity:.62}
    .riep-status{display:inline-flex;margin:6px 5px 0 0;padding:4px 7px;border-radius:4px;border:1px solid #ccd5df;background:#f5f7fa;color:#4d5c70;font:800 9px/1.15 'Instrument Sans',system-ui,sans-serif;letter-spacing:.055em;text-transform:uppercase;opacity:1!important}
    .riep-status.lost{background:#eef0f3;color:#596574;border-color:#c9d0d9}
    .riep-status.dem-won{background:#edf4ff;color:#215ed8;border-color:#cbdcf8}
    .riep-status.rep-won{background:#fff0f1;color:#b83d45;border-color:#f0c7cb}
    .riep-status.general{background:#f2f4f7;color:#4b5563;border-color:#d6dbe2}
    .riep-status.unopposed{background:#eef8f5;color:#126b5f;border-color:#c8e6dd}
    .riep-status.independent{background:#f1f3f5;color:#505a67;border-color:#cfd5dc}
  `;
  document.head.appendChild(style);
  let byName = new Map(), byRace = new Map(), busy = false;
  const containerFor = el => el.closest('.candidate-card,.candidate-result,.search-result,.result-card,.result-item,.candidate-item,.candidate-row,article,li') || el.parentElement;
  function cls(s){
    if(s.unopposed_general) return 'unopposed';
    if(s.election_status==='lost_primary') return 'lost';
    if(s.party==='OTH') return 'independent';
    if(s.primary_result==='won' && s.party==='REP') return 'rep-won';
    if(s.primary_result==='won' && s.party==='DEM') return 'dem-won';
    return 'general';
  }
  function raceKey(chamber,district){ return `${String(chamber).toLowerCase()}|${Number(district)}`; }
  function cleanBallotRaceText(root=document){
    if(!isBallot || !byRace.size || !root.querySelectorAll) return;
    [...root.querySelectorAll('h1,h2,h3,h4')].forEach(h=>{
      const m=h.textContent.match(/(House|Senate)\s+District\s+(\d+)/i); if(!m) return;
      const race=byRace.get(raceKey(m[1],m[2])); if(!race) return;
      const box=h.closest('section,article,.race-section,.race-card,.card') || h.parentElement?.parentElement;
      if(!box) return;
      const active=race.filter(s=>s.election_status!=='lost_primary');
      [...box.querySelectorAll('p,div,span')].forEach(el=>{
        const t=String(el.textContent||'').trim();
        if(/primary candidates? currently listed/i.test(t) && el.children.length===0){
          el.textContent=`${active.length} general-election candidate${active.length===1?'':'s'} currently listed.`;
        }
        if(/Competitive (Democratic|Republican) primary/i.test(t) && el.children.length===0){
          el.style.display='none';
        }
      });
    });
  }
  function decorate(root=document){
    if(busy || !byName.size) return; busy=true;
    try{
      const nodes = root.querySelectorAll ? [...root.querySelectorAll('.candidate-name,[data-candidate-name],strong,b,h2,h3,h4')] : [];
      nodes.forEach(el=>{
        const s=byName.get(norm(el.textContent)); if(!s) return;
        const box=containerFor(el); if(!box) return;
        if(isBallot && s.election_status==='lost_primary'){ box.style.display='none'; return; }
        if(s.election_status==='lost_primary') box.classList.add('riep-lost-primary');
        if(box.querySelector(`[data-riep-id="${CSS.escape(String(s.candidate_id||s.name))}"]`)) return;
        const badge=document.createElement('span'); badge.className=`riep-status ${cls(s)}`; badge.dataset.riepId=s.candidate_id||s.name; badge.textContent=s.status_label;
        const badges=box.querySelector('.badges'); if(badges) badges.appendChild(badge); else el.insertAdjacentElement('afterend',badge);
      });
      cleanBallotRaceText(root);
    } finally { busy=false; }
  }
  fetch(STATUS_URL,{cache:'no-store'}).then(r=>r.json()).then(p=>{
    (p.candidates||[]).forEach(s=>{
      byName.set(norm(s.name),s);
      const key=raceKey(s.chamber,s.district); if(!byRace.has(key)) byRace.set(key,[]); byRace.get(key).push(s);
    });
    decorate();
    [180,550,1300].forEach(ms=>setTimeout(()=>decorate(document),ms));
    let timer=0;
    const refresh=()=>{clearTimeout(timer);timer=setTimeout(()=>decorate(document),70);};
    document.addEventListener('input',refresh,true);
    document.addEventListener('change',refresh,true);
  }).catch(e=>console.warn('RIEP post-primary status layer:',e));
})();
