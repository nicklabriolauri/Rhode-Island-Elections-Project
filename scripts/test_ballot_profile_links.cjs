const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('ballot.html','utf8');
const body=source.slice(source.indexOf('  function candidateCard(candidate){'),source.indexOf('  function raceSection('));
const registry=JSON.parse(source.match(/const candidateProfile = \((\{.*?\})\)\[candidate.candidate_id\];/)[1]);
const context={profiles:new Map(),researchFor:()=>null,financeFor:()=>null,partyLong:()=>'',partyBadge:()=>'',priorityBlock:()=>'',endorsementBlock:()=>'',ratingsBlock:()=>'',officeRecordBlock:()=>'',esc:s=>String(s).replaceAll('&','&amp;').replaceAll('"','&quot;')};
vm.createContext(context);vm.runInContext(body,context);
for(const [id,slug] of Object.entries(registry)){
 assert(fs.existsSync('candidates/'+slug+'.html'));
 const html=context.candidateCard({candidate_id:id,name:slug,email:'',phone:''});
 assert.equal((html.match(new RegExp('href="candidates/'+slug+'\\.html"','g'))||[]).length,2,id);
 assert(html.includes('Candidate profile →'));
}
assert(!context.candidateCard({candidate_id:'unavailable',name:'Other candidate'}).includes('Candidate profile →'));
console.log('PASS: candidate-name and profile-button routes for all '+Object.keys(registry).length+' available profiles; no broken route for unavailable profiles');
