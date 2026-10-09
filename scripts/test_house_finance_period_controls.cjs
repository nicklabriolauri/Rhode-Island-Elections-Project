const assert=require('assert/strict'),fs=require('fs');
const data=JSON.parse(fs.readFileSync('data/candidate_finance_2026.json'));
for(const p of data.profiles.filter(p=>p.chamber==='house'&&+p.district_number<=25)){const path='candidates/'+p.slug+'.html';if(fs.existsSync(path))assert(!fs.readFileSync(path,'utf8').includes('finance-periods.js'));}
assert(fs.readFileSync('finance.html','utf8').includes('id="financeFilingSelect"'));
console.log('PASS: candidate profile selectors removed; finance page retains its reporting-period filter');
