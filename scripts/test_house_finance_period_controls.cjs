const assert=require('assert/strict'),fs=require('fs'),vm=require('vm');
const {parseHTML}=require('../../test-runtime/node_modules/linkedom');
const data=JSON.parse(fs.readFileSync('data/candidate_finance_2026.json'));
(async()=>{
for(const p of data.profiles.filter(p=>p.chamber==='house'&&+p.district_number<=25)) {
 const path='candidates/'+p.slug+'.html';if(!fs.existsSync(path))continue;
 const {document,Event}=parseHTML(fs.readFileSync(path,'utf8'));
 const ctx={document,location:{pathname:'/candidates/'+p.slug+'.html'},Intl,console,fetch:async()=>({ok:true,json:async()=>data})};vm.createContext(ctx);
 await vm.runInContext(fs.readFileSync('candidates/finance-periods.js','utf8'),ctx);
 const select=document.getElementById('profile-finance-period');assert(select,p.slug);assert(document.querySelector('aside.side').contains(select));
 assert(document.getElementById('finance').textContent.includes(new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(p.ending_cash)));
 if((p.archived_reporting_periods||[]).length){Object.defineProperty(select,'value',{value:'1',configurable:true});select.dispatchEvent(new Event('change'));const old=p.archived_reporting_periods.at(-1);assert(document.getElementById('finance').textContent.includes(old.reporting_period_label));assert(document.getElementById('finance').textContent.includes(new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(old.ending_cash)));}
}
console.log('PASS: right sidebar controls and current/archive totals across House 1–25 candidate pages');
})();
