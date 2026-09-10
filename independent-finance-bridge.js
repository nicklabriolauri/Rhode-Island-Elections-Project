(() => {
  const isBallot=(location.pathname||'').toLowerCase().endsWith('ballot.html');
  const norm=s=>String(s||'').toLowerCase().replace(/[^a-z0-9 ]+/g,' ').replace(/\b(jr|sr|ii|iii|iv)\b/g,' ').replace(/\s+/g,' ').trim();
  let mapById=new Map(),mapByName=new Map();
  const cardFor=el=>el.closest('.candidate-card,.candidate-result,.search-result,.result-card,.result-item,.candidate-item,.candidate-row,article,li')||el.parentElement;
  function cleanBallotFinance(root=document){
    if(!isBallot||!root.querySelectorAll)return;
    root.querySelectorAll('.riep-finance-summary,.independent-finance-summary,[data-riep-finance-summary]').forEach(el=>el.remove());
    root.querySelectorAll('.candidate-card,.candidate-result,.result-card,.candidate-item,article').forEach(card=>{
      [...card.querySelectorAll('div,p,section')].forEach(el=>{
        if(el.children.length) return;
        const t=(el.textContent||'').trim();
        if(/^(2026 receipts|raised in 2026|spent in 2026|cash on hand|liabilities|latest filing)/i.test(t)) el.remove();
      });
    });
  }
  function reroute(root=document){
    if(!root.querySelectorAll)return;
    root.querySelectorAll('a[href*="finance.html?candidate="]').forEach(a=>{
      try{
        const u=new URL(a.href,location.href); const id=u.searchParams.get('candidate'); const rec=mapById.get(id);
        if(rec) a.href=rec.url;
      }catch(e){}
    });
    root.querySelectorAll('.candidate-name,[data-candidate-name],h2,h3,h4,strong,b').forEach(el=>{
      const rec=mapByName.get(norm(el.textContent)); if(!rec)return;
      const card=cardFor(el); if(!card)return;
      const a=[...card.querySelectorAll('a')].find(x=>/campaign finance/i.test(x.textContent||''));
      if(a) a.href=rec.url;
    });
    cleanBallotFinance(root);
  }
  fetch('/data/independent_finance_index_2026.json?v=20260910',{cache:'no-store'}).then(r=>r.json()).then(p=>{
    (p.candidates||[]).forEach(c=>{mapById.set(c.candidate_id,c);mapByName.set(norm(c.name),c)});
    reroute();
    new MutationObserver(ms=>ms.forEach(m=>m.addedNodes.forEach(n=>{if(n.nodeType===1)reroute(n)}))).observe(document.body,{childList:true,subtree:true});
  }).catch(e=>console.warn('Independent finance routing:',e));
})();
