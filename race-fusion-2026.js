(() => {
  const path=(location.pathname||'').toLowerCase();
  const m=path.match(/\/races\/(house|senate)-(\d+)-(democratic|republican)\.html$/);
  if(!m) return;
  const chamber=m[1], district=Number(m[2]), party=m[3]==='democratic'?'DEM':'REP';
  const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'","&#39;");
  const norm=v=>String(v||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\b(jr|sr|ii|iii|iv)\.?\b/g,'').replace(/[^a-z0-9]+/g,' ').trim();
  const style=document.createElement('style');
  style.textContent=`
    .riep-info{margin-top:18px}.riep-info-head{display:flex;justify-content:space-between;gap:14px;align-items:end;flex-wrap:wrap;margin-bottom:12px}
    .riep-info-head h2{margin:0;font-size:28px;letter-spacing:-.035em}.riep-info-head p{margin:5px 0 0;color:#64748b;line-height:1.5;max-width:760px}
    .riep-profile-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.riep-profile{border:1px solid #e2e8f0;border-radius:18px;padding:17px;background:linear-gradient(180deg,#fff,#fbfdff)}
    .riep-profile.lost{opacity:.68;background:#f5f7fa}.riep-top{display:flex;justify-content:space-between;gap:12px;align-items:start}.riep-name{font-size:21px;font-weight:900;letter-spacing:-.025em}
    .riep-sub{margin-top:5px;color:#64748b;font-size:12px}.riep-badges{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}.riep-badge{padding:5px 8px;border-radius:999px;background:#eef3f8;color:#637188;font-size:9px;font-weight:900;text-transform:uppercase;letter-spacing:.06em}
    .riep-badge.dem{background:#edf4ff;color:#215ed8}.riep-badge.rep{background:#fff0f1;color:#b83d45}.riep-badge.lost{background:#e8edf3;color:#4f5f73}
    .riep-links{display:flex;gap:7px;flex-wrap:wrap;margin-top:12px}.riep-links a{border:1px solid #dbe4ef;padding:7px 9px;border-radius:999px;background:#fff;font-size:11px;font-weight:900;color:#111c3d}
    .riep-section{margin-top:14px;padding-top:13px;border-top:1px solid #e5ebf2}.riep-label{text-transform:uppercase;letter-spacing:.1em;color:#708098;font-size:9px;font-weight:900}.riep-priorities{display:grid;gap:8px;margin-top:9px}.riep-priority{padding:10px;border-radius:13px;background:#f5f8fc}.riep-priority strong{display:block;font-size:13px}.riep-priority p{margin:4px 0 0;color:#64748b;font-size:11px;line-height:1.45}
    .riep-chips{display:flex;gap:7px;flex-wrap:wrap;margin-top:9px}.riep-chip{padding:7px 9px;border-radius:999px;background:#eef8f5;border:1px solid #cce9df;color:#176b5d;font-size:10px;font-weight:800}
    .riep-rating{display:grid;grid-template-columns:minmax(130px,.8fr) 70px minmax(180px,1.4fr) auto;gap:10px;padding:10px 0;border-top:1px solid #edf1f5;align-items:start;font-size:11px}.riep-rating:first-of-type{margin-top:7px}.riep-rating strong{font-size:18px}.riep-source{color:#315f91;font-weight:800}
    .riep-await{margin-top:10px;padding:10px;border-radius:12px;background:#fff8e8;color:#76551b;font-size:11px;line-height:1.45}.riep-note{margin-top:8px;color:#78879a;font-size:10px;line-height:1.45}
    .riep-vote-method{margin-top:16px;padding:13px 14px;border:1px solid #dbe4ef;border-radius:14px;background:#f8fafc;color:#475569;font-size:12px;line-height:1.5}.riep-vote-method strong{color:#0f172a}
    @media(max-width:820px){.riep-profile-grid{grid-template-columns:1fr}.riep-rating{grid-template-columns:1fr}.riep-top{flex-direction:column}.riep-badges{justify-content:flex-start}}
  `;
  document.head.appendChild(style);

  const getCandidate=(running,name)=>{
    const rec=running?.chambers?.[chamber]?.[String(district)];
    const all=[...(rec?.candidates||[]),...(rec?.general_candidates||[])];
    return all.find(c=>norm(c.name)===norm(name))||null;
  };
  const profileFor=(profiles,c)=>profiles.find(p=>p.candidate_id===c?.candidate_id)||null;
  const researchFor=(research,c,name)=>research.find(p=>p.candidate_id===c?.candidate_id||norm(p.candidate_name||p.name)===norm(name))||null;
  const ratingsFor=(ratings,name)=>ratings.filter(r=>String(r.chamber||'').toLowerCase()===chamber&&Number(r.district_number)===district&&norm(r.candidate_name)===norm(name));
  function card(name,running,profiles,research,ratings){
    const c=getCandidate(running,name)||{name};
    const p=profileFor(profiles,c), web=researchFor(research,c,name), items=ratingsFor(ratings,name);
    const lost=c.election_status==='lost_primary'||c.primary_result==='lost';
    const campaign=p?.campaign_url||web?.campaign_website||c.campaign_url||'';
    const email=p?.email_override||c.email||'', phone=p?.phone_override||c.phone||'';
    const priorities=p?.priorities?.length?p.priorities:(web?.priorities||[]);
    const endorsements=web?.endorsements||[];
    const links=[];
    if(campaign)links.push(`<a href="${esc(campaign)}" target="_blank" rel="noopener">Campaign website</a>`);
    if(email)links.push(`<a href="mailto:${esc(email)}">Email</a>`);
    if(phone)links.push(`<a href="tel:${esc(String(phone).replace(/[^\\d+]/g,''))}">Call</a>`);
    if(c.candidate_id)links.push(`<a href="/finance.html?candidate=${encodeURIComponent(c.candidate_id)}">Campaign finance</a>`);
    return `<article class="riep-profile ${lost?'lost':''}">
      <div class="riep-top"><div><div class="riep-name">${esc(name)}</div><div class="riep-sub">${esc(c.home_label||c.hometown||'')} ${c.home_precinct_code?'· Home precinct '+esc(c.home_precinct_code):''}</div></div>
      <div class="riep-badges"><span class="riep-badge ${party==='DEM'?'dem':'rep'}">${party==='DEM'?'Democratic':'Republican'}</span>${lost?'<span class="riep-badge lost">Lost primary</span>':''}</div></div>
      ${links.length?`<div class="riep-links">${links.join('')}</div>`:''}
      ${p?.summary?`<div class="riep-sub" style="margin-top:12px;font-size:13px">${esc(p.summary)}</div>`:''}
      ${priorities.length?`<div class="riep-section"><div class="riep-label">Campaign priorities</div><div class="riep-priorities">${priorities.slice(0,5).map(x=>`<div class="riep-priority"><strong>${esc(x.title)}</strong><p>${esc(x.summary)}</p></div>`).join('')}</div><div class="riep-note">Source: ${p?.priorities?.length?'candidate response submitted to RIEP':'official campaign website'}.</div></div>`:'<div class="riep-await">Campaign priorities have not been published in this profile. RIEP does not infer positions from party affiliation.</div>'}
      ${endorsements.length?`<div class="riep-section"><div class="riep-label">Verified endorsements</div><div class="riep-chips">${endorsements.map(x=>`<a class="riep-chip" href="${esc(x.source_url||x.url||'#')}" target="_blank" rel="noopener">${esc(x.name||x.organization||x.endorser||'Endorsement')}</a>`).join('')}</div><div class="riep-note">Only explicit endorsement announcements are listed.</div></div>`:''}
      ${items.length?`<div class="riep-section"><div class="riep-label">Outside ratings & scorecards</div>${items.map(x=>`<div class="riep-rating"><span>${esc(x.organization)}<br><small>${esc(x.year)}</small></span><strong>${esc(x.rating)}</strong><span>${esc(x.measure)}<div class="riep-note">${esc(x.note||"Organization's rating; not an RIEP assessment.")}</div></span><a class="riep-source" href="${esc(x.source_url)}" target="_blank" rel="noopener">Source ↗</a></div>`).join('')}<div class="riep-note">RIEP does not combine outside ratings into an overall candidate score.</div></div>`:''}
    </article>`;
  }
  async function init(){
    const panel=[...document.querySelectorAll('main .panel')].find(x=>/primary results/i.test(x.querySelector('h2')?.textContent||''))||document.querySelector('main .panel:last-child');
    const names=[...panel.querySelectorAll('.candidate h2')].map(x=>x.textContent.trim()).filter(Boolean);
    if(!panel||!names.length)return;
    const [running,profiles,research,ratings]=await Promise.all([
      fetch('/data/whos_running_2026.json?v=20260912-race-fusion',{cache:'no-store'}).then(r=>r.json()),
      fetch('/data/candidate_profiles_2026.json?v=20260912-race-fusion',{cache:'no-store'}).then(r=>r.ok?r.json():{profiles:[]}).catch(()=>({profiles:[]})),
      fetch('/data/candidate_research_2026_with_endorsements.json?v=20260912-race-fusion',{cache:'no-store'}).then(r=>r.ok?r.json():{candidates:[]}).catch(()=>({candidates:[]})),
      fetch('/data/outside_ratings_2026.json?v=20260912-race-fusion',{cache:'no-store'}).then(r=>r.ok?r.json():{ratings:[]}).catch(()=>({ratings:[]}))
    ]);
    const section=document.createElement('section');section.className='panel riep-info';
    section.innerHTML=`<div class="riep-info-head"><div><h2>Candidate information</h2><p>Primary results and the candidate information from RIEP's Races & Candidates page are preserved together on this permanent race URL.</p></div><a class="riep-source" href="/running.html?chamber=${chamber}&district=${district}&election=primary">Open district in Races & Candidates →</a></div><div class="riep-profile-grid">${names.map(n=>card(n,running,profiles?.profiles||[],research?.candidates||research?.profiles||[],ratings?.ratings||[])).join('')}</div>
    <div class="riep-vote-method"><strong>Vote-method breakdown:</strong> Rhode Island's official results system provides a Vote Method view (Election Day, early voting, and mail ballots). RIEP links to the official results source rather than estimating or reconstructing these values when a stable machine-readable district breakdown is not available. <a class="riep-source" href="https://electionresults.ri.gov/results/public/RhodeIsland/elections/RI2026StatewidePrimary?cg=General%20Assembly" target="_blank" rel="noopener">Official RI results ↗</a></div>`;
    panel.parentElement.insertAdjacentElement('afterend',section);
  }
  init().catch(e=>console.warn('RIEP race fusion:',e));
})();