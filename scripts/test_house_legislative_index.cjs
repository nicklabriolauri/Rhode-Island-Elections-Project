const fs=require('fs'),assert=require('assert/strict');
const data=JSON.parse(fs.readFileSync('data/house_legislative_progress_2025_2026.json'));
const records=data.records,keys=['prime_sponsored','passed_chamber','became_law'];
assert.equal(records.length,75);assert.deepEqual(records.map(r=>r.district_number).sort((a,b)=>a-b),Array.from({length:75},(_,i)=>i+1));
const totals=keys.map(k=>records.reduce((sum,r)=>sum+r.legislation[k],0));assert.deepEqual(totals,[2469,648,501]);
const denominator=totals.reduce((v,t)=>v*BigInt(t),1n);
const numerator=r=>keys.reduce((sum,k,i)=>sum+BigInt(r.legislation[k])*(denominator/BigInt(totals[i])),0n);
const score=r=>Number(25n*numerator(r))/Number(denominator);
const rank=r=>1+records.filter(p=>numerator(p)>numerator(r)).length;
assert.equal(records.reduce((sum,r)=>sum+25n*numerator(r),0n),75n*denominator);
const incumbentRecords=JSON.parse(fs.readFileSync('data/incumbent_records_2026.json')).records.filter(r=>r.chamber==='house');
for(const r of incumbentRecords){const full=records.find(p=>p.district_number===r.district_number);for(const k of keys)assert.equal(r.legislation[k],full.legislation[k]);}
const slugs={1:'edith-h-ajello',2:'christopher-r-blazejewski',3:'nathan-w-biah',4:'rebecca-m-kislak',6:'raymond-a-hull',8:'john-joseph-lombardi',9:'enrique-george-sanchez',10:'scott-a-slater'};
const ranking=fs.readFileSync('candidates/current-riep-house-ranking.html','utf8');assert.equal((ranking.match(/<tr id="district-/g)||[]).length,75);assert(!/Senate|Senator/.test(ranking));
for(const r of records){const row=ranking.match(new RegExp(`<tr id="district-${r.district_number}"[^>]*>(.*?)</tr>`))[1];assert(row.startsWith(`<td>${rank(r)}</td>`));assert(row.includes(`<strong>${score(r).toFixed(2)}</strong>`));}
for(const [d,slug] of Object.entries(slugs)){
 const r=records.find(p=>p.district_number===Number(d)),page=fs.readFileSync('candidates/'+slug+'.html','utf8');
 const box=page.slice(page.indexOf('<section class="riep-progress" id="riep-legislative-index"'),page.indexOf('</details>',page.indexOf('<section class="riep-progress" id="riep-legislative-index"')));
 assert(box.includes(`<strong>${score(r).toFixed(2)}</strong>`));assert(box.includes(`#${rank(r)} of 75 House district records`));assert(box.includes(`current-riep-house-ranking.html#district-${d}`));assert(box.includes('September 22, 2026'));assert(!box.includes('under construction'));
}
console.log('PASS: 75-member totals, exact mean 1, all House ranks, eight profile calculations and matching source counts');
