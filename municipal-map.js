/* Data-driven municipal atlas. Election returns and current service are separate views. */
(()=>{
 'use strict';
 const $=id=>document.getElementById(id),C=window.RIEPMunicipalCore,esc=C.esc;
 const slug=document.body.dataset.municipality;
 if(!/^[a-z-]+$/.test(slug))return;
 const base=`/data/${slug}/`,params=new URLSearchParams(location.search);
 const palette=['#b3c9dd','#e0bd98','#c6d1a4','#c9b5d9','#9cc8c1','#e2c1c9','#d9cf9e','#b8bddb','#b5d4ba'];
 let data,wards,precincts,roads,context,water,map,wardLayer,precinctLayer,roadsLayer,marker;
 let selected=0,selectedPrecinct=null,mapView='wards',colorView='wards',info='results',office='council',fullRoads=false;
 const wardLabels=new Map(),precinctLabels=new Map(),districtLabels=new Map(),roadLabels=[];
 const status=$('address-status');
 const number=n=>Number(n).toLocaleString('en-US');
 const pct=n=>n==null?'—':`${Number(n).toFixed(1)}%`;
 const date=value=>new Date(value).toLocaleString('en-US',{timeZone:'America/New_York',month:'short',day:'numeric',year:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'});
 const wardFeature=w=>wards.features.find(f=>f.properties.ward===Number(w));
 const wardPrecincts=w=>precincts.features.filter(f=>f.properties.ward===Number(w));
 const race=(o,w)=>data.results.races.find(r=>r.office===o&&r.ward===w);
 const leader=r=>r?.candidates[0];
 function turnout(w){const ps=wardPrecincts(w),voted=ps.reduce((s,p)=>s+p.properties.voted_2024,0),eligible=ps.reduce((s,p)=>s+p.properties.eligible_2024,0);return{voted,eligible,pct:eligible?voted/eligible*100:null};}
 const stateHref=(chamber,d)=>`/general-results.html?chamber=${chamber}&district=${d}`;
 const sourceLink=(href,label)=>`<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>`;
 function updateURL(){const p=new URLSearchParams();if(selected)p.set('ward',selected);if(selectedPrecinct)p.set('precinct',selectedPrecinct);if(mapView!=='wards')p.set('map',mapView);if(colorView!=='wards')p.set('colors',colorView);if(info!=='results')p.set('info',info);if(office!=='council')p.set('office',office);history.replaceState(null,'',location.pathname+(p.size?'?'+p:''));}
 function renderRace(r,compact=false){
  if(!r)return '<p>Election returns have not been added.</p>';
  return `<div class="race-results"><h3 class="race-heading">${esc(r.ward?`Ward ${r.ward} ${r.office==='council'?'council':'school committee'}`:`Citywide ${r.office==='council'?'council':'school committee'}`)}</h3><p class="result-date">November 3, 2026 · ${data.results.is_official?'Official':'Unofficial'} returns${r.seats>1?` · ${r.seats} seats`:''}</p>${r.candidates.map(c=>`<div class="race-candidate"><div class="candidate-line"><div class="candidate-name"><strong>${esc(c.name)}</strong><span class="candidate-sub">${esc(c.is_write_in?'Write-in':C.party(c.party))}</span>${C.candidateStatus(r,c,data.results.is_official)?`<span class="tag">${esc(C.candidateStatus(r,c,data.results.is_official))}</span>`:''}</div><div class="candidate-stats"><strong>${pct(c.share)}</strong><span class="candidate-sub">${number(c.votes)} votes</span></div></div><div class="result-bar" aria-hidden="true"><span style="width:${c.share||0}%;background:${C.partyColor(c.party)}"></span></div></div>`).join('')}<p class="race-note">${r.seats>1?'Shares are percentages of candidate votes, including write-ins. Voters could select up to three candidates, so these are not percentages of participating voters.':'Shares include write-in votes.'} ${!data.results.is_official?'A lead is not a race call or certification.':''}</p>${sourceLink(r.source_url,'Official state returns')}</div>`;
 }
 function renderCurrent(){const current=data.current_officeholders[String(selected)],o=current[office];return `<h3>${office==='council'?'Current ward councilor':'Current ward school-committee member'}</h3><article class="representative"><strong>${esc(o.name)}</strong>${o.party?`<span class="candidate-sub">${esc(C.party(o.party==='D'?'DEM':o.party==='R'?'REP':o.party))}</span>`:''}${o.email?`<a href="mailto:${esc(o.email)}">${esc(o.email)}</a>`:''}</article><p class="race-note">Listed by the city as of November 19, 2026.${office==='council'?' The current council’s term ends January 4, 2027.':''} New election returns are shown separately.</p>${sourceLink(data.sources[office],'City member directory')}`;}
 function renderPrecinct(){if(!selectedPrecinct)return '';const p=precincts.features.find(f=>f.properties.precinct===selectedPrecinct)?.properties;if(!p)return '';return `<section class="selected-precinct"><p class="eyebrow">Selected precinct</p><h3>${esc(p.local_label)} <span class="candidate-sub">State precinct ${esc(p.precinct)}</span></h3><p class="small">Ward ${p.ward} · U.S. House District ${p.congress}</p><div class="district-links"><a href="${stateHref('house',p.house)}">House ${p.house}: 2026 results</a><a href="${stateHref('senate',p.senate)}">Senate ${p.senate}: 2026 results</a></div><p class="small">2024 turnout: <strong>${pct(p.voted_2024/p.eligible_2024*100)}</strong> (${number(p.voted_2024)} of ${number(p.eligible_2024)} eligible voters).</p><details><summary>City GIS-listed polling location</summary><p class="small" style="margin-top:10px">${esc(p.polling_place)}<br>${esc(p.polling_address)}</p><p class="small">This is a map reference, not confirmation of your polling location for a particular election. ${sourceLink(data.sources.state_lookup,'Check the official voter lookup')}.</p></details></section>`;}
 function renderDetail(){
  const f=wardFeature(selected);if(!f)return;const p=f.properties,t=turnout(selected);
  $('ward-detail').innerHTML=`<div class="ward-head"><h2>Ward ${selected}</h2><span class="ward-swatch" style="background:${p.color}" aria-hidden="true"></span></div><p class="ward-meta">${p.precinct_count} precincts · Council &amp; school committee<br>2024 turnout: ${pct(t.pct)}</p><nav class="tabs" aria-label="Ward information"><button type="button" data-info="results" aria-pressed="${info==='results'}">2026 results</button><button type="button" data-info="current" aria-pressed="${info==='current'}">Current representatives</button></nav><nav class="office-tabs" aria-label="Local office"><button type="button" data-office="council" aria-pressed="${office==='council'}">Council</button><button type="button" data-office="school" aria-pressed="${office==='school'}">School committee</button></nav>${info==='results'?renderRace(race(office,selected)):renderCurrent()}${office==='council'&&info==='results'?(window.RIEPLocalRepresentation?.profiles||[]).filter(o=>o.municipality==='Cranston'&&o.ward===selected).map(o=>`<section class="riep-local-group"><h3>2026 winner profile</h3>${window.RIEPLocalRepresentation.renderProfile(o)}</section>`).join(''):''}${renderPrecinct()}<section><h3>Explore this ward’s precincts</h3><p class="small">Local labels match the adopted PDF. The four-digit number is the state precinct code.</p><div class="precinct-pills">${wardPrecincts(selected).sort((a,b)=>a.properties.local_label.localeCompare(b.properties.local_label)).map(f=>`<button type="button" data-precinct="${esc(f.properties.precinct)}" aria-pressed="${selectedPrecinct===f.properties.precinct}">${esc(f.properties.local_label)} · ${esc(f.properties.precinct)}</button>`).join('')}</div><h3>State districts in this ward</h3><div class="district-links">${p.house.map(d=>`<a href="${stateHref('house',d)}">House ${d}</a>`).join('')}${p.senate.map(d=>`<a href="${stateHref('senate',d)}">Senate ${d}</a>`).join('')}</div><p class="small">A ward can cross several state districts. Select a precinct or search an address for its specific assignments.</p></section>`;
  $('ward-detail').querySelectorAll('[data-info]').forEach(b=>b.onclick=()=>{info=b.dataset.info;renderDetail();updateURL();});
  $('ward-detail').querySelectorAll('[data-office]').forEach(b=>b.onclick=()=>{office=b.dataset.office;renderDetail();updateURL();});
  $('ward-detail').querySelectorAll('[data-precinct]').forEach(b=>b.onclick=()=>selectPrecinct(b.dataset.precinct,true));
 }
 function profileLink(w,name){const p=(window.RIEPLocalRepresentation?.profiles||[]).find(p=>p.municipality==='Cranston'&&p.ward===w);return p?`<a href="${esc(p.profile)}">${esc(name)}</a>`:esc(name);}
 function renderOverview(){
  $('ward-list').innerHTML=wards.features.map(f=>`<button type="button" data-ward="${f.properties.ward}" style="--ward-color:${f.properties.color}" aria-pressed="${f.properties.ward===selected}">Ward ${f.properties.ward}</button>`).join('');
  $('ward-overview').innerHTML=wards.features.map(f=>{const p=f.properties,c=race('council',p.ward),s=race('school',p.ward);return `<tr><td><button type="button" class="ward-table-button" data-ward="${p.ward}">Ward ${p.ward}</button></td><td>${p.precinct_count}</td><td>${esc(data.current_officeholders[p.ward].council.name)}</td><td>${profileLink(p.ward,leader(c)?.name)}<span class="candidate-sub">${pct(leader(c)?.share)} · ${esc(C.candidateStatus(c,leader(c),data.results.is_official))}</span></td><td>${esc(leader(s)?.name)}<span class="candidate-sub">${pct(leader(s)?.share)} · ${esc(C.candidateStatus(s,leader(s),data.results.is_official))}</span></td></tr>`;}).join('');
  document.querySelectorAll('[data-ward]').forEach(b=>b.onclick=()=>{selectWard(Number(b.dataset.ward),true);if(b.closest('table'))$('ward-detail').scrollIntoView({behavior:'smooth',block:'start'});});
  const city=data.citywide_officeholders;
  $('citywide-current').innerHTML=`<div class="citywide-grid"><div class="citywide-group"><h3>Current mayor</h3><p>${esc(city.mayor.name)}</p><p class="small">Mayor is not on the 2026 general-election ballot.</p></div><div class="citywide-group"><h3>Current citywide councilors</h3>${city.council.map(n=>`<p>${esc(n)}</p>`).join('')}</div><div class="citywide-group"><h3>Current citywide school member</h3>${city.school.map(n=>`<p>${esc(n)}</p>`).join('')}</div></div><p class="small" style="margin:16px 0 0">City directory and GIS snapshot reviewed November 19, 2026. These are current officeholders, not a list of 2026 election winners.</p>`;
  $('citywide-results').innerHTML=renderRace(race('council',null))+renderRace(race('school',null));
  $('source-date').textContent=`Vote totals as of ${date(data.results.as_of)}. ${data.results.is_official?'Official':'Unofficial'} results from the Rhode Island Board of Elections. This page does not update automatically.`;
 }
 function colorForWard(w){if(colorView==='returns'){const r=race('council',w);return r.candidates[0]?.votes===r.candidates[1]?.votes?'#c4cbd2':C.partyColor(leader(r)?.party);}if(colorView==='turnout'){const t=turnout(w).pct;return t>=65?'#224c72':t>=55?'#5982a7':t>=45?'#9bb9d1':'#d5e3ed';}return wardFeature(w)?.properties.color||'#b4c5d8';}
 function wardStyle(f){const w=f.properties.ward,active=w===selected;return {color:active?'#172d4c':'#667785',weight:active?3:1.3,fillColor:colorForWard(w),fillOpacity:mapView==='house'||mapView==='senate'?0:mapView==='precincts'?.14:active?.64:.43};}
 function districtColor(p){const values=[...new Set(precincts.features.map(f=>f.properties[mapView]))].sort((a,b)=>a-b);return palette[values.indexOf(p[mapView])%palette.length];}
 function precinctStyle(f){const p=f.properties,active=p.precinct===selectedPrecinct,state=mapView==='house'||mapView==='senate';return{color:active?'#182b4d':state?'#ffffff':'#5a6678',weight:active?3:state?.35:.9,fillColor:state?districtColor(p):colorForWard(p.ward),fillOpacity:state?.76:active?.60:mapView==='precincts'?.38:.12,dashArray:state||active?null:'3 3'};}
 function labelMarker(latlng,cls,html,size=[30,30]){return L.marker(latlng,{interactive:false,keyboard:false,icon:L.divIcon({className:cls,html,iconSize:size,iconAnchor:[size[0]/2,size[1]/2]})});}
 function renderLegend(){
  const box=$('map-legend');
  if(mapView==='house'||mapView==='senate'){const ids=[...new Set(precincts.features.map(f=>f.properties[mapView]))].sort((a,b)=>a-b);box.innerHTML=ids.map((d,i)=>`<span><i style="background:${palette[i%palette.length]}"></i>${mapView==='house'?'House':'Senate'} ${d}</span>`).join('');}
  else if(colorView==='returns')box.innerHTML=`<span><i style="background:${C.partyColor('DEM')}"></i>Democratic lead</span><span><i style="background:${C.partyColor('REP')}"></i>Republican lead</span><span>Unofficial council returns. No independent race calls.</span>`;
  else if(colorView==='turnout')box.innerHTML=['Under 45%','45–54.9%','55–64.9%','65% or more'].map((v,i)=>`<span><i style="background:${['#d5e3ed','#9bb9d1','#5982a7','#224c72'][i]}"></i>${v}</span>`).join('');
  else box.innerHTML=wards.features.map(f=>`<span><i style="background:${f.properties.color}"></i>Ward ${f.properties.ward}</span>`).join('');
 }
 function refreshMap(){
  document.querySelectorAll('[data-ward]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.ward)===selected)));
  renderLegend();if(!map)return;
  const state=mapView==='house'||mapView==='senate',showPrecincts=mapView!=='wards'||map.getZoom()>=13.75;
  wardLayer.setStyle(wardStyle);precinctLayer.setStyle(precinctStyle);
  if(showPrecincts&&!map.hasLayer(precinctLayer))precinctLayer.addTo(map);else if(!showPrecincts&&map.hasLayer(precinctLayer))map.removeLayer(precinctLayer);
  // State colors must remain above ward fills; the selected ward outline stays visible.
  if(showPrecincts)precinctLayer.bringToFront();wardLayer.bringToFront();
  wardLabels.forEach((l,w)=>{if(!state&&!map.hasLayer(l))l.addTo(map);if(state&&map.hasLayer(l))map.removeLayer(l);l.getElement()?.classList.toggle('selected',w===selected);});
  precinctLabels.forEach(l=>{const show=!state&&showPrecincts&&map.getZoom()>=14.4;if(show&&!map.hasLayer(l))l.addTo(map);if(!show&&map.hasLayer(l))map.removeLayer(l);});
  districtLabels.forEach((entry,key)=>{const show=key.startsWith(mapView+'-');if(show&&!map.hasLayer(entry))entry.addTo(map);if(!show&&map.hasLayer(entry))map.removeLayer(entry);});
  const details=map.getZoom()>=13.1;
  if(details!==fullRoads){fullRoads=details;roadsLayer.clearLayers();roadsLayer.addData(details?roads:{type:'FeatureCollection',features:roads.features.filter(f=>/Route|Park Avenue|Reservoir|Pontiac|Scituate Avenue|Cranston Street|Broad Street|Oaklawn|Phenix|New London/i.test(f.properties.name))});}
  roadLabels.forEach(l=>{if(map.getZoom()>=14.8&&!map.hasLayer(l))l.addTo(map);if(map.getZoom()<14.8&&map.hasLayer(l))map.removeLayer(l);});
  $('color-view').disabled=state;
  $('map-caption').textContent=state?`${mapView==='house'?'House':'Senate'} districts shown only within Cranston. Select a precinct for its 2026 results.`:'Council and school-committee wards use the same boundaries.';
  $('map-hint').textContent=state?'Colors identify state districts, not parties. Select an area for its precinct and ward.':showPrecincts?'Precinct boundaries are visible. Zoom closer for state precinct codes.':'Select a ward to explore it. Zoom in for precinct boundaries and streets.';
 }
 function selectWard(w,zoom=false){if(!wardFeature(w))return;selected=w;selectedPrecinct=null;renderDetail();refreshMap();if(zoom&&map)wardLayer.eachLayer(l=>{if(l.feature.properties.ward===w)map.fitBounds(l.getBounds(),{padding:[28,28],maxZoom:14.4});});updateURL();}
 function selectPrecinct(id,zoom=false){const f=precincts.features.find(f=>f.properties.precinct===id);if(!f)return;selected=f.properties.ward;selectedPrecinct=id;renderDetail();refreshMap();if(zoom&&map)precinctLayer.eachLayer(l=>{if(l.feature.properties.precinct===id)map.fitBounds(l.getBounds(),{padding:[35,35],maxZoom:15.4});});updateURL();}
 function makeMap(){
  if(!window.L){$('municipal-map').innerHTML='<div class="map-error">The interactive map could not load. Use the ward buttons, overview table, and official PDF maps below.</div>';$('municipal-map').setAttribute('aria-busy','false');return;}
  $('municipal-map').replaceChildren();map=L.map('municipal-map',{scrollWheelZoom:false,zoomSnap:.25,minZoom:10,maxZoom:18});
  [['context',200],['water',250],['roads',300],['wards',400],['precincts',420],['labels',600]].forEach(([n,z])=>{map.createPane(n);map.getPane(n).style.zIndex=z;if(n==='roads'||n==='water'||n==='labels'||n==='context')map.getPane(n).style.pointerEvents='none';});
  const canvas=L.canvas({pane:'roads',padding:.5});
  L.geoJSON(context,{pane:'context',interactive:false,style:f=>({color:'#ccd5dc',weight:1,fillColor:f.properties.name==='Cranston'?'#ffffff':'#f1f3f4',fillOpacity:1})}).addTo(map);
  const townLabels=new Map();context.features.forEach(f=>{const n=f.properties.name;if(n==='Cranston')return;const b=L.geoJSON(f).getBounds(),area=(b.getEast()-b.getWest())*(b.getNorth()-b.getSouth());if(!townLabels.has(n)||area>townLabels.get(n).area)townLabels.set(n,{area,feature:f});});townLabels.forEach(({feature:f})=>{const p=f.properties.label;labelMarker([p[1],p[0]],'town-label',`<span>${esc(f.properties.name)}</span>`,[150,18]).addTo(map);});
  L.geoJSON(water,{pane:'water',interactive:false,style:{color:'#d2e1ea',weight:.4,fillColor:'#e2edf4',fillOpacity:1}}).addTo(map);
  const major=roads.features.filter(f=>/Route|Park Avenue|Reservoir|Pontiac|Scituate Avenue|Cranston Street|Broad Street|Oaklawn|Phenix|New London/i.test(f.properties.name));
  roadsLayer=L.geoJSON({type:'FeatureCollection',features:major},{pane:'roads',renderer:canvas,interactive:false,style:f=>({color:f.properties.in_city?'#a4afb7':'#d6dce0',weight:/Route/.test(f.properties.name)?1.6:.75,opacity:f.properties.in_city?.85:.55})}).addTo(map);
  wardLayer=L.geoJSON(wards,{pane:'wards',style:wardStyle,onEachFeature:(f,l)=>{l.bindTooltip(`Ward ${f.properties.ward}<br>${f.properties.precinct_count} precincts`,{sticky:true});l.on('click',()=>selectWard(f.properties.ward,true));}}).addTo(map);
  precinctLayer=L.geoJSON(precincts,{pane:'precincts',style:precinctStyle,onEachFeature:(f,l)=>{const p=f.properties;l.bindTooltip(`<strong>Precinct ${esc(p.local_label)} · ${esc(p.precinct)}</strong><br>Ward ${p.ward} · House ${p.house} · Senate ${p.senate}`,{sticky:true});l.on('click',()=>selectPrecinct(p.precinct));}});
  wards.features.forEach(f=>{const p=f.properties,l=labelMarker([p.label[1],p.label[0]],'local-label',`<span>${p.ward}</span>`);wardLabels.set(p.ward,l);});
  precincts.features.forEach(f=>{const p=f.properties;precinctLabels.set(p.precinct,labelMarker([p.label[1],p.label[0]],'precinct-label',`<span>${esc(p.precinct)}</span>`,[44,20]));});
  for(const kind of ['house','senate']){const ids=[...new Set(precincts.features.map(f=>f.properties[kind]))];ids.forEach(id=>{const ps=precincts.features.filter(f=>f.properties[kind]===id);const p=ps.sort((a,b)=>b.properties.eligible_2024-a.properties.eligible_2024)[0].properties;districtLabels.set(`${kind}-${id}`,labelMarker([p.label[1],p.label[0]],'district-label',`<span>${kind==='house'?'HD':'SD'} ${id}</span>`,[65,25]));});}
  const byRoad=new Map();major.forEach(f=>{if(!byRoad.has(f.properties.name))byRoad.set(f.properties.name,f);});[...byRoad.values()].slice(0,16).forEach(f=>{const cs=f.geometry.type==='MultiLineString'?f.geometry.coordinates[0]:f.geometry.coordinates,p=cs[Math.floor(cs.length/2)];roadLabels.push(labelMarker([p[1],p[0]],'road-label',`<span>${esc(f.properties.name)}</span>`,[120,16]));});
  map.fitBounds(wardLayer.getBounds().pad(.10));map.on('zoomend',refreshMap);L.control.scale({metric:false,imperial:true}).addTo(map);
  map.attributionControl.addAttribution('Boundaries &amp; roads: City of Cranston · Context: RIGIS');$('municipal-map').setAttribute('aria-busy','false');
  // Provide accessible feature names and keyboard selection in addition to the ward list.
  wardLayer.eachLayer(l=>{const el=l.getElement();if(!el)return;el.setAttribute('tabindex','0');el.setAttribute('role','button');el.setAttribute('aria-label',`Select Cranston Ward ${l.feature.properties.ward}`);el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectWard(l.feature.properties.ward,true);}});});
 }
 function matchAddress(candidate){
  const point=[candidate.location.x,candidate.location.y],match=C.matchPrecinct(precincts.features,point);$('address-matches').replaceChildren();
  if(match.ambiguous){status.textContent='This point is on a precinct boundary. Please confirm the assignment with the official voter lookup.';return;}
  if(!match.feature){status.textContent='That address is outside the mapped Cranston precincts. Try another Cranston address or choose a ward manually.';return;}
  const p=match.feature.properties;selectPrecinct(p.precinct,true);
  if(map){if(marker)map.removeLayer(marker);marker=L.circleMarker([point[1],point[0]],{radius:7,color:'#fff',weight:3,fillColor:'#172b4d',fillOpacity:1}).addTo(map).bindTooltip('Matched address');}
  status.textContent=`${candidate.address}: Ward ${p.ward}, precinct ${p.precinct} (${p.local_label}), House ${p.house}, Senate ${p.senate}. Confirm election-specific assignments with the official voter lookup.`;
 }
 $('address-form').addEventListener('submit',async event=>{
  event.preventDefault();if(!precincts){status.textContent='Map data is still loading.';return;}const input=$('address').value.trim();if(!input)return;
  $('find-button').disabled=true;status.textContent='Finding matching Cranston addresses…';$('address-matches').replaceChildren();
  try{const q=new URLSearchParams({SingleLine:/cranston/i.test(input)?input:input+', Cranston, RI',sourceCountry:'USA',outSR:'4326',outFields:'Match_addr,Addr_type,City',maxLocations:5,f:'json',searchExtent:'-71.66,41.68,-71.36,41.84'});const r=await fetch('https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates?'+q,{signal:AbortSignal.timeout(18000)});if(!r.ok)throw Error();const payload=await r.json();const cs=(payload.candidates||[]).filter(c=>c.score>=85&&['PointAddress','StreetAddress'].includes(c.attributes?.Addr_type));if(!cs.length){status.textContent='No precise address match found. Include a street number and name, or choose a ward manually.';return;}status.textContent='Choose your address to see its ward and precinct.';cs.forEach(c=>{const b=document.createElement('button');b.type='button';b.textContent=c.address;b.onclick=()=>matchAddress(c);$('address-matches').append(b);});}catch{status.textContent='Address search is temporarily unavailable. The map, ward buttons, and precinct lists still work.';}finally{$('find-button').disabled=false;}
 });
 $('map-view').onchange=e=>{mapView=e.target.value;refreshMap();updateURL();};$('color-view').onchange=e=>{colorView=e.target.value;refreshMap();updateURL();};
 $('reset-map').onclick=()=>{if(!data)return;selectedPrecinct=null;if(marker&&map){map.removeLayer(marker);marker=null;}if(map)map.fitBounds(wardLayer.getBounds().pad(.10));renderDetail();refreshMap();updateURL();};
 async function json(name){const r=await fetch(base+name,{cache:'no-cache'});if(!r.ok)throw Error(`Could not load ${name}`);return r.json();}
 Promise.all([...['overview.json','wards.geojson','precincts.geojson','roads.geojson','context.geojson','water.geojson'].map(json),window.RIEPLocalRepresentation?.ready.catch(()=>{})]).then(([d,w,p,r,c,h])=>{
  data=d;wards=w;precincts=p;roads=r;context=c;water=h;
  selected=Number(params.get('ward'));if(!wardFeature(selected))selected=1;
  if(['wards','precincts','house','senate'].includes(params.get('map')))mapView=params.get('map');if(['wards','returns','turnout'].includes(params.get('colors')))colorView=params.get('colors');if(params.get('info')==='current')info='current';if(params.get('office')==='school')office='school';
  $('map-view').value=mapView;$('color-view').value=colorView;renderOverview();makeMap();renderDetail();refreshMap();
  if(params.get('precinct'))selectPrecinct(params.get('precinct'),true);
 }).catch(error=>{console.error(error);$('municipal-map').innerHTML=`<div class="map-error"><h2>Map data could not load</h2><p>Please reload, or ${sourceLink('https://www.cranstonri.gov/departments/canvassing-department/voting-districts-and-district-maps/','open the official Cranston maps')}.</p></div>`;$('municipal-map').setAttribute('aria-busy','false');status.textContent='Map data is unavailable. Please reload or use the official city maps.';});
})();
