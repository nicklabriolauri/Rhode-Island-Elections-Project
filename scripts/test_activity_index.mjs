import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {score,PRESETS,CATEGORIES} from '../activity-index-model.mjs';
const d=JSON.parse(fs.readFileSync(new URL('../data/cranston/activity-index-pilot-2026.json',import.meta.url)));
const clone=x=>JSON.parse(JSON.stringify(x));
test('frozen coverage, deduplication, non-overlapping credits',()=>{
 assert.equal(d.members.length,9);assert.equal(d.proposals.length,42);assert.equal(new Set(d.proposals.map(p=>p.id)).size,42);
 for(const p of d.proposals)assert(!p.sponsors.some(id=>p.cosponsors.includes(id)));
});
test('local baseline matches independently counted contributions',()=>{
 // Ritz: 1 background-check rule + .5 joint pool rule + 1 stop rule
 // + 1 earlier-year zoning rule + .25 explicit school-fund cosponsorship.
 const expected={Graziano:2.25,Andujar:1.75,Ritz:3.75,Traficante:4.5,Vaziri:0.75,Campopiano:0,Buonanno:1.75,Haroian:1.75,Wall:3};
 const rows=score(d,PRESETS.core);
 for(const r of rows)assert(Math.abs(r.raw-expected[r.surname])<1e-10,r.surname);
 assert(Math.abs(rows.reduce((s,r)=>s+r.index,0)/9-100)<1e-10);
});
test('changing role and joint settings changes the correct contribution',()=>{
 const core=score(d,PRESETS.core),lead=score(d,PRESETS.initiators);
 assert.equal(lead.find(r=>r.surname==='Vaziri').raw,0);
 assert(lead.find(r=>r.surname==='Traficante').raw<core.find(r=>r.surname==='Traficante').raw);
 const full=score(d,{...clone(PRESETS.core),joint:'full'});
 for(const name of ['Wall','Ritz'])assert.equal(full.find(r=>r.surname===name).raw-core.find(r=>r.surname===name).raw,0.5);
});
test('earlier-year switch removes credits on carryover measures only',()=>{
 const baseline=score(d,PRESETS.core),changed=score(d,{...clone(PRESETS.core),includeCarryover:false});
 assert.equal(baseline.find(r=>r.surname==='Ritz').raw-changed.find(r=>r.surname==='Ritz').raw,1);
 assert.equal(baseline.find(r=>r.surname==='Andujar').raw-changed.find(r=>r.surname==='Andujar').raw,0.25);
});
test('zero denominator yields unavailable index rather than misleading zero',()=>{
 const config={...clone(PRESETS.core),weights:Object.fromEntries(CATEGORIES.map(([k])=>[k,0]))};
 assert(score(d,config).every(r=>r.raw===0&&r.index===null));
});
test('invalid inputs and duplicate/ambiguous records fail visibly',()=>{
 for(const x of [-1,NaN,Infinity,6])assert.throws(()=>score(d,{...clone(PRESETS.core),cosponsor:x}));
 const duplicate=clone(d);duplicate.proposals.push(duplicate.proposals[0]);assert.throws(()=>score(duplicate,PRESETS.core),/Duplicate measure/);
 const overlap=clone(d);overlap.proposals[0].cosponsors.push(overlap.proposals[0].sponsors[0]);assert.throws(()=>score(overlap,PRESETS.core),/overlap/);
});
