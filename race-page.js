(() => {
  const body=document.body, chamber=body.dataset.chamber, district=Number(body.dataset.district);
  const titleChamber=chamber==='house'?'State House':'State Senate';
  const geoUrl=chamber==='house'?'/data/house_new.geojson':'/data/senate_new.geojson';
  const norm=s=>String(s||'').toLowerCase().replace(/[^a-z0-9 ]+/g,' ').replace(/\b(jr|sr|ii|iii|iv)\b/g,' ').replace(/\s+/g,' ').trim();
  const partyLabel=p=>p==='DEM'?'Democratic':p==='REP'?'Republican':'Independent';
  const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const districtFromFeature=f=>{
    const p=f.properties||{},raw=p.district_number??p.DIST_NUM??p.SLDUST??p.DISTRICT??p.District??p.NAME??p.NAMELSAD;
    const m=String(raw??'').match(/\d+/); return m?Number(m[0]):null;
  };
  const precinctCode=f=>String((f.properties||{}).DISTRICT||(f.properties||{}).PRECINCTS||(f.properties||{}).PRECINCT||(f.properties||{}).PRECINCT_ID||'').trim();

  Promise.all([
    fetch('/data/whos_running_2026.json?v=20260910-race',{cache:'no-store'}).then(r=>r.json()),
    fetch('/data/post_primary_status_2026.json?v=20260910-race',{cache:'no-store'}).then(r=>r.json()).catch(()=>({})),
    fetch('/data/candidate_finance_2026.json?v=20260910-race',{cache:'no-store'}).then(r=>r.json()).catch(()=>({})),
    fetch('/data/independent_finance_index_2026.json?v=20260910-race',{cache:'no-store'}).then(r=>r.json()).catch(()=>({})),
    fetch(geoUrl,{cache:'force-cache'}).then(r=>r.json()),
    fetch('/data/ri_turnout_2024_precinct.geojson',{cache:'force-cache'}).then(r=>r.json()).catch(()=>({features:[]})),
    fetch('/data/candidate_research_2026_with_endorsements.json?v=20260912-race',{cache:'no-store'}).then(r=>r.json()).catch(()=>({candidates:[]})),
    fetch('/data/candidate_profiles_2026.json?v=20260912-race',{cache:'no-store'}).then(r=>r.json()).catch(()=>({profiles:[]})),
    fetch('/data/outside_ratings_2026.json?v=20260912-race',{cache:'no-store'}).then(r=>r.json()).catch(()=>({ratings:[]}))
  ]).then(([running,status,finance,indFinance,geo,precincts,researchData,profileData,ratingsData])=>{
    const rec=running?.chambers?.[chamber]?.[String(district)]||{};
    const all=[...(rec.candidates||[]),...(rec.general_candidates||[])];
    const seen=new Set();
    const active=all.filter(c=>{
      const key=c.candidate_id||norm(c.name); if(seen.has(key))return false; seen.add(key);
      return c.election_status==='general_candidate'||c.on_election_ballot===true;
    });
    const historical=(rec.historical_candidates||[]).filter(c=>c.election_status==='lost_primary');
    const statusByName=new Map((status.candidates||[]).map(x=>[norm(x.name),x]));
    const financeById=new Map(),financeByName=new Map();
    (finance.directory||[]).forEach(x=>{if(x.slug){const u='/finance.html?slug='+encodeURIComponent(x.slug);financeById.set(x.candidate_id,u);financeByName.set(norm(x.candidate_name),u);}});
    (indFinance.candidates||[]).forEach(x=>{financeById.set(x.candidate_id,x.url);financeByName.set(norm(x.name),x.url);});
    const researchById=new Map((researchData.candidates||[]).map(x=>[x.candidate_id,x]));
    const researchByName=new Map((researchData.candidates||[]).map(x=>[norm(x.candidate_name),x]));
    const profilesById=new Map((profileData.profiles||[]).map(x=>[x.candidate_id,x]));
    const ratingsByName=new Map();
    (ratingsData.ratings||[]).forEach(x=>{
      const key=norm(x.candidate_name);
      if(!ratingsByName.has(key)) ratingsByName.set(key,[]);
      ratingsByName.get(key).push(x);
    });

    document.querySelector('[data-race-title]').textContent=`${titleChamber} District ${district}`;
    document.title=`${titleChamber} District ${district} | 2026 Rhode Island Election | RIEP`;
    const statusText=rec.general_label||rec.general_status||'2026 general election';
    document.querySelector('[data-race-status]').textContent=statusText;

    const candidatesEl=document.querySelector('[data-candidates]');
    candidatesEl.innerHTML=active.length?active.map(c=>{
      const st=statusByName.get(norm(c.name))||c;
      const profilePage=({"senate-1-dem-primary-jacob-bissaillon":"jacob-bissaillon","senate-2-dem-primary-ana-b-quezada":"ana-b-quezada","senate-3-dem-primary-samuel-d-zurier":"samuel-d-zurier","senate-4-dem-primary-stefano-v-famiglietti":"stefano-v-famiglietti","senate-5-dem-primary-samuel-w-bell":"samuel-w-bell","senate-6-dem-primary-tiara-t-mack":"tiara-t-mack","senate-9-dem-primary-john-burke":"john-burke","senate-8-dem-primary-lori-urso":"lori-urso","senate-7-dem-primary-frank-a-ciccone":"frank-a-ciccone","senate-10-dem-primary-walter-s-felag-jr":"walter-s-felag-jr","senate-11-dem-primary-linda-l-ujifusa":"linda-l-ujifusa","senate-12-dem-primary-louis-dipalma":"louis-dipalma","senate-13-dem-primary-dawn-euer":"dawn-euer","senate-14-dem-primary-valarie-jean-lawson":"valarie-jean-lawson","senate-15-dem-primary-meghan-e-kallman":"meghan-e-kallman","senate-16-dem-primary-jonathon-acosta":"jonathon-acosta","senate-18-dem-primary-robert-britto":"robert-britto","senate-19-dem-primary-ryan-w-pearson":"ryan-w-pearson","senate-20-dem-primary-brian-j-thompson":"brian-j-thompson","senate-21-rep-primary-gordon-e-rogers":"gordon-e-rogers","senate-22-dem-primary-david-p-tikoian":"david-p-tikoian","senate-23-rep-primary-jessica-de-la-cruz":"jessica-de-la-cruz","senate-24-dem-primary-melissa-murray":"melissa-murray","senate-25-dem-primary-andrew-r-dimitri":"andrew-r-dimitri","senate-26-dem-primary-todd-m-patalano":"todd-m-patalano","senate-27-dem-primary-hanna-m-gallo":"hanna-m-gallo","senate-28-dem-primary-lammis-j-vargas":"lammis-j-vargas","senate-29-dem-primary-peter-a-appollonio-jr":"peter-a-appollonio-jr","senate-30-dem-primary-mark-mckenney":"mark-mckenney","senate-31-dem-primary-matthew-l-lamountain":"matthew-l-lamountain","senate-17-rep-primary-thomas-j-paolino":"thomas-j-paolino","senate-17-dem-primary-nelly-burdette":"nelly-burdette","senate-32-dem-primary-pamela-j-lauria":"pamela-j-lauria","senate-33-dem-primary-leonidas-peter-raptakis":"leonidas-peter-raptakis","senate-34-rep-primary-elaine-j-morgan":"elaine-j-morgan","senate-35-dem-primary-bridget-g-valverde":"bridget-g-valverde","senate-33-rep-primary-james-p-pierson":"james-p-pierson","senate-34-dem-primary-samantha-r-wilcox":"samantha-r-wilcox","senate-37-dem-primary-virginia-susan-sosnowski":"virginia-susan-sosnowski","house-35-dem-primary-kathleen-a-fogarty":"kathleen-a-fogarty","house-35-rep-primary-jennifer-p-nerbonne":"jennifer-p-nerbonne","senate-36-dem-primary-alana-m-dimario":"alana-m-dimario","senate-38-dem-primary-victoria-gu":"victoria-gu","house-1-dem-primary-edith-h-ajello":"edith-h-ajello","house-2-dem-primary-christopher-r-blazejewski":"christopher-r-blazejewski","house-3-dem-primary-nathan-w-biah":"nathan-w-biah","house-4-dem-primary-rebecca-m-kislak":"rebecca-m-kislak","house-6-dem-primary-raymond-a-hull":"raymond-a-hull","house-8-dem-primary-john-joseph-lombardi":"john-joseph-lombardi","house-9-dem-primary-enrique-george-sanchez":"enrique-george-sanchez","house-10-dem-primary-scott-a-slater":"scott-a-slater","house-5-dem-primary-anthony-j-desimone":"anthony-j-desimone","house-7-dem-primary-amy-j-santiago":"amy-j-santiago","house-7-rep-primary-christopher-l-ireland":"christopher-l-ireland","house-5-oth-general-brittany-m-kubicek":"brittany-m-kubicek","house-11-dem-primary-grace-diaz":"grace-diaz","house-13-dem-primary-ramon-perez":"ramon-perez","house-14-dem-primary-charlene-m-lima":"charlene-m-lima","house-12-dem-primary-arlette-hidalgo":"arlette-hidalgo","house-13-rep-primary-derick-a-reels":"derick-a-reels","house-16-dem-primary-brandon-potter":"brandon-potter","house-17-dem-primary-jacquelyn-baginski":"jacquelyn-baginski","house-18-dem-primary-arthur-handy":"arthur-handy","house-15-rep-primary-christopher-g-paplauskas":"christopher-g-paplauskas","house-15-dem-primary-colleen-m-crudele":"colleen-m-crudele","house-15-ind-general-allan-w-fung":"allan-w-fung","house-19-dem-primary-joseph-mcnamara":"joseph-mcnamara","house-20-dem-primary-david-a-bennett":"david-a-bennett","house-21-rep-primary-marie-a-hopkins":"marie-a-hopkins","house-22-dem-primary-zakary-j-pereira":"zakary-j-pereira","house-22-rep-primary-barbara-quigley":"barbara-quigley"})[c.candidate_id];
      const fin=financeById.get(c.candidate_id)||financeByName.get(norm(c.name));
      const home=[c.hometown,c.zip_code].filter(Boolean).join(' ');
      const research=researchById.get(c.candidate_id)||researchByName.get(norm(c.name))||{};
      const profile=profilesById.get(c.candidate_id)||{};
      const priorities=(profile.priorities&&profile.priorities.length?profile.priorities:research.priorities)||[];
      const endorsements=[];
      const seenEnd=new Set();
      (research.endorsements||[]).forEach(e=>{const label=e.organization||e.name;if(label&&!seenEnd.has(norm(label))){seenEnd.add(norm(label));endorsements.push({label,url:e.source_url||''});}});
      const ratings=ratingsByName.get(norm(c.name))||[];
      const campaign=profile.campaign_url||research.campaign_website||c.campaign_url||'';
      const email=profile.email_override||c.email||'';
      const phone=profile.phone_override||c.phone||'';
      const priorityHtml=priorities.length?`<div class="candidate-detail"><div class="detail-label">Top priorities</div><div class="priority-list">${priorities.slice(0,5).map(p=>`<div class="priority"><strong>${esc(p.title)}</strong><span>${esc(p.summary||'')}</span></div>`).join('')}</div></div>`:'';
      const endHtml=endorsements.length?`<div class="candidate-detail"><div class="detail-label">Verified endorsements</div><div class="chip-row">${endorsements.map(e=>e.url?`<a class="chip" href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.label)}</a>`:`<span class="chip">${esc(e.label)}</span>`).join('')}</div></div>`:'';
      const ratingHtml=ratings.length?`<div class="candidate-detail"><div class="detail-label">Outside ratings & scorecards</div>${ratings.map(r=>{
        if(r.source_type==='state legislative effectiveness score'){
          const bills=r.bills||{};
          const categories=r.bill_categories||[];
          const history=r.history||[];
          const categoryRows=categories.map(x=>`<tr><th><span>${esc(x.short)}</span>${esc(x.label)}</th><td>${esc(x.introduced)}</td><td>${esc(x.committee_action)}</td><td>${esc(x.beyond_committee)}</td><td>${esc(x.passed_chamber)}</td><td>${esc(x.became_law)}</td></tr>`).join('');
          const historyRows=history.map(x=>`<tr><th>${esc(x.term)}</th><td>${esc(Number(x.score).toFixed(2))}</td><td>${esc(x.rank)}</td></tr>`).join('');
          return `<section class="effectiveness-card"><div class="effectiveness-head"><div><span class="effectiveness-kicker">Legislative effectiveness · ${esc(r.year||'')}</span><strong>${esc(r.organization)}</strong></div><div class="effectiveness-score"><b>${esc(r.rating)}</b><span>Expected benchmark: ${esc(r.benchmark??'—')}</span></div></div><div class="effectiveness-context"><span>${esc(r.expectation||'')}</span><span>#${esc(r.party_rank)} of ${esc(r.party_total||'—')} ${esc(r.comparison_group||'peers')}</span></div><div class="bill-funnel"><div><b>${esc(bills.introduced??'—')}</b><span>Sponsored</span></div><div><b>${esc(bills.committee_action??'—')}</b><span>Committee action</span></div><div><b>${esc(bills.beyond_committee??'—')}</b><span>Beyond committee</span></div><div><b>${esc(bills.passed_chamber??'—')}</b><span>Passed chamber</span></div><div><b>${esc(bills.became_law??'—')}</b><span>Became law</span></div></div><details class="effectiveness-details"><summary>View legislative effectiveness details</summary>${categoryRows?`<div class="effectiveness-table-wrap"><table class="effectiveness-table"><thead><tr><th>Bill category</th><th>Sponsored</th><th>Committee action</th><th>Beyond committee</th><th>Passed chamber</th><th>Became law</th></tr></thead><tbody>${categoryRows}</tbody></table></div><p class="effectiveness-key"><b>C</b> commemorative · <b>S</b> substantive · <b>SS</b> substantive and significant</p>`:''}${historyRows?`<h4>Historical scores</h4><div class="effectiveness-table-wrap"><table class="effectiveness-table history-table"><thead><tr><th>Session</th><th>Score</th><th>Party rank</th></tr></thead><tbody>${historyRows}</tbody></table></div>`:''}</details><p>${esc(r.note||r.measure||'')}</p><div class="effectiveness-links"><a href="${esc(r.source_url)}" target="_blank" rel="noopener">View source report ↗</a>${r.methodology_url?`<a href="${esc(r.methodology_url)}" target="_blank" rel="noopener">Methodology ↗</a>`:''}${r.glossary_url?`<a href="${esc(r.glossary_url)}" target="_blank" rel="noopener">Glossary ↗</a>`:''}</div></section>`;
        }
        return `<div class="rating-row"><div><strong>${esc(r.organization)}</strong><span>${esc(r.year||'')}</span></div><b>${esc(r.rating)}</b><a href="${esc(r.source_url)}" target="_blank" rel="noopener">Source ↗</a></div>`;
      }).join('')}</div>`:'';
      return `<article class="candidate-card">
        <div class="candidate-top"><div><span class="party ${String(c.party||'OTH').toLowerCase()}">${esc(partyLabel(c.party))}</span><h2>${profilePage?`<a href="/candidates/${profilePage}.html">${esc(c.name)}</a>`:esc(c.name)}</h2></div>
        <span class="status">${esc(st.status_label||'General Election Candidate')}</span></div>
        <p class="candidate-meta">${esc(home||'Rhode Island')} ${c.home_precinct_name?`· Home precinct ${esc(c.home_precinct_code)}`:''}</p>
        <div class="actions">
          ${campaign?`<a href="${esc(campaign)}" target="_blank" rel="noopener">Campaign website</a>`:''}
          ${email?`<a href="mailto:${esc(email)}">Email</a>`:''}
          ${phone?`<a href="tel:${esc(String(phone).replace(/[^\\d+]/g,''))}">Call</a>`:''}
          ${profilePage?`<a href="/candidates/${profilePage}.html">Candidate profile</a>`:''}
          ${fin?`<a href="${esc(fin)}">Campaign finance</a>`:''}
          <a href="/running.html?chamber=${encodeURIComponent(chamber)}&district=${encodeURIComponent(district)}">Open full Races & Candidates workspace</a>
        </div>
        ${profile.summary?`<p class="candidate-summary">${esc(profile.summary)}</p>`:''}
        ${priorityHtml}
        ${endHtml}
        ${ratingHtml}
      </article>`;
    }).join(''):'<p class="empty">No general-election candidate records are currently available for this district.</p>';

    const historyEl=document.querySelector('[data-primary-history]');
    if(historical.length){
      historyEl.closest('section').hidden=false;
      historyEl.innerHTML=historical.map(c=>`<div class="history-row"><strong>${esc(c.name)}</strong><span>${esc(c.status_label||'Lost primary')}</span><a href="/primary-results.html?chamber=${chamber}&district=${district}&party=${encodeURIComponent(c.party||'')}&candidate=${encodeURIComponent(c.name)}">View primary result</a></div>`).join('');
    }

    const map=L.map('raceMap',{scrollWheelZoom:false,zoomControl:true});
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,opacity:.3,attribution:'&copy; OpenStreetMap contributors'}).addTo(map);
    const feature=(geo.features||[]).find(f=>districtFromFeature(f)===district);
    if(feature){
      const layer=L.geoJSON(feature,{style:{color:'#172554',weight:4,fillColor:'#dbeafe',fillOpacity:.42}}).addTo(map);
      map.fitBounds(layer.getBounds(),{padding:[18,18]});
    } else map.setView([41.68,-71.52],9);

    const codes=new Map();
    active.forEach(c=>{if(c.home_precinct_code)codes.set(String(c.home_precinct_code),c);});
    (precincts.features||[]).forEach(f=>{
      const code=precinctCode(f),c=codes.get(code); if(!c)return;
      const lyr=L.geoJSON(f,{style:{color:'#0f766e',weight:2,fillColor:'#99f6e4',fillOpacity:.36}}).addTo(map);
      const center=lyr.getBounds().getCenter();
      L.circleMarker(center,{radius:6,color:'#0f766e',weight:2,fillColor:'#fff',fillOpacity:1}).addTo(map)
        .bindPopup(`<strong>${esc(c.name)}</strong><br>Public filing home precinct: ${esc(code)}<br><small>Exact residential address is not displayed.</small>`);
    });
    document.querySelector('[data-map-note]').textContent=active.some(c=>c.home_precinct_code)
      ? 'Map shows the legislative district boundary and candidates’ public filing home precincts. Exact residential addresses are intentionally not displayed.'
      : 'Map shows the legislative district boundary.';
  }).catch(err=>{
    console.error(err);
    document.querySelector('[data-candidates]').innerHTML='<p class="empty">Race data could not be loaded. Please try again.</p>';
  });
})();
