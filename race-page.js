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
      const ratingHtml=ratings.length?`<div class="candidate-detail"><div class="detail-label">Outside ratings & scorecards</div>${ratings.map(r=>`<div class="rating-row"><div><strong>${esc(r.organization)}</strong><span>${esc(r.year||'')}</span></div><b>${esc(r.rating)}</b><a href="${esc(r.source_url)}" target="_blank" rel="noopener">Source ↗</a></div>`).join('')}</div>`:'';
      return `<article class="candidate-card">
        <div class="candidate-top"><div><span class="party ${String(c.party||'OTH').toLowerCase()}">${esc(partyLabel(c.party))}</span><h2>${esc(c.name)}</h2></div>
        <span class="status">${esc(st.status_label||'General Election Candidate')}</span></div>
        <p class="candidate-meta">${esc(home||'Rhode Island')} ${c.home_precinct_name?`· Home precinct ${esc(c.home_precinct_code)}`:''}</p>
        <div class="actions">
          ${campaign?`<a href="${esc(campaign)}" target="_blank" rel="noopener">Campaign website</a>`:''}
          ${email?`<a href="mailto:${esc(email)}">Email</a>`:''}
          ${phone?`<a href="tel:${esc(String(phone).replace(/[^\\d+]/g,''))}">Call</a>`:''}
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