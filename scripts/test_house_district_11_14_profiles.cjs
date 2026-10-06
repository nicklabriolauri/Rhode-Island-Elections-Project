const fs=require('fs'),assert=require('assert/strict'),vm=require('vm');
const configs=[['grace-diaz','Grace Diaz',11,true,1456,'100%'],['arlette-hidalgo','Arlette Hidalgo',12,false,851,'55.69%'],['ramon-perez','Ramon Perez',13,true,1008,'100%'],['derick-a-reels','Derick A Reels',13,false,125,'100%'],['charlene-m-lima','Charlene M Lima',14,true,627,'57.10%']];
const records=JSON.parse(fs.readFileSync('data/incumbent_records_2026.json')).records;
const finances=JSON.parse(fs.readFileSync('data/candidate_finance_2026.json')).profiles;
const roster=JSON.parse(fs.readFileSync('data/whos_running_2026.json')).chambers.house;
const registry=JSON.parse(fs.readFileSync('ballot.html','utf8').match(/const candidateProfile = \((\{.*?\})\)\[candidate.candidate_id\]/)[1]);
const index=fs.readFileSync('index.html','utf8'),ctx={normalizeSearchText:s=>s.toLowerCase().replace(/[^a-z0-9]+/g,' ').trim()};vm.createContext(ctx);
const start=index.indexOf('    function buildCandidateProfileHref(');vm.runInContext(index.slice(start,index.indexOf('\n    function ',start+5)),ctx);
for(const [slug,name,district,incumbent,votes,share] of configs){
 const page=fs.readFileSync('candidates/'+slug+'.html','utf8');
 const candidate=roster[district].candidates.find(c=>c.name===name);
 assert(page.includes(`<h1>${name}</h1>`));assert(page.includes(`House District ${district}`));assert(page.includes(`href="/races/house-${district}.html"`));
 assert(!page.includes('Anthony J DeSimone'));assert(!page.includes('District 5'));assert(!page.includes('Senate District'));
 assert(fs.existsSync('candidates/'+slug+'.png'));assert(page.includes(`src="${slug}.png"`));assert(!page.includes('Photo under construction'));
 const ids=[...page.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(ids).size,ids.length,'unique HTML IDs');
 for(const m of page.matchAll(/href="#([^"]+)"/g))assert(ids.includes(m[1]),'valid profile section '+m[1]);
 const primary=page.slice(page.indexOf('id="primaries"'),page.indexOf('id="finance"'));
 assert(primary.includes(votes.toLocaleString('en-US')+' votes'));assert(primary.includes(share));assert(primary.includes('Official results'));assert(primary.includes('/ballot-items/'));assert(!primary.includes('Unofficial'));
 assert.equal(registry[candidate.candidate_id],slug);
 assert.equal(ctx.buildCandidateProfileHref({name,chamber:'house',district_number:district}),`candidates/${slug}.html`);
 for(const f of ['running.html','race-page.js'])assert(fs.readFileSync(f,'utf8').includes('":"'+slug+'"'));
 assert(fs.readFileSync('candidate-profiles.html','utf8').includes(`href="candidates/${slug}.html"`));
 if(incumbent){
  const rec=records.find(r=>r.candidate_id===candidate.candidate_id);assert(rec);
  assert(page.includes('Democrat · Incumbent'));assert(page.includes(`data-candidate="${name}"`));assert(page.includes('house-voting-patterns/pilot.js'));assert(page.includes('riep-legislative-index'));assert(page.includes('of 75 House district records'));
  assert(page.includes('current-riep-house-ranking.html#district-'+district));
  for(const bill of rec.legislation_detail.lead_sponsored)assert(page.includes(bill.bill));
 }else{
  assert(page.includes((candidate.party==='REP'?'Republican':'Democratic')+' · Candidate'));
  assert(page.includes('General Assembly record not applicable'));assert(!page.includes('data-voting-widget'));assert(!page.includes('riep-legislative-index'));assert(!page.includes('House record rank'));
 }
 const finance=page.slice(page.indexOf('id="finance"'),page.indexOf('id="record"')),fin=finances.find(r=>r.slug===slug);
 if(slug==='derick-a-reels'){assert(finance.includes('No financial summary'));assert(!finance.includes('$0.00'));}
 else for(const key of ['money_raised','money_spent','ending_cash'])assert(finance.includes('$'+fin[key].toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})));
}
for(const district of [11,12,13,14])assert(fs.readFileSync(`races/house-${district}.html`,'utf8').includes('race-page.js?v=20261006-house11-14'));
console.log('PASS: five House profiles, official primary totals, portraits, incumbent/challenger records, finance coverage and entry links');
