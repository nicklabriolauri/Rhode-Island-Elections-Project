const assert=require('node:assert/strict'),fs=require('fs');
const C=require('../municipal-map-core.js');
const p=JSON.parse(fs.readFileSync('data/cranston/precincts.geojson')).features;
for(const f of p){const m=C.matchPrecinct(p,f.properties.label);assert(!m.ambiguous);assert.equal(m.feature.properties.precinct,f.properties.precinct);}
assert.equal(C.matchPrecinct(p,[-71.2,41.8]).feature,null);
const hole={type:'Polygon',coordinates:[[[0,0],[4,0],[4,4],[0,4],[0,0]],[[1,1],[3,1],[3,3],[1,3],[1,1]]]};
assert(C.contains(hole,[.5,.5]));assert(!C.contains(hole,[2,2]));assert(!C.contains(hole,[NaN,1]));
const square={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,1],[0,0]]]};assert(C.matchPrecinct([{geometry:square},{geometry:square}],[.5,.5]).ambiguous);
const c=[{name:'A',votes:60},{name:'B',votes:40}],r={total_votes:100,seats:1,candidates:c};
assert.equal(C.candidateStatus(r,c[0],false),'Leading in returns');assert.equal(C.candidateStatus(r,c[0],true),'Elected');
c[1].votes=60;assert.equal(C.candidateStatus(r,c[0],false),'Tied');
const cs=[100,90,80,80,20].map((votes,i)=>({name:String(i),votes}));const multi={total_votes:370,seats:3,candidates:cs};
assert.equal(C.candidateStatus(multi,cs[2]),'Tied at final seat');assert.equal(C.candidateStatus(multi,cs[0]),'Currently in top 3');
console.log('PASS: all 27 precinct address matches; holes and outside points; boundary ambiguity; unofficial leads; ties; multi-seat cutoff.');
