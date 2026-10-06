const fs=require('fs'),assert=require('assert/strict'),vm=require('vm');
const configs=[['anthony-j-desimone','Anthony J DeSimone',5],['brittany-m-kubicek','Brittany M Kubicek',5],['amy-j-santiago','Amy J Santiago',7],['christopher-l-ireland','Christopher L Ireland',7]];
const index=fs.readFileSync('index.html','utf8'),ctx={normalizeSearchText:s=>s.toLowerCase().replace(/[^a-z0-9]+/g,' ').trim()};vm.createContext(ctx);
const start=index.indexOf('    function buildCandidateProfileHref(');vm.runInContext(index.slice(start,index.indexOf('\n    function ',start+5)),ctx);
for(const [slug,name,district] of configs){
 const page=fs.readFileSync('candidates/'+slug+'.html','utf8');assert(page.includes(`<h1>${name}</h1>`));assert(page.includes(`House District ${district}`));assert(page.includes(`href="/races/house-${district}.html"`));assert(!page.includes('Senate District'));
 if(slug==='anthony-j-desimone'){assert(page.includes('data-voting-widget'));assert(page.includes('riep-legislative-index'));assert(page.includes('of 75 House district records'));const section=page.slice(page.indexOf('id="elections"'),page.indexOf('id="primaries"'));assert(section.includes('2022')&&section.includes('2024'));assert(!section.includes('2014'));}
 else{assert(!page.includes('data-voting-widget'));assert(!page.includes('riep-legislative-index'));assert(!page.includes('rep-desimone'));assert(page.includes('General Assembly record not applicable'));}
 assert.equal(ctx.buildCandidateProfileHref({name,chamber:'house',district_number:district}),`candidates/${slug}.html`);
 for(const f of ['ballot.html','running.html','race-page.js'])assert(fs.readFileSync(f,'utf8').includes('":"'+slug+'"'));
 assert(fs.readFileSync('candidate-profiles.html','utf8').includes('href="candidates/'+slug+'.html"'));
}
const sanchez=fs.readFileSync('candidates/enrique-george-sanchez.html','utf8');const history=sanchez.slice(sanchez.indexOf('id="elections"'),sanchez.indexOf('id="primaries"'));assert(!history.includes('2014'));assert(history.includes('2022')&&history.includes('2024'));assert.equal((history.match(/class="year election-link"/g)||[]).length,2);
const kubicek=fs.readFileSync('candidates/brittany-m-kubicek.html','utf8');for(const amount of ['$16,771.76','$12,753.07','$4,018.69'])assert(kubicek.includes(amount));assert(kubicek.includes('/finance-candidates/house-5-oth-general-brittany-m-kubicek.html'));assert(kubicek.includes('Year to date through June 30, 2026'));assert(kubicek.includes('Independent Socialist'));
assert(fs.readFileSync('candidates/christopher-l-ireland.html','utf8').includes('Photo under construction'));
console.log('PASS: four competitive profiles, correct incumbent/challenger records, finance routes, profile links and Sanchez election history');
