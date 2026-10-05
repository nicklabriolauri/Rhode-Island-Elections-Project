const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const html=fs.readFileSync('index.html','utf8');
function extract(name){const start=html.indexOf(`    function ${name}(`);assert(start>=0);const end=html.indexOf('\n    function ',start+5);return html.slice(start,end);}
const roster=JSON.parse(fs.readFileSync('data/whos_running_2026.json','utf8'));
let candidates=[];for(const [chamber,ds] of Object.entries(roster.chambers))for(const [d,r] of Object.entries(ds)){const seen=new Set();for(const c of [...r.candidates,...(r.general_candidates||[])]){if(seen.has(c.candidate_id))continue;seen.add(c.candidate_id);candidates.push({...c,chamber,district_number:Number(d)});}}
const ctx={homepageCandidates:candidates,chamberLabel:c=>c==='house'?'House':'Senate',partyLongLabel:p=>({DEM:'Democrat',REP:'Republican',IND:'Independent'}[p]||p),normalizeSearchText:s=>s.toLowerCase().replace(/[^a-z0-9]+/g,' ').trim(),escapeHtml:s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),encodeURIComponent};vm.createContext(ctx);vm.runInContext(extract('buildCandidateProfileHref')+extract('buildAddressCandidateGroup'),ctx);
const group=(c,d)=>ctx.buildAddressCandidateGroup(c,d);
const house=group('house',35);assert(house.includes('candidates/kathleen-a-fogarty.html'));assert(house.includes('candidates/jennifer-p-nerbonne.html'));assert.equal((house.match(/class="address-candidate"/g)||[]).length,2);
assert(group('senate',37).includes('candidates/virginia-susan-sosnowski.html'));
assert(!group('senate',5).includes('Theodore Newcomer'));
ctx.homepageCandidates=[...candidates.filter(c=>!(c.chamber==='house'&&c.district_number===35)),...['A','B','C'].map(n=>({name:n,candidate_id:n,chamber:'house',district_number:35,party:'IND',election_status:'general_candidate'}))];const multi=group('house',35);assert.equal((multi.match(/class="address-candidate"/g)||[]).length,3);assert(multi.includes('Profile coming soon'));assert.equal(group('house',null),'');
const render=extract('renderAddressSearchResult');assert(!render.includes('Find My Precinct'));assert(render.includes('All Candidate Profiles'));assert(render.includes('2024 election results'));
console.log('PASS: Fogarty/Nerbonne and Sosnowski direct links; primary loser exclusion; three-candidate fallback; no precinct button');
