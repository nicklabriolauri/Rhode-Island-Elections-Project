const fs=require('fs'),assert=require('assert/strict');
const read=p=>fs.readFileSync(p,'utf8');
const roster=JSON.parse(read('data/whos_running_2026.json')).chambers.house['15'].candidates;
const registry=JSON.parse(read('ballot.html').match(/const candidateProfile = \((\{.*?\})\)\[candidate.candidate_id\]/)[1]);
const section=(s,id)=>s.match(new RegExp('<section class="card" id="'+id+'">[\\s\\S]*?</section>'))[0];
assert.equal(roster.length,3);
for(const c of roster){
 const slug=registry[c.candidate_id],s=read('candidates/'+slug+'.html');
 assert(s.includes('<h1>'+c.name+'</h1>'));
 assert(s.includes('House District 15'));assert(!s.includes('Providence'));
 assert(s.includes('/races/house-15.html'));
 assert(fs.existsSync('candidates/'+slug+'.png'));
 assert(read('candidate-profiles.html').includes('href="candidates/'+slug+'.html"'));
 assert(read('race-page.js').includes('"'+c.candidate_id+'":"'+slug+'"'));
 const ids=[...s.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(ids).size,ids.length);
 for(const m of s.matchAll(/href="#([^"]+)"/g))assert(ids.includes(m[1]),m[1]);
 assert(!s.includes('bffi-scorecard'));
 if(c.party==='REP'){
  assert(s.includes('Republican · Incumbent · Cranston'));assert(!s.includes('Democratic'));
  assert(section(s,'primaries').includes('575 votes'));assert(section(s,'primaries').includes('Uncontested Republican'));
  assert(s.includes('data-candidate="Christopher G Paplauskas"'));assert(s.includes('current-riep-house-ranking.html#district-15'));
  assert(s.includes('$28,314.70'));assert(s.includes('No 2023–2024 CEL score'));
 }else{
  assert(!s.includes('data-voting-widget'));assert(!s.includes('class="riep-progress"'));
  assert(section(s,'finance').includes('Missing figures are not treated as zero'));
  assert(!s.includes('rep-paplauskas'));assert(!s.includes('$28,314.70'));
  if(c.party==='DEM')assert(section(s,'primaries').includes('1,258 votes'));
  else{
   assert(s.includes('Independent · Candidate · Cranston'));assert(!s.includes('Independent Socialist'));
   assert(section(s,'primaries').includes('a party-primary vote total is not assigned'));assert(!section(s,'primaries').includes('votes</strong>'));
   assert(section(s,'about').includes('mayor of Cranston from 2009 to 2021'));
   assert(section(s,'finance').includes('/finance-candidates/'+c.candidate_id+'.html'));
   assert(!section(s,'elections').includes('Fenton-Fung'));assert(!section(s,'elections').includes('Districtwide general election'));
  }
 }
}
assert(read('races/house-15.html').includes('race-page.js?v=20261006-house15'));
console.log('PASS: District 15 three-party profiles, incumbent-only scores, official primary returns, Independent finance and history, portraits and navigation');
