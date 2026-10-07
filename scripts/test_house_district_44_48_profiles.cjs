const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),cp=require('child_process');
const read=p=>fs.readFileSync(p,'utf8'),load=p=>JSON.parse(read('data/'+p+'.json'));
const entries=[['gregory-costantino','Gregory Costantino',44,1577,'costantino'],['joseph-hosey','Joseph Hosey',44,498,null],['mia-a-ackerman','Mia A Ackerman',45,1519,'ackerman'],['mary-ann-shallcross-smith','Mary Ann Shallcross Smith',46,1524,'shallcross-smith'],['david-j-place','David J Place',47,495,'place'],['brian-c-newberry','Brian C Newberry',48,437,'newberry']];
const records=load('incumbent_records_2026').records,roster=load('whos_running_2026').chambers.house,primary=load('candidate_profile_primary_returns_2026');
const index=read('index.html'),ctx={normalizeSearchText:s=>s.toLowerCase().replace(/[^a-z0-9]+/g,' ').trim()};vm.createContext(ctx);const start=index.indexOf('    function buildCandidateProfileHref('),end=index.indexOf('\n    function ',start+5);vm.runInContext(index.slice(start,end),ctx);
for(const [slug,name,d,votes,surname] of entries){
 const p=read('candidates/'+slug+'.html');assert(p.includes(`<h1>${name}</h1>`));assert(p.includes(votes.toLocaleString('en-US')+' votes'));assert(p.includes('Official results'));assert(p.includes('100%'));
 assert(p.includes(`/running.html?chamber=house&amp;district=${d}&amp;election=general`));assert(!p.includes('Senate District'));assert(!p.includes('Eleven Senate votes'));assert(!p.includes('bffi-scorecard'));
 assert.equal(p.includes('data-voting-widget'),!!surname);assert.equal(p.includes('riep-legislative-index'),!!surname);
 if(surname){assert(p.includes(`mailto:rep-${surname}@rilegislature.gov`));assert(p.includes(`data-candidate="${name}"`));assert(p.includes(`current-riep-house-ranking.html#district-${d}`));assert(p.includes('of 75 House district records'));
 const rec=records.find(r=>r.chamber==='house'&&r.district_number===d);for(const b of rec.legislation_detail.lead_sponsored)assert(p.includes(b.bill));assert(p.includes('Center for Effective Lawmaking'));assert(p.includes('Session attendance'));
 }else{assert(p.includes('General Assembly record not applicable'));assert(!p.includes('rep-desimone'));assert(!p.includes('class="lawmaker-score"'));}
 assert.equal(ctx.buildCandidateProfileHref({name,chamber:'house',district_number:d}),`candidates/${slug}.html`);
 for(const route of ['ballot.html','running.html','race-page.js','candidate-profiles.html'])assert(read(route).includes(slug));
 assert(read(`races/house-${d}.html`).includes('20261007-house44-48'));
 const ids=[...p.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(ids.length,new Set(ids).size);for(const m of p.matchAll(/href="#([^"]+)"/g))assert(ids.includes(m[1]));
 for(const m of p.matchAll(/<img[^>]+src="([^"/]+\.(?:png|jpg))"/g))assert(fs.existsSync('candidates/'+m[1]));
 assert.equal(primary[slug].votes,votes);assert(primary[slug].source_url.includes('/ballot-items/'));assert(roster[d].candidates.find(c=>c.name===name).profile_available);
}
const hosey=read('candidates/joseph-hosey.html');assert(hosey.includes('mailto:HoseyforRI@gmail.com'));assert(hosey.includes('Roads, bridges, and infrastructure'));assert(hosey.includes('src="joseph-hosey.jpg"'));
assert(read('candidates/mary-ann-shallcross-smith.html').includes('/representatives/shallcross%20smith/Pages/Biography.aspx'));
for(const fn of ['candidate_research_2026','candidate_research_2026_with_endorsements']){const r=load(fn).candidates.find(c=>c.candidate_name==='Brian C Newberry');assert.equal(r.campaign_website,'');assert(r.professional_biography_url.includes('lewisbrisbois'));}
console.log('PASS: six D44–48 profiles, competitive pair, official primaries, portraits, incumbent-only metrics and navigation');
