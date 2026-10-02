const fs=require('fs'),vm=require('vm'),assert=require('assert');
const urso=fs.readFileSync('candidates/lori-urso.html','utf8');
const records=JSON.parse(fs.readFileSync('data/lori_urso_supplied_records_2026.json','utf8'));
assert.equal((urso.match(/class="sponsored-bill"/g)||[]).length,271);
const table=urso.split('<table class="vote-records-table">')[1].split('</table>')[0];
assert.equal((table.match(/<th scope="row">/g)||[]).length,100);
assert.equal((table.match(/datetime="2026-06-10"/g)||[]).length,3);
assert.equal((table.match(/datetime="2026-06-11"/g)||[]).length,97);
assert.equal((table.match(/class="vote-position">Nay/g)||[]).length,1);
assert(!urso.includes('billtrack50.com'));assert(!urso.includes('class="profile-fold"'));
for(const file of ['candidates/lori-urso.html','candidates/frank-a-ciccone.html']){
 const html=fs.readFileSync(file,'utf8');for(const cls of ['class="lawmaker-head"','class="riep-progress-metrics"','class="aclu-vote-dialog"','class="endorsement-chip"','class="metric-grid"','class="office-details"','class="details"'])assert(html.includes(cls),file+' '+cls);
 assert.equal((html.match(/class="aclu-dialog-vote"/g)||[]).length,11);
}
assert.equal((urso.match(/href="\/primary-results.html\?chamber=senate&amp;district=8&amp;party=DEM#racePanel"/g)||[]).length,2);
const source=fs.readFileSync('primary-results.html','utf8');
const helper=source.slice(source.indexOf('    function applyProfilePrimaryLink()'),source.indexOf('    async function loadResults()'));
const dataset=JSON.parse(fs.readFileSync('data/primary_results_2026.json','utf8'));
function testLink(query,expected){
 let rendered=null,scrolled=false;
 const context={profileLinkParams:new URLSearchParams(query),currentChamber:'senate',selectedRaceKey:null,geoLayer:null,
 racesForDistrict:(c,d)=>dataset.races.filter(r=>r.chamber===c&&r.district===d),
 normalizeParty:p=>String(p).toLowerCase().startsWith('dem')?'Democratic':String(p).toLowerCase().startsWith('rep')?'Republican':p,
 renderRacePanel:r=>rendered=r,document:{getElementById:()=>({scrollIntoView:()=>scrolled=true})}};
 vm.runInNewContext(helper+';applyProfilePrimaryLink();',context);
 if(expected){assert.equal(rendered.length,1);assert.equal(rendered[0].district,8);assert.equal(rendered[0].party_code,'DEM');assert(scrolled)}else assert.equal(rendered,null);
}
testLink('chamber=senate&district=8&party=DEM',true);testLink('district=8&party=REP',false);testLink('district=99',false);testLink('',false);
let handlers={},shown=false,closed=false;const dialog={addEventListener:(n,f)=>handlers[n]=f,showModal:()=>shown=true,close:()=>closed=true};const trigger={addEventListener:(n,f)=>handlers.trigger=f};
vm.runInNewContext(fs.readFileSync('candidates/candidate-profile.js','utf8'),{document:{getElementById:id=>id==='aclu-votes-dialog'?dialog:trigger}});handlers.trigger();assert(shown);handlers.click({target:dialog});assert(closed);
console.log('PASS: 271 bills, 100 votes with original dates/positions, matching components, specific primary links, valid/invalid deep links, ACLU dialog');
