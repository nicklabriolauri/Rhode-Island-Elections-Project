const fs=require('fs'),assert=require('assert/strict');
const read=p=>fs.readFileSync(p,'utf8');
const research=JSON.parse(read('data/candidate_research_2026_with_endorsements.json')).candidates;
const finance=JSON.parse(read('data/candidate_finance_2026.json')).profiles;
for(const [slug,name,district,votes,incumbent] of [
 ['david-a-bennett','David A Bennett',20,'1,371',true],
 ['marie-a-hopkins','Marie A Hopkins',21,'418',true],
 ['zakary-j-pereira','Zakary J Pereira',22,'1,133',false],
 ['barbara-quigley','Barbara Quigley',22,'402',false]
]){
 const page=read('candidates/'+slug+'.html');
 assert(page.includes(`<h1>${name}</h1>`));assert(page.includes(votes+' votes'));
 assert(page.includes('Official results'));assert(page.includes('/ballot-items/'));
 assert(page.includes(`/running.html?chamber=house&amp;district=${district}&amp;election=general`));
 assert.equal(page.includes('data-voting-widget'),incumbent);
 assert.equal(page.includes(`current-riep-house-ranking.html#district-${district}`),incumbent);
 assert(!page.includes('bffi-scorecard'));assert(!page.includes('Senate District'));
 const fin=finance.find(f=>f.slug===slug);
 for(const key of ['money_raised','money_spent','ending_cash'])assert(page.includes('$'+fin[key].toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})));
 const ids=[...page.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(ids.length,new Set(ids).size);
 for(const m of page.matchAll(/href="#([^"]+)"/g))assert(ids.includes(m[1]));
 for(const route of ['ballot.html','running.html','race-page.js','candidate-profiles.html'])assert(read(route).includes(slug));
 assert(read(`races/house-${district}.html`).includes('20261006-house20-22'));
}
const q=research.find(c=>c.candidate_id==='house-22-rep-primary-barbara-quigley');
assert.equal(q.campaign_website,'https://quigleyforri.com/');assert.equal(q.priorities.length,4);
for(const p of q.priorities){assert.equal(p.source_url,q.campaign_website);assert(read('candidates/barbara-quigley.html').includes(p.title));}
const p=read('candidates/zakary-j-pereira.html');assert(p.includes('70.24%'));assert(p.includes('mailto:ZakaryForRI@gmail.com'));assert(p.includes('(401) 287-8451'));assert(!p.includes('tel:+1"'));assert(!p.includes('mailto:"'));assert(p.includes('June 22, 2026 to August 11, 2026'));
const roster=JSON.parse(read('data/whos_running_2026.json')).chambers.house['22'];
assert.deepEqual(roster.candidates.filter(c=>c.on_election_ballot).map(c=>c.name).sort(),['Barbara Quigley','Zakary J Pereira']);
console.log('PASS: D20–22 profiles, incumbent-only legislative metrics, official primaries, Quigley priorities, contacts, finance periods and routes');
