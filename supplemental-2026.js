(() => {
  const norm=s=>String(s||'').toLowerCase().replace(/[^a-z0-9 ]+/g,' ').replace(/\b(jr|sr|ii|iii|iv)\b/g,' ').replace(/\s+/g,' ').trim();
  const money=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(Number(n||0));
  const style=document.createElement('style');
  style.textContent=`
    .riep-search-status{display:inline-flex;margin-top:8px;padding:5px 8px;border-radius:999px;font:800 10px/1.1 'Instrument Sans',system-ui,sans-serif;letter-spacing:.04em;text-transform:uppercase}
    .riep-search-status.lost{background:#eceff3;color:#4b5563;border:1px solid #cbd2da}
    .riep-search-status.rep{background:#fff0f1;color:#b83d45;border:1px solid #f0c7cb}
    .riep-search-status.dem{background:#edf4ff;color:#215ed8;border:1px solid #cbdcf8}
    .riep-search-status.ind{background:#f1f3f5;color:#505a67;border:1px solid #cfd5dc}
    .riep-search-status.unopposed{background:#eef8f5;color:#126b5f;border:1px solid #c8e6dd}
    .riep-finance-supplement{margin-top:14px;padding-top:13px;border-top:1px solid #e5ebf2}
    .riep-finance-title{font-size:9px;font-weight:900;letter-spacing:.1em;text-transform:uppercase;color:#708098;margin-bottom:8px}
    .riep-finance-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}
    .riep-finance-stat{padding:9px;border:1px solid #e2e8f0;border-radius:4px;background:#fff}
    .riep-finance-stat strong{display:block;font-size:15px;color:#101b3b}.riep-finance-stat span{display:block;margin-top:3px;font-size:9px;color:#6b778c}
    .riep-finance-note{margin-top:7px;font-size:9px;line-height:1.4;color:#78879a}
  `;
  document.head.appendChild(style);
  let statuses=new Map(), finance=new Map();
  function statusClass(s){if(s.election_status==='lost_primary')return'lost';if(s.unopposed_general)return'unopposed';if(s.party==='REP')return'rep';if(s.party==='DEM')return'dem';return'ind';}
  function decorateSearch(root=document){
    if(!root.querySelectorAll)return;
    root.querySelectorAll('.hero-search-match-name').forEach(el=>{
      const s=statuses.get(norm(el.textContent)); if(!s)return;
      const parent=el.parentElement; if(!parent||parent.querySelector('.riep-search-status'))return;
      const badge=document.createElement('span'); badge.className=`riep-search-status ${statusClass(s)}`; badge.textContent=s.status_label; parent.appendChild(badge);
    });
  }
  function decorateFinance(root=document){
    if(!root.querySelectorAll)return;
    root.querySelectorAll('.candidate-name,[data-candidate-name]').forEach(el=>{
      const f=finance.get(norm(el.textContent)); if(!f)return;
      const card=el.closest('.candidate-card,article,.candidate-result,.result-card')||el.parentElement?.parentElement; if(!card||card.querySelector('.riep-finance-supplement'))return;
      const box=document.createElement('div'); box.className='riep-finance-supplement';
      box.innerHTML=`<div class="riep-finance-title">Campaign finance · through ${f.latest_period_label}</div><div class="riep-finance-grid"><div class="riep-finance-stat"><strong>${money(f.ytd_receipts)}</strong><span>2026 receipts</span></div><div class="riep-finance-stat"><strong>${money(f.ytd_campaign_expenses)}</strong><span>2026 campaign expenses</span></div><div class="riep-finance-stat"><strong>${money(f.cash_on_hand)}</strong><span>Cash on hand</span></div><div class="riep-finance-stat"><strong>${money(f.liabilities)}</strong><span>Liabilities</span></div></div><div class="riep-finance-note">Source: ${f.source}. Figures reflect filed reports supplied to RIEP.</div>`;
      card.appendChild(box);
    });
  }
  function decorate(root=document){decorateSearch(root);decorateFinance(root)}
  Promise.all([
    fetch('data/post_primary_status_2026.json?v=20260910c',{cache:'no-store'}).then(r=>r.json()),
    fetch('data/independent_finance_supplement_2026.json?v=20260910',{cache:'no-store'}).then(r=>r.json())
  ]).then(([s,f])=>{
    (s.candidates||[]).forEach(x=>statuses.set(norm(x.name),x));
    (f.candidates||[]).forEach(x=>{finance.set(norm(x.name),x);(x.aliases||[]).forEach(a=>finance.set(norm(a),x));});
    decorate();
    new MutationObserver(ms=>ms.forEach(m=>m.addedNodes.forEach(n=>{if(n.nodeType===1)decorate(n)}))).observe(document.body,{childList:true,subtree:true});
  }).catch(e=>console.warn('RIEP supplemental 2026 layer:',e));
})();
