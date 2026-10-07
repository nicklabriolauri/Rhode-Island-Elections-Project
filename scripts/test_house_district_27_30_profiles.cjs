const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const read=p=>fs.readFileSync(p,'utf8'),load=p=>JSON.parse(read('data/'+p+'.json'));
const finance=load('candidate_finance_2026').profiles,records=load('incumbent_records_2026').records;
const index=read('index.html'),ctx={normalizeSearchText:s=>s.toLowerCase().replace(/[^a-z0-9]+/g,' ').trim()};
vm.createContext(ctx);const start=index.indexOf('    function buildCandidateProfileHref('),end=index.indexOf('\n    function ',start+5);vm.runInContext(index.slice(start,end),ctx);
for(const [slug,name,district,votes,surname,party] of [
 ['angela-s-coburn','Angela S Coburn',27,'1,202',null,'Democratic'],
 ['lawrence-paul-almagno-jr','Lawrence Paul Almagno Jr',27,'419',null,'Republican'],
 ['george-a-nardone','George A Nardone',28,'524','nardone','Republican'],
 ['sherry-l-roberts','Sherry L Roberts',29,'514','roberts','Republican'],
 ['justine-caldwell','Justine Caldwell',30,'1,628','caldwell','Democratic']
]){
 const page=read('candidates/'+slug+'.html');assert(page.includes(`<h1>${name}</h1>`));assert(page.includes(votes+' votes'));assert(page.includes(`Uncontested ${party} primary · Official results`));
 assert(page.includes(`/running.html?chamber=house&amp;district=${district}&amp;election=general`));assert(!page.includes('Senate District'));assert(!page.includes('bffi-scorecard'));
 assert.equal(page.includes('data-voting-widget'),!!surname);assert.equal(page.includes(`current-riep-house-ranking.html#district-${district}`),!!surname);
 if(surname){
  assert(page.includes(`mailto:rep-${surname}@rilegislature.gov`));assert(page.includes(`data-candidate="${name}"`));assert(page.includes('of 75 House district records'));
  const rec=records.find(r=>r.chamber==='house'&&r.district_number===district);for(const b of rec.legislation_detail.lead_sponsored)assert(page.includes(b.bill));
 }else{assert(page.includes('Open seat in 2026'));assert(page.includes('West Warwick, Coventry'));assert(!page.includes('Patricia Serpa represents'));}
 const f=finance.find(f=>f.slug===slug);for(const k of ['money_raised','money_spent','ending_cash'])assert(page.includes('$'+f[k].toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})));
 assert.equal(ctx.buildCandidateProfileHref({name,chamber:'house',district_number:district}),`candidates/${slug}.html`);
 for(const route of ['ballot.html','running.html','race-page.js','candidate-profiles.html'])assert(read(route).includes(slug));
 assert(read(`races/house-${district}.html`).includes('20261006-house27-30'));
 const ids=[...page.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(ids.length,new Set(ids).size);for(const m of page.matchAll(/href="#([^"]+)"/g))assert(ids.includes(m[1]));
}
const c=read('candidates/angela-s-coburn.html');assert(c.includes('West Warwick School Committee, Ward 5'));assert(c.includes('Campaign priorities under construction'));assert(c.includes('Photo under construction'));
const a=load('candidate_research_2026_with_endorsements').candidates.find(c=>c.candidate_id==='house-27-rep-primary-lawrence-paul-almagno-jr');assert.equal(a.campaign_website,'https://lawrencealmagno.com/');assert.equal(a.priorities.length,3);
assert(!read('candidates/lawrence-paul-almagno-jr.html').includes('href="https://almagno-law.com/about/"'));
assert(read('candidates/sherry-l-roberts.html').includes('Coventry, West Greenwich'));assert(read('candidates/justine-caldwell.html').includes('East Greenwich, West Greenwich'));
const race=load('whos_running_2026').chambers.house['27'];assert.deepEqual(race.candidates.filter(c=>c.on_election_ballot).map(c=>c.name).sort(),['Angela S Coburn','Lawrence Paul Almagno Jr']);
console.log('PASS: D27 open-seat candidates and D28–30 incumbents, official primaries, finance, Almagno priorities and all routes');
