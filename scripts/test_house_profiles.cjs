const fs=require('fs'),assert=require('assert/strict'),vm=require('vm');
const profiles=[['edith-h-ajello','Edith H Ajello',1],['christopher-r-blazejewski','Christopher R Blazejewski',2],['nathan-w-biah','Nathan W Biah',3],['rebecca-m-kislak','Rebecca M Kislak',4]];
profiles.push(['raymond-a-hull','Raymond A Hull',6],['john-joseph-lombardi','John Joseph Lombardi',8],['enrique-george-sanchez','Enrique George Sanchez',9],['scott-a-slater','Scott A Slater',10]);
const ballot=fs.readFileSync('ballot.html','utf8'),running=fs.readFileSync('running.html','utf8'),index=fs.readFileSync('index.html','utf8'),directory=fs.readFileSync('candidate-profiles.html','utf8');
const records=JSON.parse(fs.readFileSync('data/incumbent_records_2026.json')).records;
const finance=JSON.parse(fs.readFileSync('data/candidate_finance_2026.json')).profiles;
const ctx={normalizeSearchText:s=>s.toLowerCase().replace(/[^a-z0-9]+/g,' ').trim()};vm.createContext(ctx);
const start=index.indexOf('    function buildCandidateProfileHref('),end=index.indexOf('\n    function ',start+5);vm.runInContext(index.slice(start,end),ctx);
for(const [slug,name,district] of profiles){
 const page=fs.readFileSync('candidates/'+slug+'.html','utf8'),rec=records.find(r=>r.chamber==='house'&&r.district_number===district),fin=finance.find(r=>r.slug===slug);
 assert(page.includes(`<h1>${name}</h1>`));assert(page.includes(`House District ${district}`));assert(page.includes(`data-candidate="${name}"`));assert(page.includes('house-voting-patterns/pilot.js'));assert(!page.includes('src="voting-patterns/pilot.js'));assert(!page.includes('Senate District'));assert(!page.includes('chamber=senate'));assert(page.includes('Current-session House index under construction'));
 assert(page.includes(`mailto:rep-${name.split(' ').at(-1).toLowerCase()}@rilegislature.gov`));assert(fs.existsSync('candidates/'+slug+'.png'));
 for(const k of ['money_raised','money_spent','ending_cash'])assert(page.includes('$'+fin[k].toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})),k);
 for(const b of rec.legislation_detail.lead_sponsored)assert(page.includes(b.bill));
 for(const source of [ballot,running])assert.equal(JSON.parse(source.match(/const candidateProfile = \((\{.*?\})\)\[candidate.candidate_id\]/)[1])[rec.candidate_id],slug);
 assert.equal(ctx.buildCandidateProfileHref({name,chamber:'house',district_number:district}),`candidates/${slug}.html`);assert.equal(ctx.buildCandidateProfileHref({name:'Other candidate',chamber:'house',district_number:district}),'');assert(directory.includes(`href="candidates/${slug}.html"`));
}
assert(fs.readFileSync('candidates/edith-h-ajello.html','utf8').includes('1,528 votes'));
for(const slug of ['christopher-r-blazejewski','nathan-w-biah','rebecca-m-kislak','raymond-a-hull','john-joseph-lombardi','scott-a-slater'])assert(fs.readFileSync('candidates/'+slug+'.html','utf8').includes('Primary vote totals are under construction'));
assert(fs.readFileSync('candidates/enrique-george-sanchez.html','utf8').includes('879 votes'));
assert(fs.readFileSync('candidates/raymond-a-hull.html','utf8').includes('Providence, North Providence'));
console.log('PASS: eight House profiles, dated finance, official contacts, bills, voting widgets, primary coverage and all profile routes');
