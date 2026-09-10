(() => {
  const STATUS_URL = 'data/post_primary_status_2026.json?v=20260910';
  const path = (location.pathname || '').toLowerCase();
  const isBallot = path.endsWith('/ballot.html') || path.endsWith('ballot.html');
  const norm = s => String(s||'').toLowerCase().replace(/[^a-z0-9 ]+/g,' ').replace(/\b(jr|sr|ii|iii|iv)\b/g,' ').replace(/\s+/g,' ').trim();
  const style = document.createElement('style');
  style.textContent = `
    .riep-lost-primary{background:#f4f5f7!important;border-color:#c8d0da!important;filter:grayscale(.15)}
    .riep-lost-primary>:not(.riep-status){opacity:.62}
    .riep-status{display:inline-flex;margin:6px 5px 0 0;padding:4px 7px;border-radius:4px;border:1px solid #ccd5df;background:#f5f7fa;color:#4d5c70;font:800 9px/1.15 'Instrument Sans',system-ui,sans-serif;letter-spacing:.055em;text-transform:uppercase;opacity:1!important}
    .riep-status.lost{background:#eef0f3;color:#596574;border-color:#c9d0d9}
    .riep-status.general{background:#eef5ff;color:#2459b8;border-color:#cbdcf8}
    .riep-status.unopposed{background:#eef8f5;color:#126b5f;border-color:#c8e6dd}
    .riep-status.independent{background:#ebf8f6;color:#0b756c;border-color:#bfe3de}
  `;
  document.head.appendChild(style);
  let byName = new Map(), busy = false;
  const containerFor = el => el.closest('.candidate-card,.candidate-result,.search-result,.result-card,.result-item,.candidate-item,.candidate-row,article,li') || el.parentElement;
  function cls(s){ return s.unopposed_general?'unopposed':s.election_status==='lost_primary'?'lost':s.party==='OTH'?'independent':'general'; }
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
    } finally { busy=false; }
  }
  fetch(STATUS_URL,{cache:'no-store'}).then(r=>r.json()).then(p=>{
    (p.candidates||[]).forEach(s=>byName.set(norm(s.name),s)); decorate();
    new MutationObserver(ms=>ms.forEach(m=>m.addedNodes.forEach(n=>{if(n.nodeType===1) decorate(n)}))).observe(document.body,{childList:true,subtree:true});
  }).catch(e=>console.warn('RIEP post-primary status layer:',e));
})();
