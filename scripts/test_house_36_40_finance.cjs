const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),cp=require('child_process');
const read=p=>fs.readFileSync(p,'utf8'),data=JSON.parse(read('data/candidate_finance_2026.json')),mirror=JSON.parse(read('candidate_finance_2026.json'));
const prior=JSON.parse(cp.execFileSync('git',['show','12f3be18edd4884db5efad57772496f6f0d4ee0e:data/candidate_finance_2026.json'],{encoding:'utf8',maxBuffer:2000000}));
const cents=n=>Math.round(n*100),sum=rows=>cents(rows.reduce((s,r)=>s+r.amount,0));
const html=read('finance.html'),script=html.match(/<script>([\s\S]*)<\/script>/)[1].replace(/\n    boot\(\);/,'');
const ctx={Intl,URLSearchParams,window:{location:{search:''}},document:{addEventListener(){}}};vm.createContext(ctx);vm.runInContext(script,ctx);
const rows=[['tina-l-spears',9011.93,1454,3143.07,7322.86,'September 2',5,10,4,'9385'],['samuel-angelo-azzinaro',19778.28,3175,2823.36,20129.92,'July 1',6,6,5,'913'],['brian-patrick-kennedy',67756.55,2307.27,7457.67,62606.15,'September 2',7,14,4,'1364'],['megan-l-cotter',28600.20,21264.19,19403.05,30461.34,'July 1',104,25,102,'9018'],['michael-chippendale',19694.29,1632.42,4403.54,16923.17,'July 1',9,43,1,'6999']];
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
const az=data.profiles.find(p=>p.slug==='samuel-angelo-azzinaro');assert.equal(az.in_kind_contributions,535.36);assert.equal(sum(az.in_kind_transactions),53536);assert.equal(az.aggregate_expenses,379.58);assert.equal(sum(az.receipt_transactions),317500);assert.equal(az.in_kind_transactions[0].donor,'WESTERLY DEMOCRATIC TOWN COMMITTEE');assert(!az.top_donors.some(d=>d.donor==='WESTERLY DEMOCRATIC TOWN COMMITTEE'));assert(read('candidates/samuel-angelo-azzinaro.html').includes('$535.36 in non-cash advertising support'));
const kennedy=data.profiles.find(p=>p.slug==='brian-patrick-kennedy');assert.equal(kennedy.refunds_rebates,1282.27);assert.equal(sum(kennedy.top_donors),102500);
const cotter=data.profiles.find(p=>p.slug==='megan-l-cotter');assert.equal(cotter.accounts_payable,500);assert.equal(cotter.total_fund_balance,29961.34);assert(cotter.top_donors.some(d=>d.donor==='RI ALLIANCE SSE SEIU COPE (Social Service Employees)'&&d.amount===2000));
const chip=data.profiles.find(p=>p.slug==='michael-chippendale');assert.equal(chip.loans_payable,7882.85);assert.equal(chip.total_fund_balance,9040.32);assert.equal(chip.refunds_rebates,74.54);assert.equal(chip.other_receipts,149.82);assert.equal(chip.source_buckets.find(b=>b.label==='Aggregate PAC contributions').amount,100);assert.equal(sum(chip.top_donors),20820);
for(const slug of slugs){const current=read('candidates/'+slug+'.html'),before=cp.execFileSync('git',['show','12f3be18edd4884db5efad57772496f6f0d4ee0e:candidates/'+slug+'.html'],{encoding:'utf8'});const removeFinance=s=>s.replace(/<section class="card" id="finance">[\s\S]*?<\/section>/,'');assert.equal(removeFinance(current),removeFinance(before));}
console.log('PASS: five filings, cash/in-kind separation, receipts, expenses, liabilities, donor attribution, history, source PDFs, both page displays and unrelated records preserved');
