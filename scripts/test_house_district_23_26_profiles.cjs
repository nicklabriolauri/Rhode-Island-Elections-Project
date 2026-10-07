const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const read=p=>fs.readFileSync(p,'utf8'),load=p=>JSON.parse(read('data/'+p+'.json'));
const finance=load('candidate_finance_2026').profiles,records=load('incumbent_records_2026').records;
const index=read('index.html'),ctx={normalizeSearchText:s=>s.toLowerCase().replace(/[^a-z0-9]+/g,' ').trim()};
vm.createContext(ctx);const start=index.indexOf('    function buildCandidateProfileHref('),end=index.indexOf('\n    function ',start+5);vm.runInContext(index.slice(start,end),ctx);
for(const [slug,name,district,votes,surname] of [
 ['william-muto','William Muto',23,'869',null],['dana-james-traversie','Dana James Traversie',23,'417',null],
 ['evan-patrick-shanley','Evan Patrick Shanley',24,'1,841','shanley'],['thomas-e-noret','Thomas E Noret',25,'741','noret'],['earl-a-read-iii','Earl A Read III',26,'1,068','read']
]){
 const page=read('candidates/'+slug+'.html');assert(page.includes(`<h1>${name}</h1>`));assert(page.includes(votes+' votes'));assert(page.includes('Official results'));
 assert(page.includes(`/running.html?chamber=house&amp;district=${district}&amp;election=general`));assert(!page.includes('Senate District'));assert(!page.includes('bffi-scorecard'));
 assert.equal(page.includes('data-voting-widget'),!!surname);assert.equal(page.includes(`current-riep-house-ranking.html#district-${district}`),!!surname);
 if(surname){
  assert(page.includes(`mailto:rep-${surname}@rilegislature.gov`));assert(page.includes(`data-candidate="${name}"`));assert(page.includes('of 75 House district records'));
  const rec=records.find(r=>r.chamber==='house'&&r.district_number===district);for(const b of rec.legislation_detail.lead_sponsored)assert(page.includes(b.bill));
 }
 const f=finance.find(f=>f.slug===slug);for(const k of ['money_raised','money_spent','ending_cash'])assert(page.includes('$'+f[k].toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})));
 assert.equal(ctx.buildCandidateProfileHref({name,chamber:'house',district_number:district}),`candidates/${slug}.html`);
 for(const route of ['ballot.html','running.html','race-page.js','candidate-profiles.html'])assert(read(route).includes(slug));
 assert(read(`races/house-${district}.html`).includes('20261006-house23-26'));
 const ids=[...page.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(ids.length,new Set(ids).size);for(const m of page.matchAll(/href="#([^"]+)"/g))assert(ids.includes(m[1]));
}
assert(read('candidates/william-muto.html').includes('52.25%'));assert(read('candidates/william-muto.html').includes('Ward 6 city councilman'));
assert(read('candidates/evan-patrick-shanley.html').includes('Warwick, East Greenwich'));assert(!read('candidates/evan-patrick-shanley.html').includes('href="https://rilaborlaw.com/attorneys/evan-shanley/"'));
assert(read('candidates/thomas-e-noret.html').includes('Coventry, West Warwick'));assert(read('candidates/earl-a-read-iii.html').includes('Coventry, West Warwick, Warwick'));
const race=load('whos_running_2026').chambers.house['23'];assert.deepEqual(race.candidates.filter(c=>c.on_election_ballot).map(c=>c.name).sort(),['Dana James Traversie','William Muto']);
console.log('PASS: five D23–26 profiles, official primaries, incumbent-only legislative data, finance, suffix-aware routes and competitive D23 roster');
