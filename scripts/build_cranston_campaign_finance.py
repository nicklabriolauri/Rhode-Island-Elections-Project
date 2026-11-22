"""Rebuild five Cranston council finance profiles from supplied CF-2/3/4 exports.
Summary variants are retained; no amendment chronology is inferred from UUIDs.
"""
from pathlib import Path
import fitz,re,json,bisect
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'data/finance-documents/cranston-council';out={}
clean=lambda s:' '.join(s.split())
left={'beginning_cash':313.1,'aggregate_receipts':349.1,'individual_receipts':397.1,'party_receipts':409.1,'pac_receipts':421.1,'loan_receipts':433.1,'total_cash':601.1,'aggregate_expenses':625.1,'campaign_expenses':637.1,'loan_repayments':649.1,'ap_repayments':661.1}
right={'ending_cash':373.1,'in_kind_total':427.1,'total_assets':517.1,'accounts_payable':559.1,'loans_payable':571.1,'total_liabilities':637.1,'total_fund_balance':649.1}
for f in sorted(base.glob('*-RICF2-*.pdf')):
 if f.name.startswith('10358'):continue
 doc=fitz.open(f);texts=[p.get_text() for p in doc];offsets=[];pos=0
 for t in texts:offsets.append(pos);pos+=len(t)+1
 text='\n'.join(texts);summary={}
 for side,fields in [(0,left),(1,right)]:
  for k,y in fields.items():
   words=[w[4] for w in doc[0].get_text('words') if abs(w[1]-y)<.3 and (240<w[0]<290 if side==0 else 530<w[0]<590)];v=''.join(words).replace('$','').replace(',','').strip();summary[k]=float(Decimal(v.replace('(','-').replace(')','')))
 summary['money_raised']=round(summary['total_cash']-summary['beginning_cash'],2);summary['money_spent']=round(summary['total_cash']-summary['ending_cash'],2)
 summary['period_start'],summary['period_end']=re.findall(r'\d{2}/\d{2}/\d{4}',texts[0])[:2]
 receipts=[];expenses=[]
 for m in re.finditer(r'Item\s*\nReceipt Date\nDeposit Date\nContribution Amount\n(.*?)Contributor Information',text,re.S):
  b=m.group(1);v=b.split('Transaction Type')[0];a=re.search(r'([\d,]+\.\d{2})',v)
  if not a:continue
  dates=re.findall(r'\d{2}/\d{2}/\d{4}',v);first=re.search(r'Prefix\nFirst Name\nMI\n(.*?)Last Name or PAC/Party Committee Name',b,re.S)[1];last=re.search(r'Last Name or PAC/Party Committee Name\nSuffix\n(.*?)Street Address',b,re.S)[1];typ=clean(re.search(r'Transaction Type\nContribution Type\n(.*?)In Kind/Other Receipts Description',b,re.S)[1]);note=clean(re.search(r'In Kind/Other Receipts Description\n(.*?)Prefix',b,re.S)[1]);emp=clean(re.search(r'Employer Name\n(.*?)Street Address',b,re.S)[1])
  receipts.append(dict(date=dates[0],deposit_date=dates[1] if len(dates)>1 else None,donor=clean(first+' '+last),amount=float(Decimal(a[1].replace(',',''))),type='In-kind' if 'In-Kind' in typ else 'PAC' if typ.endswith('PAC') else 'Party' if typ.endswith('Party') else 'Individual',notes=note,employer=emp,source_page=bisect.bisect_right(offsets,m.start()),source_type=typ))
 for m in re.finditer(r'Check #\nExpenditure Date\nPayment Date\nExpenditure Amount\nDisbursement Type\nExpenditure Type\nPurpose of Expenditure\n(.*?)Payee Information',text,re.S):
  b=m[1];am=re.search(r'\$([\d,]+\.\d{2})',b)
  if not am:continue
  after=b[am.end():].strip().splitlines();kind=after[0];cat=after[1];dates=re.findall(r'\d{2}/\d{2}/\d{4}',b[:am.start()]);payee=re.search(r'Zip\n(.*?)\nSuffix\nLastName or Vendor Name',b,re.S)[1];pn=bisect.bisect_right(offsets,m.start());page=doc[pn-1];before=text[offsets[pn-1]:m.start()];idx=len(re.findall(r'Check #\nExpenditure Date',before));labels=page.search_for('Purpose of Expenditure');rect=labels[idx];purpose=clean(page.get_text(clip=fitz.Rect(27,rect.y1+1,590,rect.y1+14)))
  expenses.append(dict(check_number=clean(b[:re.search(r'\d{2}/\d{2}/\d{4}',b).start()]),date=dates[0],payment_date=dates[1] if len(dates)>1 else None,payee=clean(payee),amount=float(Decimal(am[1].replace(',',''))),type=kind,category=cat,purpose=purpose,source_page=pn))
 out[f.name]=dict(summary=summary,receipts=receipts,expenses=expenses,pages=len(doc))
 print(f.name[:37],summary['beginning_cash'],summary['money_raised'],summary['money_spent'],summary['ending_cash'],'rows',len(receipts),len(expenses),'cash row sums',round(sum(x['amount'] for x in receipts if x['type']!='In-kind'),2),round(sum(x['amount'] for x in expenses if x['type']!='Account Payable'),2))

import hashlib,collections,datetime,copy
from html import escape as esc
reg=json.loads((ROOT/'data/local_representatives.json').read_text());data=json.loads((ROOT/'data/municipal_campaign_finance_2026.json').read_text());D=lambda n:Decimal(str(n));cents=lambda n:int((D(n)*100).to_integral_value())
# Explicit source selection, documented below. File order and UUIDs do not establish amendment order.
def find(prefix):
 matches=[f for f in out if f.startswith(prefix)];assert len(matches)==1,prefix;return matches[0]
configs={
 '10359':('avery-therese-mangahas', [('10359-RICF2-243057-05','10359-RICF2-243057-'),('10359-RICF2-243058-375','10359-RICF2-243058-')]),
 '9834':('andy-m-andujar',[('9834-RICF2-239645-40','9834-RICF2-239645-'),('9834-RICF2-239646-','9834-RICF2-239646-')]),
 '9360':('frank-j-ritz-jr',[('9360-RICF2-239755-3','9360-RICF2-239755-'),('9360-RICF2-239756-','9360-RICF2-239756-')]),
 '325':('michael-a-traficante',[('325-RICF2-239770-','325-RICF2-239770-'),('325-RICF2-239771-','325-RICF2-239771-')]),
 '7963':('daniel-robert-wall',[('7963-RICF2-239780-','7963-RICF2-239780-'),('7963-RICF2-239781-','7963-RICF2-239781-')])}
audit={'reviewed':'2026-11-21','method':'CF-2 totals are selected once per period. CF-3/CF-4 schedules are combined by exact transaction identity, including across PDF page breaks. Account Payable entries are separated from cash disbursements; loan and payable repayments are cash disbursements. Conflicting export summaries remain visible and linked; no amendment order is asserted.','candidates':[]}
new=[]
for committee,(slug,periods) in configs.items():
 person=next(p for p in reg['profiles'] if p['slug']==slug);snapshots=[]
 for idx,(chosen_prefix,group_prefix) in enumerate(periods):
  chosen=find(chosen_prefix);summary=out[chosen]['summary'];files=[f for f in out if f.startswith(group_prefix)];label='28' if idx==0 else '8';start=datetime.datetime.strptime(summary['period_start'],'%m/%d/%Y');end=datetime.datetime.strptime(summary['period_end'],'%m/%d/%Y');period=start.strftime('%B %-d, %Y')+' to '+end.strftime('%B %-d, %Y')
  docs=[dict(label=f'2026 {label} days before election · '+('displayed CF-2 summary' if f==chosen else 'supporting / alternate export'),href='/data/finance-documents/cranston-council/'+f,period=period,original_filename=f,sha256=hashlib.sha256((base/f).read_bytes()).hexdigest(),embed=True) for f in [chosen]+[f for f in files if f!=chosen]]
  def rows(kind):
   rs={}
   for f in files:
    occurrences=collections.Counter()
    for x in out[f][kind]:
     # Exact duplicate entries in overlapping exports count only once; unlike spellings and classifications are reviewed below.
     key=(x['date'],x.get('donor',x.get('payee')),x['amount'],x['type'],x.get('purpose',x.get('notes')),x.get('check_number'))
     occurrences[key]+=1;key=key+(occurrences[key],)
     if key not in rs:rs[key]=x|{'source_document':'/data/finance-documents/cranston-council/'+f}
   return list(rs.values())
  receipts=rows('receipts');expenses=rows('expenses');note=''
  if committee=='9360' and idx==0:
   old=[x for x in receipts if x['date']=='09/03/2026' and x['amount']==1000 and x['type']=='Individual'];assert len(old)==1
   receipts.remove(old[0]);note='The $1,000 International Brotherhood of Police contribution appears in both individual and PAC forms. It is counted once as PAC support, matching the alternate CF-2 split of $850 individuals and $1,650 PACs. The full-schedule export instead classifies it among individuals. Total cash receipts remain $2,500 in both summaries.'
  if committee=='10359':
   for x in receipts:
    if not x['donor']:x['type']='Aggregate';x['donor']='Aggregate contributions (unnamed)';x['notes']='Reported in aggregate; no individual donor identities are supplied.'
   note=('Four supplied 28-day exports show the same $310 receipts and $3,047.59 cash disbursements, but different opening and closing cash. The displayed $4,073.66 opening and $1,336.07 closing come from the export that matches the displayed next-period opening. Alternate closing balances are $1,311.07, $656.07 and $531.07. No amendment timestamps establish which version is authoritative. Transaction schedules reconcile to receipts and disbursements; the opening-balance changes are unexplained.' if idx==0 else 'The two supplied 8-day exports show the same $130.76 aggregate receipts and $1,040.31 cash disbursements, but closing cash differs by $25 ($426.52 versus $401.52). The displayed export opens at $1,336.07, matching the selected 28-day closing balance. No amendment timestamp establishes which version is authoritative. Both original exports are retained for comparison.')
  if committee=='9834':note=('The full schedules show $6,954.08 campaign expenses. A separate export adds a $250 payment to Dan Wall and reports total expenses of $7,204.08, opening cash of $7,231.36 and closing cash of $127.28; that summary is displayed, with all 21 cash expenses counted once. The earlier full-schedule summary shows opening cash of $7,606.36 and closing cash of $752.28. These are conflicting exports, not separate periods. The subsequent report opens at $377.28, $250 above the displayed closing balance; this difference is unexplained.' if idx==0 else 'The preceding 28-day summary closes at $127.28, but this report opens at $377.28, a $250 unexplained increase. Each report reconciles internally; no adjustment has been invented to bridge them.')
  cash=[x for x in receipts if x['type']!='In-kind'];inkind=[x for x in receipts if x['type']=='In-kind'];payables=[x for x in expenses if x['type']=='Account Payable'];spent=[x for x in expenses if x['type']!='Account Payable']
  total=lambda xs:sum(cents(x['amount']) for x in xs)
  for rs,target in [(cash,summary['money_raised']),(spent,summary['money_spent']),(inkind,summary['in_kind_total'])]:assert total(rs)==cents(target),(slug,label,target,total(rs))
  assert cents(summary['beginning_cash'])+cents(summary['money_raised'])-cents(summary['money_spent'])==cents(summary['ending_cash'])
  assert cents(summary['total_assets'])-cents(summary['total_liabilities'])==cents(summary['total_fund_balance'])
  buckets=[]
  for typ,k,cls,title in [('Individual','individual_receipts','individuals','Itemized individual contributions'),('PAC','pac_receipts','pacs','PAC contributions'),('Party','party_receipts','other','Political party contributions'),('Aggregate','aggregate_receipts','aggregate','Aggregate contributions (unnamed)')]:
   amount=total([x for x in cash if x['type']==typ])/100;assert cents(amount)==cents(summary[k]),(slug,label,typ,amount,summary[k])
   if amount:buckets.append(dict(label=title,amount=amount,class_name=cls,description='Contribution type as filed, with source corrections explained in the verification note.'))
  donors=collections.defaultdict(list)
  for x in cash:
   if x['type']!='Aggregate':donors[(x['donor'],x['type'])].append(x)
  top=sorted([dict(donor=n,amount=total(rs)/100,type=t,interest_group=t,notes='; '.join(sorted(set('Employer as filed: '+r['employer'] for r in rs if r['employer'])))) for (n,t),rs in donors.items()],key=lambda x:(-x['amount'],x['donor']))
  cats=collections.defaultdict(list)
  for x in spent:cats[x['type'] if x['type']!='Campaign Expenditure' else x['category']].append(x)
  p=dict(candidate_id='cranston-council-'+str(person['ward'])+'-'+slug,slug=slug,candidate_name=person['name'],chamber='municipal',district_number=str(person['ward']),ward=person['ward'],municipality='Cranston',party=person['party'],party_label='Democratic' if person['party']=='DEM' else 'Republican',office_sought='Cranston City Council · Ward '+str(person['ward']),profile_url=person['profile'],ward_map='/cranston-map.html?ward='+str(person['ward'])+'&colors=returns',committee_key=committee,finance_status='available',reporting_period_type='custom',receipts_label='Cash raised',report_label=f'2026 {label}-days-before-election',reporting_period_label=period,period_start=start.date().isoformat(),period_end=end.date().isoformat(),**{k:v for k,v in summary.items() if k not in ['period_start','period_end']},net_change=round(summary['money_raised']-summary['money_spent'],2),total_cash_receipts=summary['money_raised'],receipt_transactions=cash,in_kind_transactions=inkind,expenditure_transactions=spent,accounts_payable_transactions=payables,original_documents=docs,latest_filing_href=docs[0]['href'],top_donors=top,source_buckets=buckets,spending_categories=[dict(title=k,amount=total(rs)/100,description='Cash disbursements itemized in the supplied CF-4 schedules.') for k,rs in cats.items()],coverage_note='Amounts cover the exact dates of this filing, not the full election cycle. Account Payable schedule entries record obligations incurred, some repaid in the same period; they are not added to cash spending. In-kind support is separate from cash receipts.',summary_intro='Cranston ward council campaign finance. Switch reporting periods to update cash totals, donors, expenses and original source PDFs together.',source_note='User-supplied Rhode Island Board of Elections CF-2/3/4 exports. Committee '+committee+'. Reviewed November 21, 2026.',takeaways=[],explainer_cards=[])
  p['finance_audit_note']=note or 'Cash receipts, cash disbursements and in-kind schedules reconcile to the selected CF-2 summary. Cash disbursements include any loan repayments or accounts-payable repayments shown separately below. Ending cash is not reduced by outstanding loans in the cash-on-hand figure.'
  p['source_summary_variants']=[dict(document='/data/finance-documents/cranston-council/'+f,displayed=f==chosen,**out[f]['summary']) for f in [chosen]+[f for f in files if f!=chosen]]
  snapshots.append(p)
 latest=copy.deepcopy(snapshots[1]);latest['archived_reporting_periods']=[snapshots[0]];latest['filing_history']=[{k:p[k] for k in ['report_label','reporting_period_label','money_raised','money_spent','ending_cash','net_change']} for p in snapshots]
 new.append(latest);person['finance_url']='/finance.html?slug='+slug;person['finance_status']='available'
 audit['candidates'].append(dict(slug=slug,name=person['name'],committee_key=committee,periods=[dict(report_label=p['report_label'],cash_receipts=p['money_raised'],cash_disbursements=p['money_spent'],closing_cash=p['ending_cash'],cash_rows=len(p['receipt_transactions']),expense_rows=len(p['expenditure_transactions']),in_kind=p['in_kind_total'],source_variants=p['source_summary_variants'],note=p['finance_audit_note']) for p in snapshots]))
 # Update only this candidate's finance card and navigation, preserving all other research and election links.
 page=ROOT/person['profile'].lstrip('/');s=page.read_text();fmt=lambda n:f'${n:,.2f}'
 finance=f'<section class="card" id="finance"><h2>Campaign finance</h2><p class="intro">8 days before the 2026 election · October 6–26, 2026</p><div class="metric-grid"><div class="metric"><b>{fmt(latest["money_raised"])}</b><span>Cash raised</span></div><div class="metric"><b>{fmt(latest["money_spent"])}</b><span>Cash disbursed</span></div><div class="metric"><b>{fmt(latest["ending_cash"])}</b><span>Cash at period end</span></div></div><p>Both 28-day and 8-day reports are available. Open the finance page to choose a reporting period, view donors and expenses, and read the original filings.</p><p>Outstanding loans: {fmt(latest["loans_payable"])}. Accounts payable: {fmt(latest["accounts_payable"])}. Reported fund balance after liabilities: {fmt(latest["total_fund_balance"])}.</p><p>{esc(latest["finance_audit_note"])}</p><a class="finance-profile-button" href="{esc(person["finance_url"],quote=True)}">Explore campaign finance</a><p class="source">Rhode Island Board of Elections · Committee {committee} · Supplied exports reviewed November 21, 2026. Totals cover this reporting period, not the full cycle.</p></section>'
 s=re.sub(r'<section class="card" id="finance">.*?</section>',lambda _:finance,s,flags=re.S)
 s=s.replace('<a href="'+person['finance_url']+'">Campaign finance</a>','');s=s.replace('<a href="/?view=full">Find your representatives</a>','<a href="'+person['finance_url']+'">Campaign finance</a><a href="/?view=full">Find your representatives</a>');page.write_text(s)
# Keep Haupt's verified reports and all source documents unchanged.
slugs={p['slug'] for p in new};data['profiles']=[p for p in data['profiles'] if p['slug'] not in slugs]+new
data['directory']=[p for p in data['directory'] if p['slug'] not in slugs]+[{k:p[k] for k in ['candidate_name','slug','candidate_id','chamber','district_number','party','office_sought','municipality','ward','profile_url','ward_map']}|{'has_profile':True} for p in new]
data['donor_index']=[x|{k:p[k] for k in ['candidate_id','candidate_name','chamber','district_number','party','slug']} for p in data['profiles'] for x in p['top_donors']];data['coverage_note']='Six Cranston ward council campaign finance profiles. Amounts are filing-period totals; report date ranges vary. Source conflicts are documented on the affected profiles.'
for file,obj in [('data/local_representatives.json',reg),('data/municipal_campaign_finance_2026.json',data),('data/cranston-council-finance-audit.json',audit)]: (ROOT/file).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
print('Built five finance profiles and retained Haupt. All 10 new filing-period cash summaries and schedules reconcile.')
