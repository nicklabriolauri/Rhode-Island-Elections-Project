const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const source=JSON.parse(fs.readFileSync('data/general_results_2026.json','utf8'));
const index=JSON.parse(fs.readFileSync('data/candidate_results_2026.json','utf8'));
const context={window:{},document:{createElement:()=>({}),head:{append(){}},querySelectorAll:()=>[]},location:{pathname:'/index.html'},fetch:async url=>({ok:true,json:async()=>url.includes('candidate_results')?index:source}),console};
vm.createContext(context);vm.runInContext(fs.readFileSync('election-results-2026.js','utf8'),context);
(async()=>{
 const api=context.window.RIEPResults2026;await api.ready;
 assert.equal(index.candidates.filter(c=>c.profile).length,135);
 for(const c of index.candidates){
  assert(api.record(c.slug));
  const html=api.section(c);assert(html.includes('2026 general election'));
  const r=api.race(c.chamber,c.district);
  if(c.source_id){assert(r.candidates.some(x=>x.source_id===c.source_id));assert(html.includes('Shares include write-ins'));}
  else assert(api.badge(c).includes('Not on general-election ballot'));
 }
 const fung=index.candidates.find(c=>c.chamber==='house'&&c.district===15&&c.name.includes('Fung'));
 const crudele=index.candidates.find(c=>c.name.includes('Crudele'));
 const pap=index.candidates.find(c=>c.name.includes('Paplauskas'));
 assert(api.badge(fung).includes('Won · DDHQ call'));assert(api.badge(crudele).includes('Not elected'));assert(api.badge(pap).includes('Not elected'));
 assert(api.section(fung).includes('Paplauskas'));assert(api.section(fung).includes('Crudele'));
 assert(api.badge('john-burke').includes('Unopposed · elected'));
 assert.equal(api.badge({name:'Wrong Person',chamber:'house',district:15}), '');
 assert(api.district('senate',34).includes('Wilcox'));
 console.log('PASS: all 135 profiles mapped; three-way race outcomes; unopposed result; absent candidate; wrong-identity rejection; district link');
})().catch(e=>{console.error(e);process.exit(1)});
