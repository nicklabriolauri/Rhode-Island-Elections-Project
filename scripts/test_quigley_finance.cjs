const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const slug='barbara-quigley',data=JSON.parse(fs.readFileSync('data/candidate_finance_2026.json'));
const p=data.profiles.find(p=>p.slug===slug);
assert.deepEqual(p,JSON.parse(fs.readFileSync('candidate_finance_2026.json')).profiles.find(p=>p.slug===slug));
assert.equal(p.reporting_period_label,'July 1, 2026 to October 5, 2026');
assert.equal(p.reporting_period_type,'custom');assert.equal(p.beginning_cash,5);
assert.equal(p.money_raised,5952.82);assert.equal(p.money_spent,1739.79);assert.equal(p.ending_cash,4218.03);
const cents=n=>Math.round(n*100),sum=rows=>cents(rows.reduce((s,r)=>s+r.amount,0));
assert.equal(cents(p.beginning_cash+p.money_raised-p.money_spent),421803);
assert.equal(cents(p.ending_cash-p.beginning_cash),cents(p.net_change));
assert.equal(sum(p.top_donors),595282);assert.equal(p.top_donors.length,31);
assert.equal(sum(p.top_donors.filter(d=>d.type==='Individual')),335282);
assert.equal(sum(p.top_donors.filter(d=>d.type==='PAC')),260000);
assert.equal(sum(p.spending_categories),173979);assert.equal(sum(p.source_buckets),595282);
assert.equal(p.top_donors.filter(d=>d.donor==='Deborah Doyle').length,1);
assert.equal(p.top_donors.find(d=>d.donor==='Deborah Doyle').amount,25);
for(const name of ['Jon Brien','Mike Chippendale','Marie Hopkins']){
 const donor=p.top_donors.find(d=>d.donor===name);assert.equal(donor.type,'Individual');assert(donor.notes.includes('description'));
}
const index=data.donor_index.filter(d=>d.slug===slug);assert.equal(index.length,31);
assert(!index.some(d=>d.donor==='BARBARA J QUIGLEY RO'));
for(const donor of p.top_donors)assert(index.some(d=>d.donor===donor.donor&&d.amount===donor.amount));
assert.equal(p.filing_history.length,1);assert.equal(p.original_documents.length,2);
for(const doc of p.original_documents)assert(fs.existsSync('.'+doc.href));
const html=fs.readFileSync('finance.html','utf8');
const script=html.match(/<script>([\s\S]*)<\/script>/)[1].replace(/\n    boot\(\);/,'');
const ctx={Intl,URLSearchParams,window:{location:{search:'?slug='+slug}},document:{addEventListener(){}}};
vm.createContext(ctx);vm.runInContext(script,ctx);assert.equal(ctx.getRequestedProfile(data.profiles).slug,slug);
const rendered=ctx.buildHero(p)+ctx.buildMoneyFlow(p)+ctx.buildHistory(p)+ctx.buildVerification(p)+ctx.buildDonorHighlights(p);
const page=fs.readFileSync('candidates/'+slug+'.html','utf8');
for(const amount of ['$5,952.82','$1,739.79','$4,218.03']){assert(rendered.includes(amount));assert(page.includes(amount));}
assert(rendered.includes('Filing-period snapshot'));assert(rendered.includes('Filing history'));
assert(!rendered.includes('Quarter snapshot'));assert(page.includes(p.reporting_period_label));
for(const doc of p.original_documents)assert(rendered.includes(doc.href));
for(const title of ['Responsible Fiscal Management','Affordable Healthcare and Patient Choice','Parental Rights and Education','Economic Expansion and Small Business Growth'])assert(page.includes(title));
console.log('PASS: Quigley updated summary, 31 deduplicated receipts, spending, mirrored data, both page renderings and source PDFs');
