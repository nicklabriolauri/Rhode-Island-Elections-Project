/* Shared geography and result logic for municipality maps. */
((root)=>{
 'use strict';
 const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function onSegment(p,a,b){const cross=(p[1]-a[1])*(b[0]-a[0])-(p[0]-a[0])*(b[1]-a[1]);return Math.abs(cross)<1e-12&&p[0]>=Math.min(a[0],b[0])-1e-10&&p[0]<=Math.max(a[0],b[0])+1e-10&&p[1]>=Math.min(a[1],b[1])-1e-10&&p[1]<=Math.max(a[1],b[1])+1e-10;}
 function ringContains(r,p){let hit=false;for(let i=0,j=r.length-1;i<r.length;j=i++){const a=r[i],b=r[j];if(onSegment(p,a,b))return true;if((a[1]>p[1])!==(b[1]>p[1])&&p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0])hit=!hit;}return hit;}
 function contains(g,p){if(!g||!p?.every(Number.isFinite))return false;const polygons=g.type==='Polygon'?[g.coordinates]:g.type==='MultiPolygon'?g.coordinates:[];return polygons.some(poly=>ringContains(poly[0],p)&&!poly.slice(1).some(h=>ringContains(h,p)));}
 function matchPrecinct(features,point){const matches=features.filter(f=>contains(f.geometry,point));return matches.length===1?{feature:matches[0],ambiguous:false}:{feature:null,ambiguous:matches.length>1};}
 const party=p=>({DEM:'Democrat',REP:'Republican',IND:'Independent'}[p]||'Nonpartisan');
 const partyColor=p=>({DEM:'#2e6495',REP:'#b24749',IND:'#9b7a39'}[p]||'#687f97');
 function candidateStatus(race,candidate,isOfficial=false){
  if(!race?.total_votes)return 'No votes reported';
  const sorted=[...race.candidates].sort((a,b)=>b.votes-a.votes),i=sorted.indexOf(candidate),cutoff=sorted[Math.min(race.seats,sorted.length)-1]?.votes;
  const tied=sorted.filter(c=>c.votes===cutoff).length>1;
  if(candidate.source_is_winner===true)return 'Winner (state source)';
  if(isOfficial&&!tied&&i<race.seats&&!candidate.is_write_in)return 'Elected';
  if(candidate.is_write_in)return '';
  if(race.seats===1){if(sorted[0].votes===sorted[1]?.votes)return candidate.votes===sorted[0].votes?'Tied':'';return i===0?(sorted.filter(c=>!c.is_write_in).length===1?'Unopposed ballot candidate':'Leading in returns'):'';}
  if(candidate.votes===cutoff&&tied)return 'Tied at final seat';
  return i<race.seats?`Currently in top ${race.seats}`:'';
 }
 const api={esc,contains,matchPrecinct,party,partyColor,candidateStatus};
 root.RIEPMunicipalCore=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
