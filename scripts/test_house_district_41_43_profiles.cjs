const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const read=p=>fs.readFileSync(p,'utf8'),load=p=>JSON.parse(read('data/'+p+'.json'));
const finance=load('candidate_finance_2026').profiles,records=load('incumbent_records_2026').records;
const index=read('index.html'),ctx={normalizeSearchText:s=>s.toLowerCase().replace(/[^a-z0-9]+/g,' ').trim()};vm.createContext(ctx);
const start=index.indexOf('    function buildCandidateProfileHref('),end=index.indexOf('\n    function ',start+5);vm.runInContext(index.slice(start,end),ctx);
for(const [slug,name,district,votes,share,surname] of [
 ['shaina-n-smith','Shaina N Smith',41,'1,023','100%',null],
 ['michael-j-riley','Michael J Riley',41,'525','100%',null],
 ['edward-w-stravato','Edward W Stravato',42,'1,202','100%',null],
 ['richard-r-fascia','Richard R Fascia',42,'425','100%','fascia'],
 ['deborah-a-fellela','Deborah A Fellela',43,'1,256','100%','fellela']
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
 assert(read(`races/house-${district}.html`).includes('20261007-house41-43'));
 const ids=[...p.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(ids.length,new Set(ids).size);for(const m of p.matchAll(/href="#([^"]+)"/g))assert(ids.includes(m[1]));
 for(const m of p.matchAll(/<img[^>]+src="([^"/]+\.(?:png|jpg))"/g))assert(fs.existsSync('candidates/'+m[1]));
}
assert(read('candidates/michael-j-riley.html').includes('Campaign response submitted directly to RIEP'));
assert(read('candidates/michael-j-riley.html').includes('Repeal the Assault Weapons Ban'));
assert(read('candidates/michael-j-riley.html').includes('mailto:TEAM@RileyforRI.com'));
assert(read('candidates/michael-j-riley.html').includes('June 22, 2026 to October 5, 2026'));
assert(read('candidates/michael-j-riley.html').includes('$28,520.00'));
assert(read('candidates/edward-w-stravato.html').includes('Support seniors'));
assert(read('candidates/richard-r-fascia.html').includes('No 2023–2024 CEL score is available'));
assert(read('candidates/deborah-a-fellela.html').includes('#37 of 66 House Democrats'));
const roy=read('candidates/jasmin-roy.html');assert(roy.includes('src="jasmin-roy.png"'));assert(roy.includes('height:auto;object-fit:contain'));assert(read('candidate-profiles.html').includes('candidates/jasmin-roy.png'));
assert(fs.readFileSync('candidates/jasmin-roy.png').equals(fs.readFileSync('../attachments/8bb1702e-5ecd-43ca-b691-6fa3dc9bc261/Screenshot 2026-10-07 at 12.20.08\u202fAM.png')));
console.log('PASS: D41–43 profiles, competitive pairs, official primaries, financial periods, incumbent records, supplied priorities, portrait assets and routing');
