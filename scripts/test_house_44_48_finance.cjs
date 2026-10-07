const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),cp=require('child_process');
const read=p=>fs.readFileSync(p,'utf8'),data=JSON.parse(read('data/candidate_finance_2026.json')),mirror=JSON.parse(read('candidate_finance_2026.json'));
const prior=JSON.parse(cp.execFileSync('git',['show','6dd4faab4a6766277bd90ae87538b18ee950c3b9:data/candidate_finance_2026.json'],{encoding:'utf8',maxBuffer:4000000}));
const cents=n=>Math.round(n*100),sum=rows=>cents(rows.reduce((s,r)=>s+r.amount,0));
const html=read('finance.html'),script=html.match(/<script>([\s\S]*)<\/script>/)[1].replace(/\n    boot\(\);/,'');
const ctx={Intl,URLSearchParams,window:{location:{search:''}},document:{addEventListener(){}}};vm.createContext(ctx);vm.runInContext(script,ctx);
const rows=[['gregory-costantino',56823.77,0,8042.51,48781.26,'July 1',0,5,0,'7176'],['mia-a-ackerman',49463.38,2690.63,4533.60,47620.41,'July 1',3,20,1,'6184'],['joseph-hosey',19132.25,3924.83,4684.34,18372.74,'July 1',24,21,21,'10224'],['mary-ann-shallcross-smith',41142.61,304.36,20564.93,20882.04,'July 1',6,9,3,'547'],['david-j-place',4427.49,1348.83,4617.80,1158.52,'July 1',9,21,1,'6988'],['brian-c-newberry',15008.49,601.24,9222.49,6387.24,'July 1',5,42,0,'5624']];
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
const bySlug=slug=>data.profiles.find(p=>p.slug===slug);
const mary=bySlug('mary-ann-shallcross-smith');assert.equal(mary.loan_repayments,20000);assert.equal(mary.campaign_expenses,564.93);assert.equal(mary.loans_payable,27527.58);assert.equal(mary.total_fund_balance,-6645.54);assert.equal(mary.interest_received,54.36);assert(read('candidates/mary-ann-shallcross-smith.html').includes('$20,000.00 loan repayment'));
const hosey=bySlug('joseph-hosey');assert.equal(hosey.in_kind_contributions,282.56);assert.equal(sum(hosey.in_kind_transactions),28256);assert.equal(hosey.source_buckets.find(b=>b.label==='Political party contributions').amount,350);assert.equal(hosey.top_donors.filter(d=>d.type==='Party').length,2);assert.equal(hosey.top_donors.find(d=>d.donor==='Patrick Hosey').amount,780.75);assert.equal(hosey.loans_payable,20000);assert.equal(hosey.loan_proceeds,0);assert.equal(hosey.total_fund_balance,-1627.26);
const ackerman=bySlug('mia-a-ackerman');assert.equal(ackerman.in_kind_contributions,120);assert.equal(sum(ackerman.in_kind_transactions),12000);assert.equal(ackerman.refunds_rebates,2490.63);assert.equal(ackerman.top_donors[0].donor,'PROVIDENCE CHAMBER PAC');assert.equal(ackerman.top_donors[0].amount,200);
const costantino=bySlug('gregory-costantino');assert.equal(costantino.loans_payable,192269);assert.equal(costantino.total_fund_balance,-143487.74);assert.equal(costantino.top_donors.length,0);
const place=bySlug('david-j-place');assert.equal(place.aggregate_expenses,607.23);assert.equal(place.refunds_rebates,71.47);assert.equal(place.interest_received,.46);assert.equal(place.top_donors[0].donor,'Lisa Curtis');
const newberry=bySlug('brian-c-newberry');assert.equal(newberry.source_buckets.find(b=>b.label==='Aggregate PAC contributions').amount,400);assert.equal(newberry.top_donors.length,0);assert.equal(newberry.aggregate_expenses,2600.41);assert.equal(newberry.refunds_rebates,200);assert.equal(newberry.interest_received,1.24);
for(const p of data.profiles.filter(p=>slugs.includes(p.slug)))assert.equal(p.loan_proceeds,0);
for(const slug of slugs){const current=read('candidates/'+slug+'.html'),before=cp.execFileSync('git',['show','6dd4faab4a6766277bd90ae87538b18ee950c3b9:candidates/'+slug+'.html'],{encoding:'utf8'});const removeFinance=s=>s.replace(/<section class="card" id="finance">[\s\S]*?<\/section>/,'');assert.equal(removeFinance(current),removeFinance(before));}
console.log('PASS: six CF-2 updates, reconciliation, in-kind support, party/PAC distinction, interest and refunds, loan repayment and liabilities, source PDFs, histories, both page displays and unrelated profiles preserved');
