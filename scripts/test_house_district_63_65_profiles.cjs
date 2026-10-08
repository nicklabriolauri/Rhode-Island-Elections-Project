const fs=require('fs'),assert=require('assert/strict'),cp=require('child_process'),vm=require('vm'),crypto=require('crypto');
const read=p=>fs.readFileSync(p,'utf8'),load=p=>JSON.parse(read(p));
const main=load('data/candidate_finance_2026.json'),mirror=load('candidate_finance_2026.json');
const old=JSON.parse(cp.execFileSync('git',['show','eae88e6:data/candidate_finance_2026.json'],{encoding:'utf8',maxBuffer:12e6}));
const entries=[['katherine-sheena-kazarian',63,12325,40849.95,157297.92,23,80],['jenni-a-furtado',64,1096.07,2314.51,9499.73,2,9],['matthew-dawson',65,750,10079.27,19569.26,2,11]];
const slugs=entries.map(x=>x[0]),cents=n=>Math.round(n*100),sum=rs=>cents(rs.reduce((n,r)=>n+r.amount,0));
for(const [slug,d,raised,spent,end,nr,ne] of entries){
 const p=main.profiles.find(p=>p.slug===slug),prior=old.profiles.find(p=>p.slug===slug),page=read(`candidates/${slug}.html`);
 assert.deepEqual(p,mirror.profiles.find(p=>p.slug===slug));assert.deepEqual([p.money_raised,p.money_spent,p.ending_cash],[raised,spent,end]);
 assert.equal(sum(p.receipt_transactions),cents(raised));assert.equal(sum(p.expenditure_transactions),cents(spent));assert.equal(sum(p.source_buckets),cents(raised));assert.equal(sum(p.spending_categories),cents(spent));assert.equal(cents(p.beginning_cash+raised-spent),cents(end));assert.equal(cents(end-p.total_liabilities),cents(p.total_fund_balance));
 assert.equal(p.receipt_transactions.length,nr);assert.equal(p.expenditure_transactions.length,ne);assert.equal(p.reporting_period_start,d===65?'2026-09-02':'2026-07-01');
 const snapshot={...prior};delete snapshot.filing_history;delete snapshot.archived_reporting_periods;assert.deepEqual(p.archived_reporting_periods.at(-1),snapshot);assert.deepEqual(p.filing_history.slice(0,-1),prior.filing_history);
 const sourceHashes={'katherine-sheena-kazarian': '6f5d01814b16afef648280820e7ed41d358ddf3810f0b55d809c8a29700c2de8', 'jenni-a-furtado': '911cdbd6f24cdd82b4c4b48aebf425c5af8220581171759b370d5d96d7414e20', 'matthew-dawson': '60ae62c40af7e5b0b1b01ea30b27ba5ed58c4298763c9231489e60f3cb68d9f4'};assert.equal(crypto.createHash('sha256').update(fs.readFileSync(p.latest_filing_href.slice(1))).digest('hex'),sourceHashes[slug]);
 for(const text of [p.reporting_period_label,p.latest_filing_href,'<iframe','of 75 House district records','data-voting-widget','ACLU of Rhode Island','Session attendance'])assert(page.includes(text),slug+' '+text);
 assert(!page.includes('Senate District'));assert(page.includes('Official results'));assert(page.includes(`/running.html?chamber=house&amp;district=${d}&amp;election=general`));
 for(const route of ['index.html','ballot.html','running.html','race-page.js','candidate-profiles.html'])assert(read(route).includes(slug));
 assert(read(`races/house-${d}.html`).includes('house63-65'));
 const ids=[...page.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(ids.length,new Set(ids).size);for(const m of page.matchAll(/href="#([^"]+)"/g))assert(ids.includes(m[1]));
 assert(fs.statSync(`candidates/${slug}.jpg`).size>10000);
}
for(const p of main.profiles)if(![...slugs,'jennifer-smith-boylan','nicole-p-jellinek','june-s-speakman','susan-ann-donovan','john-g-edwards','terri-denise-cortvriend','marvin-abney','alex-finkelman','lauren-h-carson','michelle-e-mcgaw'].includes(p.slug))assert.deepEqual(p,old.profiles.find(x=>x.slug===p.slug),p.slug);
assert.deepEqual(main.donor_index.filter(p=>![...slugs,'jennifer-smith-boylan','nicole-p-jellinek','june-s-speakman','susan-ann-donovan','john-g-edwards','terri-denise-cortvriend','marvin-abney','alex-finkelman','lauren-h-carson','michelle-e-mcgaw'].includes(p.slug)),old.donor_index.filter(p=>![...slugs,'jennifer-smith-boylan','nicole-p-jellinek','june-s-speakman','susan-ann-donovan','john-g-edwards','terri-denise-cortvriend','marvin-abney','alex-finkelman','lauren-h-carson','michelle-e-mcgaw'].includes(p.slug)));
const aclu=load('data/outside_ratings_2026.json').ratings.find(r=>r.organization==='ACLU of Rhode Island'&&r.chamber==='house'&&r.district_number===59);assert.equal(aclu.rating,'11/11');assert.equal(aclu.votes.length,11);assert(aclu.votes.every(v=>v.status==='aligned'));assert(read('candidates/jennifer-a-stewart.html').includes('<b>11/11</b>'));
assert(read('candidates/jenni-a-furtado.html').includes('House service, which began in 2025'));
const html=read('finance.html'),nodes={financeApp:{innerHTML:''},financeFilingSelect:{addEventListener(e,cb){this[e]=cb;}}};
const ctx={URL,URLSearchParams,window:{location:{search:'?slug=jenni-a-furtado',href:'https://example.org/finance.html?slug=jenni-a-furtado'},history:{replaceState(a,b,url){ctx.window.location.href=String(url);ctx.window.location.search=url.search;}}},document:{getElementById:id=>nodes[id]},escapeHtml:s=>String(s),formatCurrency:n=>'$'+Number(n).toFixed(2)};
vm.createContext(ctx);
for(const name of ['filingChoices','filingView','buildTransactions','buildFilingControl','renderProfile']){const start=html.indexOf('    function '+name+'('),end=html.indexOf('\n    function ',start+5);assert(start>=0);vm.runInContext(html.slice(start,end),ctx);}
for(const name of ['buildHero','buildPacTopicPanel','buildDonorHighlights','buildSpendingHighlights','buildHistory','buildVerification'])ctx[name]=p=>JSON.stringify({raised:p.money_raised,donors:p.top_donors,expenses:p.spending_categories,docs:p.original_documents});
for(const slug of [...slugs,'leonela-felix']){
 const p=main.profiles.find(p=>p.slug===slug),choices=ctx.filingChoices(p),q2=choices.find(x=>x.label==='Q2 2026');assert(q2,'Q2 option '+slug);
 ctx.renderProfile(p,main,'latest');assert(nodes.financeApp.innerHTML.includes(p.latest_filing_href));assert(nodes.financeApp.innerHTML.includes('Donors &amp; expenses'));
 nodes.financeFilingSelect.change({target:{value:q2.key}});assert.equal(new URL(ctx.window.location.href).searchParams.get('period'),q2.key);assert(!nodes.financeApp.innerHTML.includes(p.latest_filing_href),'latest document leaked into Q2');assert(nodes.financeApp.innerHTML.includes(String(q2.snapshot.money_raised)));
 const view=ctx.filingView(q2,p);assert.equal(view.money_spent,q2.snapshot.money_spent);assert(!view.receipt_summary_adjustments?.length,'latest adjustment leaked into Q2');assert.equal(view.top_donors,q2.snapshot.top_donors);
 ctx.renderProfile(p,main,'invalid');assert(nodes.financeApp.innerHTML.includes(p.latest_filing_href));
}
console.log('PASS: D63–65 profiles, source PDFs, finance/history reconciliation, Stewart ACLU and filing selector isolation');
