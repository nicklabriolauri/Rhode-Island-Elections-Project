import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {score,PRESETS,CATEGORIES,matchesTopic,rankRows} from '../activity-index-model.mjs';
const d=JSON.parse(fs.readFileSync(new URL('../data/cranston/activity-index-pilot-2026.json',import.meta.url)));
const clone=x=>JSON.parse(JSON.stringify(x));
test('frozen coverage, deduplication, non-overlapping credits',()=>{
 assert.equal(d.members.length,9);assert.equal(d.proposals.length,42);assert.equal(new Set(d.proposals.map(p=>p.id)).size,42);
 for(const p of d.proposals)assert(!p.sponsors.some(id=>p.cosponsors.includes(id)));
});
test('local baseline matches independently counted contributions',()=>{
 // Independently summed from the original six action types using Python Fractions:
 // ordinances 5 except property approval 2; advocacy/symbolic/recognition 1.
 const expected={Graziano:16,Andujar:16,Ritz:29,Traficante:28,Vaziri:10,Campopiano:7,Buonanno:19,Haroian:16,Wall:29};
 const rows=score(d,PRESETS.core);
 for(const r of rows)assert(Math.abs(r.raw-expected[r.surname])<1e-10,r.surname);
 assert(Math.abs(rows.reduce((s,r)=>s+r.index,0)/9-100)<1e-10);
});
test('changing role and joint settings changes the correct contribution',()=>{
 const core=score(d,{...clone(PRESETS.core),cosponsor:.25}),lead=score(d,PRESETS.core);
 assert(lead.find(r=>r.surname==='Traficante').raw<core.find(r=>r.surname==='Traficante').raw);
 const full=score(d,PRESETS.core),split=score(d,{...clone(PRESETS.core),joint:'split'});
 for(const name of ['Wall','Ritz'])assert(full.find(r=>r.surname===name).raw>split.find(r=>r.surname===name).raw);
});
test('earlier-year switch removes credits on carryover measures only',()=>{
 const baseline=score(d,PRESETS.core),changed=score(d,{...clone(PRESETS.core),includeCarryover:false});
 assert(Math.abs(baseline.find(r=>r.surname==='Ritz').raw-changed.find(r=>r.surname==='Ritz').raw-5)<1e-10);
 assert(Math.abs(baseline.find(r=>r.surname==='Andujar').raw-changed.find(r=>r.surname==='Andujar').raw-0)<1e-10);
});
test('zero denominator yields unavailable index rather than misleading zero',()=>{
 const config={...clone(PRESETS.core),weights:Object.fromEntries(CATEGORIES.map(([k])=>[k,0]))};
 assert(score(d,config).every(r=>r.raw===0&&r.index===null));
});
test('invalid inputs and duplicate/ambiguous records fail visibly',()=>{
 for(const x of [-1,NaN,Infinity,11])assert.throws(()=>score(d,{...clone(PRESETS.core),cosponsor:x}));
 const duplicate=clone(d);duplicate.proposals.push(duplicate.proposals[0]);assert.throws(()=>score(duplicate,PRESETS.core),/Duplicate measure/);
 const overlap=clone(d);overlap.proposals[0].cosponsors.push(overlap.proposals[0].sponsors[0]);assert.throws(()=>score(overlap,PRESETS.core),/overlap/);
});
test('topic tags are valid, independent of weights and usable as secondary filters',()=>{
 const before=score(d,PRESETS.core);
 for(const p of d.proposals){assert(p.primary_topic);assert(p.secondary_topics.length<=2);}
 const health=d.proposals.find(p=>p.id==='title-43fd7891de48');
 assert.equal(health.tier,'symbolic');assert.equal(health.primary_topic,'Health');
 assert(matchesTopic(health,'Community recognition'));assert(!matchesTopic(health,'Transportation and traffic'));
 const changed=clone(d);changed.proposals[0].primary_topic='Public property';
 assert.deepEqual(score(changed,PRESETS.core).map(r=>r.raw),before.map(r=>r.raw));
 const bad=clone(d);bad.proposals[0].primary_topic='Invented topic';assert.throws(()=>score(bad,PRESETS.core),/topic/);
});
test('each member primary-topic subtotals reconcile without counting secondary tags twice',()=>{
 for(const r of score(d,PRESETS.core)){
  const total=d.topic_vocabulary.reduce((s,t)=>s+r.contributions.filter(c=>c.proposal.primary_topic===t).reduce((n,c)=>n+c.points,0),0);
  assert(Math.abs(total-r.raw)<1e-10);
 }
});

test('competition ranks keep exact ties and do not mutate input',()=>{
 const rows=score(d,PRESETS.core), original=rows.map(r=>r.id);
 const ranked=rankRows(rows);assert.deepEqual(rows.map(r=>r.id),original);
 assert.deepEqual(ranked.map(r=>r.rank),[1,1,3,4,5,5,5,8,9]);
 for(const r of rows)assert(r.contributions.filter(c=>c.role==='sponsor').every(c=>c.roleCredit===1));
 for(const r of rows)assert(r.contributions.filter(c=>c.role==='cosponsor').every(c=>c.points===0));
});
