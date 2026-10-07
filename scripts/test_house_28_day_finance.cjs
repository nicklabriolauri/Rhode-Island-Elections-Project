const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),cp=require('child_process');
const read=p=>fs.readFileSync(p,'utf8'),data=JSON.parse(read('data/candidate_finance_2026.json')),mirror=JSON.parse(read('candidate_finance_2026.json'));
const prior=JSON.parse(cp.execFileSync('git',['show','db4a0e7f9fe1e1935abd8116dae91064f05c403e:data/candidate_finance_2026.json'],{encoding:'utf8',maxBuffer:2000000}));
const cents=n=>Math.round(n*100),sum=rows=>cents(rows.reduce((s,r)=>s+r.amount,0));
const html=read('finance.html'),script=html.match(/<script>([\s\S]*)<\/script>/)[1].replace(/\n    boot\(\);/,'');
const ctx={Intl,URLSearchParams,window:{location:{search:''}},document:{addEventListener(){}}};vm.createContext(ctx);vm.runInContext(script,ctx);
const rows=[['james-c-sheehan',3495.41,791.25,4082.38,204.28,'September 2',3,12,1,'4665'],['robert-e-craven-jr',56056.98,2474,1016.59,57514.39,'September 2',14,14,14,'9140'],['carol-hagan-mcentee',83982.92,3350,11339.79,75993.13,'July 1',5,26,5,'2834'],['jessica-drew-day',5311.61,1125,6192.31,244.30,'July 1',6,20,2,'9372']];
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
const s=data.profiles.find(p=>p.slug==='james-c-sheehan');assert.equal(s.loan_proceeds,300);assert.equal(s.refunds_rebates,241.25);assert.equal(s.loans_payable,66243.01);assert.equal(sum(s.top_donors),25000);assert(read('candidates/james-c-sheehan.html').includes('$241.25 yard-sign refund'));
const day=data.profiles.find(p=>p.slug==='jessica-drew-day');assert.equal(sum(day.top_donors),60000);assert.equal(day.source_buckets.find(b=>b.class_name.includes('aggregate')).amount,525);
assert.equal(data.profiles.find(p=>p.slug==='carol-hagan-mcentee').aggregate_expenses,13.31);
console.log('PASS: all four 28-day filings reconcile; source PDFs, history, donors, categories and both page displays; unrelated profiles preserved');
