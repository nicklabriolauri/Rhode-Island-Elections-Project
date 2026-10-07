const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const read=p=>fs.readFileSync(p,'utf8'),load=p=>JSON.parse(read('data/'+p+'.json'));
const finance=load('candidate_finance_2026').profiles,records=load('incumbent_records_2026').records;
const index=read('index.html'),ctx={normalizeSearchText:s=>s.toLowerCase().replace(/[^a-z0-9]+/g,' ').trim()};vm.createContext(ctx);
const start=index.indexOf('    function buildCandidateProfileHref('),end=index.indexOf('\n    function ',start+5);vm.runInContext(index.slice(start,end),ctx);
for(const [slug,name,district,votes,share,surname] of [
 ['james-c-sheehan','James C Sheehan',31,'1,088','46.70%',null],
 ['robert-e-craven-jr','Robert E Craven Jr',32,'1,887','72.97%',null],
 ['carol-hagan-mcentee','Carol Hagan McEntee',33,'2,284','100%','mcentee'],
 ['jessica-drew-day','Jessica Drew Day',33,'414','100%',null],
 ['teresa-a-tanzi','Teresa A Tanzi',34,'2,075','100%','tanzi']
]){
 const p=read('candidates/'+slug+'.html');assert(p.includes(`<h1>${name}</h1>`));assert(p.includes(votes+' votes'));assert(p.includes(share));assert(p.includes('Official results'));
 assert(p.includes(`/running.html?chamber=house&amp;district=${district}&amp;election=general`));assert(!p.includes('Senate District'));assert(!p.includes('bffi-scorecard'));
 assert.equal(p.includes('data-voting-widget'),!!surname);assert.equal(p.includes(`current-riep-house-ranking.html#district-${district}`),!!surname);
 if(surname){assert(p.includes(`mailto:rep-${surname}@rilegislature.gov`));assert(p.includes(`data-candidate="${name}"`));assert(p.includes('of 75 House district records'));
  const rec=records.find(r=>r.chamber==='house'&&r.district_number===district);for(const b of rec.legislation_detail.lead_sponsored)assert(p.includes(b.bill));
 }else{assert(!p.includes('riep-legislative-index'));assert(!p.includes('mailto:rep-craven@'));}
 const f=finance.find(f=>f.slug===slug);for(const k of ['money_raised','money_spent','ending_cash'])assert(p.includes('$'+f[k].toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})));
 assert.equal(ctx.buildCandidateProfileHref({name,chamber:'house',district_number:district}),`candidates/${slug}.html`);
 for(const route of ['ballot.html','running.html','race-page.js','candidate-profiles.html'])assert(read(route).includes(slug));
 assert(read(`races/house-${district}.html`).includes('20261007-house31-34'));
 const ids=[...p.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(ids.length,new Set(ids).size);for(const m of p.matchAll(/href="#([^"]+)"/g))assert(ids.includes(m[1]));
 for(const m of p.matchAll(/<img[^>]+src="([^"/]+\.(?:png|jpg))"/g))assert(fs.existsSync('candidates/'+m[1]));
}
assert(read('candidates/james-c-sheehan.html').includes('Former Rhode Island state senator'));
assert(read('candidates/james-c-sheehan.html').includes('Sludge plant and environmental protection'));
assert(read('candidates/robert-e-craven-jr.html').includes('cravenforri@gmail.com'));
assert(read('candidates/robert-e-craven-jr.html').includes('his father’s House service'));
assert(!records.some(r=>r.candidate_id==='house-32-dem-primary-robert-e-craven-jr'));
const sr=records.find(r=>r.chamber==='house'&&r.district_number===32);assert.equal(sr.candidate_name,'Robert E Craven Sr');
assert.equal(load('house_legislative_progress_2025_2026').records.find(r=>r.district_number===32).candidate_name,'Robert E Craven Sr');
assert(!load('outside_ratings_2026').ratings.some(r=>r.candidate_name==='Robert E Craven Jr'));
// Exercise real race comparison lookup: Jr must not inherit Sr's record or CEL rating.
const run=read('running.html'),rctx={incumbentRecords:records,outsideRatings:load('outside_ratings_2026').ratings};vm.createContext(rctx);
for(const name of ['normPersonName','sameNameSuffix','officeRecordFor','ratingsFor']){
 const a=run.indexOf('    function '+name+'('),b=run.indexOf('\n    function ',a+5);assert(a>=0);vm.runInContext(run.slice(a,b),rctx);
}
const jr={name:'Robert E Craven Jr',chamber:'house',district_number:32};assert.equal(rctx.officeRecordFor(jr),null);assert.equal(rctx.ratingsFor(jr).length,0);
assert.equal(rctx.officeRecordFor({...jr,name:'Robert E Craven Sr'}).candidate_name,'Robert E Craven Sr');
assert(rctx.ratingsFor({...jr,name:'Robert E Craven Sr'}).length>0);
console.log('PASS: D31–34 profiles, official primaries, finance, House calculations, routing and Craven father/son isolation');
