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
  function isRobertCravenJrName(value){
    const t=String(value||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
    return t.includes('robert') && t.includes('craven') && (t.includes(' jr') || t.includes('junior'));
  }
  const CRAVEN_SOURCE='https://www.cravenforri.com/';
  const CRAVEN_ENDORSEMENTS=['House District 32 Democratic Committee','AFL-CIO','National Education Association Rhode Island','American Federation of Teachers and Healthcare Professionals','SEIU','Rhode Island Troopers Association','Climate Action Rhode Island',"Laborers' International Union of North America",'AFSCME Council 94','Rhode Island Building Trades','International Association of Fire Fighters','Planned Parenthood Votes! Rhode Island','Clean Water Action','Rhode Island Fraternal Order of Police','Rhode Island Coalition Against Gun Violence','National Association of Government Employees','International Brotherhood of Police Officers'];
  function fixCravenJr(root=document){
    if(!root.querySelectorAll)return;
    root.querySelectorAll('.hero-search-match').forEach(card=>{
      const name=card.querySelector('.hero-search-match-name')?.textContent||'';
      if(!isRobertCravenJrName(name))return;
      card.querySelectorAll('.hero-search-match-status.is-incumbent').forEach(n=>n.remove());
      card.querySelectorAll('.hero-search-result-grid').forEach(grid=>{
        const label=grid.querySelector('.hero-search-result-label')?.textContent||'';
        if(/2024 candidate performance/i.test(label))grid.remove();
      });
    });
    root.querySelectorAll('.candidate-card').forEach(card=>{
      const name=card.querySelector('.candidate-name')?.textContent||'';
      if(!isRobertCravenJrName(name))return;
      card.querySelectorAll('.office-record,.outside-rating-block').forEach(n=>n.remove());
      let block=card.querySelector('.endorsement-block');
      if(!block){
        block=document.createElement('div');block.className='endorsement-block';
        block.innerHTML='<div class="priority-label">Endorsements</div><div class="endorsement-list"></div><div class="source-note">Only explicit endorsement announcements are listed. Select an endorsement to open its source.</div>';
        const anchor=card.querySelector('.priority-block,.awaiting');
        if(anchor)anchor.insertAdjacentElement('afterend',block);else card.appendChild(block);
      }
      const list=block.querySelector('.endorsement-list');
      if(list){
        const existing=new Map([...list.querySelectorAll('.endorsement-chip')].map(a=>[norm(a.textContent),a]));
        CRAVEN_ENDORSEMENTS.forEach(label=>{
          const key=norm(label);if(existing.has(key))return;
          const a=document.createElement('a');a.className='endorsement-chip';a.href=CRAVEN_SOURCE;a.target='_blank';a.rel='noopener';a.textContent=label;list.appendChild(a);existing.set(key,a);
        });
      }
    });
  }
  function dedupeEndorsements(root=document){
    if(!root.querySelectorAll)return;
    root.querySelectorAll('.endorsement-block').forEach(block=>{
      const seen=new Set();
      block.querySelectorAll('.endorsement-chip').forEach(chip=>{
        const key=String(chip.textContent||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
        if(!key)return;if(seen.has(key))chip.remove();else seen.add(key);
      });
      const card=block.closest('.candidate-card');
      if(card){
        const count=block.querySelectorAll('.endorsement-chip').length;
        let badge=[...card.querySelectorAll('.badge.response')].find(b=>/endorsement/i.test(b.textContent||''));
        if(!badge&&count){badge=document.createElement('span');badge.className='badge response';card.querySelector('.badges')?.appendChild(badge);}
        if(badge)badge.textContent=`${count} endorsement${count===1?'':'s'}`;
      }
    });
  }
  function applyCorrections(root=document){fixCravenJr(root);dedupeEndorsements(root);}
  function reroute(root=document){
    if(!root.querySelectorAll)return;
    root.querySelectorAll('a[href*="finance.html?candidate="]').forEach(a=>{try{const u=new URL(a.href,location.href);const id=u.searchParams.get('candidate');const rec=mapById.get(id);if(rec)a.href=rec.url;}catch(e){}});
    root.querySelectorAll('.candidate-name,[data-candidate-name],h2,h3,h4,strong,b').forEach(el=>{const rec=mapByName.get(norm(el.textContent));if(!rec)return;const card=cardFor(el);if(!card)return;const a=[...card.querySelectorAll('a')].find(x=>/campaign finance/i.test(x.textContent||''));if(a)a.href=rec.url;});
    cleanBallotFinance(root);applyCorrections(root);
  }
  fetch('/data/independent_finance_index_2026.json?v=20260910',{cache:'no-store'}).then(r=>r.json()).then(p=>{
    (p.candidates||[]).forEach(c=>{mapById.set(c.candidate_id,c);mapByName.set(norm(c.name),c)});reroute();
    [100,250,600,1200,2500].forEach(ms=>setTimeout(()=>reroute(document),ms));
    let timer=0;const refresh=()=>{clearTimeout(timer);timer=setTimeout(()=>reroute(document),60);};
    document.addEventListener('input',refresh,true);document.addEventListener('change',refresh,true);document.addEventListener('click',()=>setTimeout(()=>reroute(document),80),true);
    const observer=new MutationObserver(()=>refresh());observer.observe(document.body,{childList:true,subtree:true});
  }).catch(e=>{console.warn('Independent finance routing:',e);applyCorrections(document);const observer=new MutationObserver(()=>applyCorrections(document));observer.observe(document.body,{childList:true,subtree:true});});
})();
