const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),cp=require('child_process');
const read=p=>fs.readFileSync(p,'utf8'),data=JSON.parse(read('data/candidate_finance_2026.json')),mirror=JSON.parse(read('candidate_finance_2026.json'));
const prior=JSON.parse(cp.execFileSync('git',['show','fd013de958b2276d9db7c09f72b08fb484fa8104:data/candidate_finance_2026.json'],{encoding:'utf8',maxBuffer:2000000}));
const cents=n=>Math.round(n*100),sum=rows=>cents(rows.reduce((s,r)=>s+r.amount,0));
const html=read('finance.html'),script=html.match(/<script>([\s\S]*)<\/script>/)[1].replace(/\n    boot\(\);/,'');
const ctx={Intl,URLSearchParams,window:{location:{search:''}},document:{addEventListener(){}}};vm.createContext(ctx);vm.runInContext(script,ctx);
const rows=[['michael-j-riley',0,28520,4823.43,23696.57,'June 22',35,3,32,'7352'],['shaina-n-smith',618.56,1402,466.03,1554.53,'July 1',4,4,1,'9957'],['edward-w-stravato',45724.70,3863,22946.59,26641.11,'July 1',19,69,19,'10230'],['richard-r-fascia',9733.56,17248.25,9750.21,17231.60,'July 1',57,69,34,'7247'],['deborah-a-fellela',10139.28,300,2501.29,7937.99,'July 1',2,33,2,'6385']];
const slugs=rows.map(r=>r[0]);
for(const [slug,start,receipts,spent,cash,from,receiptCount,expenseCount,donors,key] of rows){
 const p=data.profiles.find(p=>p.slug===slug),old=prior.profiles.find(p=>p.slug===slug);assert.deepEqual(p,mirror.profiles.find(p=>p.slug===slug));
 assert.equal(p.beginning_cash,start);assert.equal(p.money_raised,receipts);assert.equal(p.money_spent,spent);assert.equal(p.ending_cash,cash);
 assert.equal(cents(p.beginning_cash+p.money_raised-p.money_spent),cents(cash));assert.equal(cents(p.net_change),cents(cash-start));
 assert.equal(p.reporting_period_label,`${from}, 2026 to October 5, 2026`);assert.equal(p.reporting_period_type,'custom');assert(p.report_label.includes('28-days-before-election'));
 assert.equal(sum(p.receipt_transactions),cents(receipts));assert.equal(sum(p.expenditure_transactions),cents(spent));assert.equal(sum(p.source_buckets),cents(receipts));assert.equal(sum(p.spending_categories),cents(spent));
 assert.equal(p.receipt_transactions.length,receiptCount);assert.equal(p.expenditure_transactions.length,expenseCount);assert.equal(p.top_donors.length,donors);
 assert.deepEqual(p.filing_history.slice(0,old.filing_history.length),old.filing_history);assert.equal(p.filing_history.length,old.filing_history.length+1);
 assert.deepEqual(p.archived_reporting_periods[0].top_donors,old.top_donors);
 const source='.'+p.latest_filing_href;assert(fs.existsSync(source));const uploaded=fs.readdirSync('../upload').find(n=>n.startsWith(key+'-'));assert(fs.readFileSync(source).equals(fs.readFileSync('../upload/'+uploaded)));
 const page=read('candidates/'+slug+'.html'),rendered=ctx.buildHero(p)+ctx.buildHeroStats(p)+ctx.buildMoneyFlow(p)+ctx.buildHistory(p)+ctx.buildVerification(p)+ctx.buildDonorHighlights(p)+ctx.buildSpendingHighlights(p);
 for(const n of [receipts,spent,cash]){const formatted='$'+n.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});assert(page.includes(formatted));assert(rendered.includes(formatted));}
 assert(page.includes(p.latest_filing_href));assert(rendered.includes(p.latest_filing_href));assert(page.includes('Total receipts'));assert(rendered.includes('Total receipts'));assert(rendered.includes('Filing-period snapshot'));
 assert.equal(data.donor_index.filter(d=>d.slug===slug).length,donors);assert(!data.donor_index.some(d=>d.slug===slug&&(d.type.includes('Aggregate')||d.type==='Refund/Rebate')));
}
for(const p of prior.profiles.filter(p=>!slugs.includes(p.slug)))assert.deepEqual(data.profiles.find(x=>x.slug===p.slug),p);
assert.deepEqual(data.donor_index.filter(d=>!slugs.includes(d.slug)),prior.donor_index.filter(d=>!slugs.includes(d.slug)));
const riley=data.profiles.find(p=>p.slug==='michael-j-riley');assert.equal(riley.finance_status,'available');assert.equal(riley.archived_reporting_periods[0].finance_status,'available_historical');assert.equal(riley.filing_history[0].label,'2019 On-Going Quarterly (3rd)');assert(!read('candidates/michael-j-riley.html').includes('Historical filing only. No 2026'));assert.equal(riley.source_buckets.find(b=>b.label==='Aggregate PAC contributions').amount,400);
const smith=data.profiles.find(p=>p.slug==='shaina-n-smith');assert.equal(smith.loans_payable,1500);assert.equal(smith.loan_proceeds,0);assert.equal(smith.total_fund_balance,54.53);assert.equal(smith.aggregate_expenses,207.09);
const stravato=data.profiles.find(p=>p.slug==='edward-w-stravato');assert.equal(stravato.loans_payable,50000);assert.equal(stravato.total_fund_balance,-23358.89);assert.equal(stravato.loan_proceeds,0);assert(read('candidates/edward-w-stravato.html').includes('-$23,358.89'));
const fascia=data.profiles.find(p=>p.slug==='richard-r-fascia');assert.equal(fascia.loans_payable,2017);assert.equal(fascia.refunds_rebates,225);assert.equal(fascia.aggregate_expenses,868.79);assert.equal(fascia.source_buckets.find(b=>b.label==='Political party contributions').amount,3000);assert.equal(fascia.top_donors.filter(d=>d.type==='Party').length,2);assert.equal(sum(fascia.top_donors),1210896);
for(const slug of slugs){const current=read('candidates/'+slug+'.html'),before=cp.execFileSync('git',['show','fd013de958b2276d9db7c09f72b08fb484fa8104:candidates/'+slug+'.html'],{encoding:'utf8'});const removeFinance=s=>s.replace(/<section class="card" id="finance">[\s\S]*?<\/section>/,'');assert.equal(removeFinance(current),removeFinance(before));}
console.log('PASS: five CF-2 updates, current Riley finances, liabilities, party/PAC distinction, receipts and spending totals, source PDFs, histories, both page displays and other profiles preserved');
