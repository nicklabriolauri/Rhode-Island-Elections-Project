/* Municipal profiles share one precinct registry across address-search entry points. */
(function(root){
 'use strict';
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 let registry={profiles:[],municipalities:{}};
 function normalizedCode(value){const s=String(value??'').trim();return /^\d{1,4}$/.test(s)?s.padStart(4,'0'):null;}
 function wardFor(municipality,precinct){const code=normalizedCode(precinct);return code&&registry.municipalities[municipality]?.precinct_wards?.[code]||null;}
 function profilesFor(municipality,precinct){
  const city=registry.municipalities[municipality];
  if(city?.council_scope==='citywide'){
   if(!city.precincts.includes(normalizedCode(precinct)))return [];
   const rosterField=city.term_switch_at&&Date.now()>=Date.parse(city.term_switch_at)?'elected_2026':'sitting';
   return registry.profiles.filter(p=>p.municipality===municipality&&p[rosterField]===true);
  }
  const ward=wardFor(municipality,precinct);if(!ward)return [];return registry.profiles.filter(p=>p.municipality===municipality&&(p.ward==null||Number(p.ward)===Number(ward)));}
 const mapFor=municipality=>({'Cranston':'cranston','Central Falls':'central-falls'}[municipality]);
 function mapHref(municipality,precinct){const slug=mapFor(municipality),code=normalizedCode(precinct);return slug&&wardFor(municipality,code)?'/'+slug+'-map.html?precinct='+code:null;}
 function renderProfile(p){return `<article class="riep-local-person"><a class="riep-local-profile" href="${esc(p.profile)}">${p.photo?`<img src="${esc(p.photo)}" alt="${esc(p.name)}" width="90" height="90" loading="lazy">`:`<span class="riep-local-initials" aria-label="Portrait not yet verified">${esc(p.name.split(/\s+/).map(n=>n[0]).filter((_,i,a)=>i===0||i===a.length-1).join(''))}</span>`}<span><strong>${esc(p.name)}</strong><span>${esc(p.municipality)} ${esc(p.office)} · ${p.ward==null?p.municipality==='Woonsocket'?'At-large · Citywide':p.municipality==='Central Falls'?'At-large · All five wards':'Citywide · All six wards':`Ward ${esc(p.ward)}`}</span><span>${esc({DEM:'Democrat',REP:'Republican',IND:'Independent',NON:'Nonpartisan'}[p.party]||p.party)} · ${esc(p.status)}</span><span class="riep-local-outcome">${esc(p.outcome||'Won the 2026 election · New term begins January 4, 2027')}</span><span class="riep-local-action">View profile</span></span></a>${p.finance_url ? `<a class="riep-local-finance" href="${esc(p.finance_url)}">Campaign finance</a>` : ""}</article>`;}
 function renderGroup(municipality,precinct){const ps=profilesFor(municipality,precinct);if(!ps.length)return '';
  const city=registry.municipalities[municipality];
  if(city?.council_scope==='citywide'){
   const title=esc(municipality)+' City Council';
   return `<section class="riep-local-group" aria-label="${title}"><details><summary><strong>${title} · ${ps.length} at-large councilors</strong></summary><p>Each councilor represents the entire city.</p><ul>${ps.map(p=>`<li><a href="${esc(p.profile)}">${esc(p.name)}</a></li>`).join('')}</ul><a href="${esc(city.council_url)}">Council overview and election results</a></details></section>`;
  }
  const ward=wardFor(municipality,precinct),wardMembers=ps.filter(p=>p.ward!=null),citywide=ps.filter(p=>p.ward==null),centralFalls=municipality==='Central Falls';return `<section class="riep-local-group" aria-label="${esc(municipality)} local council representatives"><h2>${esc(municipality)} City Council · Your Ward ${ward} councilor</h2>${wardMembers.map(renderProfile).join('')}${citywide.length?`<h2>${centralFalls?'At-large council · All five wards':'Citywide council · All six wards'}</h2><p>${centralFalls?'Two at-large councilors represent the entire city.':'Every Cranston voter elects these same three citywide seats, in addition to their ward councilor.'}</p>${citywide.map(renderProfile).join('')}`:''}<p>${centralFalls?'The 2026 returns are shown separately from current service. New terms begin January 4, 2027.':'Profiles cover all nine 2026 council winners. School-committee profiles are not yet included. This is not a complete list of offices on your ballot.'}</p><a href="${esc(mapHref(municipality,precinct))}">Explore this ward and precinct</a></section>`;}

 const api={mapHref,wardFor,profilesFor,renderProfile,renderGroup,get profiles(){return registry.profiles;},setRegistryForTests:d=>{registry=d;}};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 if(!root.document)return;
 root.RIEPLocalRepresentation=api;
 const style=root.document.createElement('link');style.rel='stylesheet';style.href='/local-representation.css?v=20261121-citywide';root.document.head.append(style);
 api.ready=fetch('/data/local_representatives.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Municipal profiles unavailable');return r.json();}).then(d=>{registry=d;return d;});api.ready.catch(()=>{});
})(typeof window==='undefined'?globalThis:window);
