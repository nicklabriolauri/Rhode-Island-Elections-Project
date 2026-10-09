/* Complete filing snapshots: totals and detail always use the same reporting period. */
(async () => {
 const slug=location.pathname.split('/').pop().replace(/\.html$/,'');
 const section=document.getElementById('finance'),side=document.querySelector('aside.side');
 if(!section||!side)return;
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const cash=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n||0);
 try {
  const response=await fetch('/data/candidate_finance_2026.json',{cache:'no-store'});if(!response.ok)return;
  const data=await response.json(),latest=data.profiles.find(p=>p.slug===slug);
  if(!latest||latest.chamber!=='house'||Number(latest.district_number)>25)return;
  const choices=[latest,...(latest.archived_reporting_periods||[]).slice().reverse()];
  const label=p=>/28.days.before/i.test(p.report_label||'')?'28 days before election · 2026':/April 1, 2026 to June 30, 2026|4\/1\/2026.*6\/30\/2026|^Q2 2026$|second.quarter/i.test(p.reporting_period_label||p.report_label||'')?'Q2 2026':p.reporting_period_label||p.report_label;
  const control=document.createElement('section');control.className='card finance-period-card';
  control.innerHTML='<label for="profile-finance-period">Reporting period</label><select id="profile-finance-period">'+choices.map((p,i)=>'<option value="'+i+'">'+esc(label(p))+(i===0?' (latest)':'')+'</option>').join('')+'</select><p class="finance-period-dates"></p><p class="finance-period-help">Switch filings to compare totals, donors and spending.</p>';
  side.prepend(control);
  const render=index=>{
   const p=choices[index];control.querySelector('.finance-period-dates').textContent=p.reporting_period_label;
   const docs=p.latest_filing_href?[{href:p.latest_filing_href,label:'Open selected financial report (PDF) ↗'}]:(p.original_documents||[]).filter(d=>d.period===p.reporting_period_label);
   const table=(rows,expense)=>'<div class="finance-period-table"><table><thead><tr><th>'+(expense?'Payee':'Donor')+'</th><th>Amount</th><th>'+(expense?'Purpose':'Type')+'</th></tr></thead><tbody>'+rows.map(r=>'<tr><td>'+esc(expense?r.payee||r.vendor:r.donor)+'</td><td>'+cash(r.amount)+'</td><td>'+esc(expense?r.purpose||r.category:r.type)+'</td></tr>').join('')+'</tbody></table></div>';
   const receipts=p.receipt_transactions||p.top_donors||[],expenses=p.expenditure_transactions||[];
   section.innerHTML='<h2>Campaign finance snapshot</h2><p class="intro">'+esc(p.report_label)+' · '+esc(p.reporting_period_label)+'</p><div class="metric-grid">'+[['money_raised','Total receipts'],['money_spent','Spent during period'],['ending_cash','Cash at period end']].map(([k,t])=>'<div class="metric"><b>'+cash(p[k])+'</b><span>'+t+'</span></div>').join('')+'</div><a class="finance-profile-button" href="/finance.html?slug='+encodeURIComponent(slug)+'&amp;period='+(index===0?'latest':'archive-'+((latest.archived_reporting_periods||[]).length-index))+'">View campaign finance →</a><details><summary>Donors &amp; receipts ('+receipts.length+')</summary>'+table(receipts,false)+'</details><details><summary>Expenses ('+expenses.length+')</summary>'+(expenses.length?table(expenses,true):'<p>Transaction details have not been transcribed for this filing. See the original report.</p>')+'</details>'+docs.map(d=>'<p class="source"><a href="'+esc(d.href)+'">'+esc(d.label)+'</a></p><details><summary>Read the financial report on this page</summary><iframe title="'+esc(p.candidate_name)+' campaign finance report" src="'+esc(d.href)+'" loading="lazy" style="width:100%;height:640px;border:1px solid #dbe4ef;margin-top:12px"></iframe></details>').join('');
  };
  control.querySelector('select').addEventListener('change',e=>render(Number(e.target.value)));render(0);
 }catch(error){console.warn('Reporting periods unavailable',error);}
})();
