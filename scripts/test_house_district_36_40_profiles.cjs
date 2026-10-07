const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const read=p=>fs.readFileSync(p,'utf8'),load=p=>JSON.parse(read('data/'+p+'.json'));
const finance=load('candidate_finance_2026').profiles,records=load('incumbent_records_2026').records;
const index=read('index.html'),ctx={normalizeSearchText:s=>s.toLowerCase().replace(/[^a-z0-9]+/g,' ').trim()};vm.createContext(ctx);
const start=index.indexOf('    function buildCandidateProfileHref('),end=index.indexOf('\n    function ',start+5);vm.runInContext(index.slice(start,end),ctx);
for(const [slug,name,district,votes,share,surname] of [
 ['tina-l-spears','Tina L Spears',36,'2,238','81.92%','spears'],
 ['samuel-angelo-azzinaro','Samuel Angelo Azzinaro',37,'1,123','100%','azzinaro'],
 ['christopher-m-stanton','Christopher M Stanton',37,'303','100%',null],
 ['brian-patrick-kennedy','Brian Patrick Kennedy',38,'852','66.15%','kennedy'],
 ['megan-l-cotter','Megan L Cotter',39,'1,375','100%','cotter'],
 ['jasmin-roy','Jasmin Roy',39,'570','100%',null],
 ['michael-chippendale','Michael Chippendale',40,'680','100%','chippendale']
]){
 const p=read('candidates/'+slug+'.html');assert(p.includes(`<h1>${name}</h1>`));assert(p.includes(votes+' votes'));assert(p.includes(share));assert(p.includes('Official results'));
 assert(p.includes(`/running.html?chamber=house&amp;district=${district}&amp;election=general`));assert(!p.includes('Senate District'));assert(!p.includes('bffi-scorecard'));
 assert.equal(p.includes('data-voting-widget'),!!surname);assert.equal(p.includes(`current-riep-house-ranking.html#district-${district}`),!!surname);
 if(surname){assert(p.includes(`mailto:rep-${surname}@rilegislature.gov`));assert(p.includes(`data-candidate="${name}"`));assert(p.includes('of 75 House district records'));
  const rec=records.find(r=>r.chamber==='house'&&r.district_number===district);for(const b of rec.legislation_detail.lead_sponsored)assert(p.includes(b.bill));
 }else{assert(!p.includes('riep-legislative-index'));assert(!p.includes('mailto:rep-craven@'));}
 if(slug==='christopher-m-stanton')assert(p.includes('No financial summary is currently available'));
 const f=finance.find(f=>f.slug===slug);for(const k of ['money_raised','money_spent','ending_cash'])if(f[k]!=null)assert(p.includes('$'+f[k].toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})));
 assert.equal(ctx.buildCandidateProfileHref({name,chamber:'house',district_number:district}),`candidates/${slug}.html`);
 for(const route of ['ballot.html','running.html','race-page.js','candidate-profiles.html'])assert(read(route).includes(slug));
 assert(read(`races/house-${district}.html`).includes('20261007-house36-40'));
 const ids=[...p.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(ids.length,new Set(ids).size);for(const m of p.matchAll(/href="#([^"]+)"/g))assert(ids.includes(m[1]));
 for(const m of p.matchAll(/<img[^>]+src="([^"/]+\.(?:png|jpg))"/g))assert(fs.existsSync('candidates/'+m[1]));
}
assert(read('candidates/christopher-m-stanton.html').includes('mailto:Stanton@Stanton4RI.com'));
assert(read('candidates/christopher-m-stanton.html').includes('Second-home tax'));
assert(read('candidates/jasmin-roy.html').includes('https://jasminroy4ri.org/'));
assert(!read('candidates/tina-l-spears.html').includes('tinaspearsri.com/priorities'));
for(const slug of ['tina-l-spears','samuel-angelo-azzinaro','brian-patrick-kennedy','megan-l-cotter','michael-chippendale'])assert(read('candidates/'+slug+'.html').includes('Legislative Effectiveness Score'));
assert(read('candidates/michael-chippendale.html').includes('Republican incumbent'));
console.log('PASS: D36–40 profiles, both competitive races, verified primary totals, finance, legislative scores, portrait files and routes');
