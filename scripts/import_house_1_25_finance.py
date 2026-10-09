"""Import the supplied combined CF-2 reports, preserving complete previous snapshots."""
import json,re,copy,subprocess,datetime,unicodedata
from pathlib import Path
from pypdf import PdfReader,PdfWriter
ROOT=Path(__file__).resolve().parents[1]
def norm(s):return re.sub('[^a-z]','',unicodedata.normalize('NFKD',s.lower()))
def money(s):return float(s.replace(',','').replace('$','').replace('(','-').replace(')','').strip())
def parse(text):
 lines=text.splitlines(); summary=text.split('\f')[0]
 def value(label):
  m=re.search(label+r'\s+\$?\s*(\(?-?[\d,]+(?:\.\d{2})?\)?)',summary);assert m,label;return money(m[1])
 begin=value('Beginning Cash Balance');end=value('Ending Cash Balance');raised=round(value('3. Total Cash')-begin,2);spent=round(begin+raised-end,2)
 dates=re.search(r'Period Beginning:\s*(\d+/\d+/\d+)\s+Period Ending:\s*(\d+/\d+/\d+)',summary).groups()
 receipts=[];expenses=[];inkind=[];unpaid=[]
 for page in text.split('\f')[2:]:
  ls=page.splitlines();kind='expenses' if ('SCHEDULE OF EXPENDITURES' in page or 'Disbursement Type' in page) else 'receipts' if ('Contribution Type' in page or 'SCHEDULE OF CONTRIBUTIONS' in page) else None
  if not kind:continue
  starts=[]
  for i,l in enumerate(ls):
   m=re.search(r'(\d{2}/\d{2}/\d{4})\s+(?:(\d{2}/\d{2}/\d{4})\s+)?(.+?)\s+\$?([\d,]+\.\d{2})\s*$',l)
   if m and (kind=='expenses' or not re.search('From:|Reporting Period',l)):starts.append((i,m))
  for j,(i,m) in enumerate(starts):
   block=ls[i+1:starts[j+1][0] if j+1<len(starts) else len(ls)];amount=money(m[4]);line=ls[i]
   name='';purpose=''
   for k,l in enumerate(block):
    if 'Prefix' in l and ('Last Name' in l or 'LastName' in l) and k+1<len(block):
     n=block[k+1];right=l.find('Employer Name')
     name=' '.join((n[:right] if right>0 else n).split())
     if name.startswith('Street Address'):name=''
    if ('Purpose of Expenditure' in l or 'In Kind/Other Receipts Description' in l):
     following=[]
     for n in block[k+1:]:
      if 'Contributor Information' in n or 'Payee Information' in n or 'Prefix' in n:break
      if n.strip():following.append(n.strip())
     purpose=' '.join(following)
   if kind=='expenses':
    cat=re.sub(r'^(?:Campaign Expenditure|Aggregate Expenditure|Accounts Payable|Loan Repayment)\s+','',m[3]).strip()
    row=dict(date=m[1],payee=name or 'Reported in aggregate',amount=amount,type='Expenditure',category=cat,purpose=purpose)
    if 'Refund of Contribution' in m[3]:receipts.append(dict(date=m[1],donor=name or 'Returned contribution',amount=-amount,type='Returned contribution',notes=purpose))
    else:(unpaid if re.search(r'Account.? Payable',m[3]) else expenses).append(row)
   else:
    before=line[:m.start()].strip();typ='Aggregate' if 'Aggregate' in before else 'PAC' if 'PAC' in before else 'Party' if 'Political Party' in before else 'Individual' if 'Individual' in before else 'Loan' if 'Loan' in before else 'Interest' if 'Interest' in before else 'Refund/Rebate' if 'Refund' in before else 'Other'
    row=dict(date=m[1],donor=name or ('Unitemized / aggregate receipts' if typ=='Aggregate' else typ),amount=amount,type=typ,notes=purpose)
    (inkind if 'In-Kind' in before else receipts).append(row)
 returned=value('13. Returned Contributions')
 if returned and round(sum(r['amount'] for r in receipts)+returned,2)==raised:
  receipts.append(dict(date=dates[1],donor='Returned contributions (CF-2 summary)',amount=returned,type='Returned contribution',notes='Summary adjustment; the summary does not identify the original donor.'))
 return dict(beginning_cash=begin,money_raised=raised,money_spent=spent,ending_cash=end,net_change=round(end-begin,2),total_cash_receipts=raised,campaign_expenses=value('b. Campaign Expenses'),aggregate_expenses=value('a. Aggregate Expenses'),loans_payable=value('b. Loans Payable'),accounts_payable=value('a. Accounts Payable'),total_liabilities=value('11. Total Liabilities'),total_fund_balance=value('12. Total Fund Balance'),loan_proceeds=value('5. Loan Proceeds'),refunds_rebates=value('9. Refund/Rebate'),returned_contributions=returned,receipt_transactions=receipts,expenditure_transactions=expenses,in_kind_transactions=inkind,accounts_payable_transactions=unpaid),dates

def main(source):
 data=json.loads((ROOT/'data/candidate_finance_2026.json').read_text());reader=PdfReader(source);starts=[i for i,p in enumerate(reader.pages) if 'SUMMARY OF CAMPAIGN ACTIVITY' in p.extract_text()];updated=[]
 kubicek=dict(candidate_id='house-5-oth-general-brittany-m-kubicek',slug='brittany-m-kubicek',candidate_name='Brittany M Kubicek',chamber='house',district_number='5',party='IND',party_label='Independent',office_sought='State Representative',report_label='2026 year to date through Q2',reporting_period_label='January 1, 2026 to June 30, 2026',beginning_cash=0,money_raised=16771.76,money_spent=12753.07,ending_cash=4018.69,net_change=4018.69,top_donors=[],source_buckets=[],spending_categories=[],original_documents=[],filing_history=[],coverage_note='Previously published year-to-date totals from Q1 and Q2; not standalone Q2 amounts.')
 if not any(p['slug']==kubicek['slug'] for p in data['profiles']):data['profiles'].append(kubicek)
 aliases={'christopher leslie ireland':'christopher-l-ireland','ramon a perez':'ramon-perez','zakary pereira':'zakary-j-pereira','anthony j desimone':'anthony-j-desimone','rebecca kislak':'rebecca-m-kislak','amy joseph santiago':'amy-j-santiago'}
 for idx,start in enumerate(starts):
  stop=starts[idx+1] if idx+1<len(starts) else len(reader.pages);writer=PdfWriter()
  for page in reader.pages[start:stop]:writer.add_page(page)
  temp=Path('/tmp/house-report.pdf');writer.write(temp);text=subprocess.check_output(['pdftotext','-layout',str(temp),'-'],text=True)
  name=re.search(r'Name of Candidate[^\n]*\n([^\n]+)',text)[1];name=re.sub(r'\s+\d+\s*$','',name).strip()
  candidates=[p for p in data['profiles'] if p['chamber']=='house' and (norm(name)==norm(p['candidate_name']) or (name.split()[0].lower()==p['candidate_name'].split()[0].lower() and name.split()[-1].lower()==p['candidate_name'].split()[-1].lower()))]
  if name.lower() in aliases:candidates=[p for p in data['profiles'] if p['slug']==aliases[name.lower()]]
  assert len(candidates)==1,(name,[p['slug'] for p in candidates]);p=candidates[0];new,dates=parse(text)
  for field,target in [('receipt_transactions','money_raised'),('expenditure_transactions','money_spent')]:
   actual=round(sum(t['amount'] for t in new[field]),2)
   assert actual==new[target],(name,field,actual,new[target])
  slug=p['slug'];href=f'/data/finance-documents/{slug}-28-days-before-election-2026.pdf';writer.write(ROOT/href.lstrip('/'))
  same=p.get('reporting_period_label')==period(dates) and p.get('money_raised')==new['money_raised'] and p.get('money_spent')==new['money_spent']
  archives=copy.deepcopy(p.get('archived_reporting_periods',[]))
  if not same:
   archives.append({k:copy.deepcopy(v) for k,v in p.items() if k not in ('archived_reporting_periods','filing_history')})
  history=copy.deepcopy(p.get('filing_history',[]))
  if not same:history.append(dict(label='28-days-before-election 2026',reporting_period_label=period(dates),money_raised=new['money_raised'],money_spent=new['money_spent'],ending_cash=new['ending_cash'],net_change=new['net_change'],notes='Supplied CF-2 filing.'))
  buckets={};donors={};spend={}
  for r in new['receipt_transactions']:
   buckets[r['type']]=round(buckets.get(r['type'],0)+r['amount'],2)
   if r['type'] in ('Individual','PAC','Party') and r['donor']!=r['type']:
    key=(r['donor'],r['type']);donors[key]=round(donors.get(key,0)+r['amount'],2)
  for r in new['expenditure_transactions']:spend[r['category']]=round(spend.get(r['category'],0)+r['amount'],2)
  p.update(new);p.update(report_label='2026 28-days-before-election',reporting_period_label=period(dates),reporting_period_type='custom',latest_filing_href=href,finance_status='available',archived_reporting_periods=archives,filing_history=history,source_note='Supplied Rhode Island Board of Elections CF-2 report.',coverage_note='Cash receipts and disbursements reconcile to the CF-2 summary. In-kind contributions are separate from cash receipts.',summary_intro='Filing-period snapshot of cash receipts, spending and ending cash.',takeaways=[],explainer_cards=[],source_buckets=[dict(label=k,amount=v,description='Cash receipts in the selected filing.',class_name=k.lower()) for k,v in buckets.items()],top_donors=[dict(donor=k[0],type=k[1],amount=v,notes='Named contributor in the selected filing.') for k,v in sorted(donors.items(),key=lambda kv:-kv[1])],spending_categories=[dict(title=k,amount=v,description='Cash disbursements in the selected filing.') for k,v in sorted(spend.items(),key=lambda kv:-kv[1])])
  p['original_documents']=[d for d in p.get('original_documents',[]) if d['href']!=href]+[dict(label='28-days-before-election 2026 CF-2 report',period=period(dates),href=href,embed=True)]
  updated.append(slug);print(slug,dates,new['money_raised'],new['money_spent'],new['ending_cash'],len(new['receipt_transactions']),len(new['expenditure_transactions']))
 # Write only after every report passes reconciliation.
 for p in data['profiles']:
  if p['slug'] in updated and not any(d['slug']==p['slug'] for d in data['directory']):data['directory'].append({k:p[k] for k in ('candidate_name','slug','candidate_id','chamber','district_number','party','office_sought')}|{'has_profile':True})
 data['donor_index']=[d for d in data['donor_index'] if d['slug'] not in updated]
 for p in data['profiles']:
  if p['slug'] in updated:
   for d in p['top_donors']:data['donor_index'].append(dict(d,**{k:p[k] for k in ('candidate_id','candidate_name','chamber','district_number','party','slug')}))
 for path in ['data/candidate_finance_2026.json','candidate_finance_2026.json']:(ROOT/path).write_text(json.dumps(data,indent=2)+'\n')
 for p in data['profiles']:
  if p['slug'] not in updated:continue
  path=ROOT/'candidates'/f'{p["slug"]}.html'
  if not path.exists():continue
  esc=__import__('html').escape
  section='<section class="card" id="finance"><h2>Campaign finance snapshot</h2><p class="intro">'+esc(p['report_label']+' · '+p['reporting_period_label'])+'</p><div class="metric-grid">'+''.join(f'<div class="metric"><b>${p[k]:,.2f}</b><span>{label}</span></div>' for k,label in [('money_raised','Total receipts'),('money_spent','Spent during period'),('ending_cash','Cash at period end')])+'</div><a class="finance-profile-button" href="/finance.html?slug='+p['slug']+'">View campaign finance →</a><p class="source"><a href="'+p['latest_filing_href']+'">Open 28-days-before-election financial report (PDF) ↗</a></p><details><summary>Read the financial report on this page</summary><iframe title="'+esc(p['candidate_name'])+' campaign finance report" src="'+p['latest_filing_href']+'" loading="lazy" style="width:100%;height:640px;border:1px solid #dbe4ef;margin-top:12px"></iframe></details></section>'
  page=path.read_text();page,n=re.subn(r'<section class="card" id="finance">.*?</section>',lambda m:section,page,flags=re.S);assert n==1;path.write_text(page)
 (ROOT/'data/house-1-25-finance-import.json').write_text(json.dumps({'source':'Ajiello_district1-combined.pdf','updated_slugs':updated},indent=2)+'\n')
def period(dates):return ' to '.join(datetime.datetime.strptime(s,'%m/%d/%Y').strftime('%B %-d, %Y') for s in dates)
if __name__=='__main__':
 import sys;main(sys.argv[1])
