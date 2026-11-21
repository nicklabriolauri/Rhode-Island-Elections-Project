/* Municipal profiles share one precinct registry across address-search entry points. */
(function(root){
 'use strict';
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 let registry={profiles:[],municipalities:{}};
 function normalizedCode(value){const s=String(value??'').trim();return /^\d{1,4}$/.test(s)?s.padStart(4,'0'):null;}
 function wardFor(municipality,precinct){const code=normalizedCode(precinct);return code&&registry.municipalities[municipality]?.precinct_wards?.[code]||null;}
 function profilesFor(municipality,precinct){const ward=wardFor(municipality,precinct);if(!ward)return [];return registry.profiles.filter(p=>p.municipality===municipality&&(p.ward==null||Number(p.ward)===Number(ward)));}
 function renderProfile(p){return `<article class="riep-local-person"><a class="riep-local-profile" href="${esc(p.profile)}">${p.photo?`<img src="${esc(p.photo)}" alt="${esc(p.name)}" width="90" height="90" loading="lazy">`:`<span class="riep-local-initials" aria-label="Portrait not yet verified">${esc(p.name.split(/\s+/).map(n=>n[0]).filter((_,i,a)=>i===0||i===a.length-1).join(''))}</span>`}<span><strong>${esc(p.name)}</strong><span>${esc(p.municipality)} ${esc(p.office)} · Ward ${esc(p.ward)}</span><span>${esc({DEM:'Democrat',REP:'Republican',IND:'Independent'}[p.party]||p.party)} · ${esc(p.status)}</span><span class="riep-local-outcome">Won the 2026 election · New term begins January 4, 2027</span><span class="riep-local-action">View profile</span></span></a>${p.finance_url ? `<a class="riep-local-finance" href="${esc(p.finance_url)}">Campaign finance</a>` : ""}</article>`;}
 function renderGroup(municipality,precinct){const ps=profilesFor(municipality,precinct);if(!ps.length)return '';const ward=wardFor(municipality,precinct);return `<section class="riep-local-group" aria-label="${esc(municipality)} Ward ${ward} local representatives"><h2>${esc(municipality)} City Council · Ward ${ward}</h2>${ps.map(renderProfile).join('')}<p>Profiles cover all six 2026 ward council winners. Citywide council and school-committee profiles are not yet included. This is not a complete list of offices on your ballot.</p><a href="/cranston-map.html?precinct=${esc(normalizedCode(precinct))}">Explore this ward and precinct</a></section>`;}
 const api={wardFor,profilesFor,renderProfile,renderGroup,get profiles(){return registry.profiles;},setRegistryForTests:d=>{registry=d;}};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 if(!root.document)return;
 root.RIEPLocalRepresentation=api;
 const style=root.document.createElement('link');style.rel='stylesheet';style.href='/local-representation.css?v=20261121-six-wards';root.document.head.append(style);
 api.ready=fetch('/data/local_representatives.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Municipal profiles unavailable');return r.json();}).then(d=>{registry=d;return d;});api.ready.catch(()=>{});
})(typeof window==='undefined'?globalThis:window);
