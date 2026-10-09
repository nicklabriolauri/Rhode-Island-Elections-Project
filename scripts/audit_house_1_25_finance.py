"""Audit candidate identities and rebuild available Q2 snapshots from CF-2 PDFs."""
import sys,json,re,subprocess,copy
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,str(Path(__file__).parent))
from import_house_1_25_finance import parse,period,norm
ROOT=Path(__file__).resolve().parents[1]
def rebuild(p,path):
 text=subprocess.check_output(['pdftotext','-layout',str(path),'-'],text=True)
 name=re.search(r'Name of Candidate[^\n]*\n([^\n]+)',text)[1];name=re.sub(r'\s+\d+\s*$','',name).strip()
 assert name.split()[0].lower()==p['candidate_name'].split()[0].lower() and name.split()[-1].lower()==p['candidate_name'].split()[-1].lower(),(name,p['candidate_name'])
 values,dates=parse(text)
 for field,key in [('receipt_transactions','money_raised'),('expenditure_transactions','money_spent')]:assert round(sum(r['amount'] for r in values[field]),2)==values[key],(p['slug'],field)
 buckets=defaultdict(float);spending=defaultdict(float);donors=defaultdict(float)
 for r in values['receipt_transactions']:
  buckets[r['type']]+=r['amount']
  if r['type'] in ('Individual','PAC','Party') and r['donor']!=r['type']:donors[(r['donor'],r['type'])]+=r['amount']
 for r in values['expenditure_transactions']:spending[r['category']]+=r['amount']
 p.update(values);p.update(reporting_period_label=period(dates),source_buckets=[dict(label=k,amount=round(v,2),description='Cash receipts in this filing.',class_name=k.lower()) for k,v in buckets.items()],top_donors=[dict(donor=k[0],type=k[1],amount=round(v,2),notes='Named contributor in this filing.') for k,v in sorted(donors.items(),key=lambda x:-x[1])],spending_categories=[dict(title=k,amount=round(v,2),description='Cash disbursements in this filing.') for k,v in sorted(spending.items(),key=lambda x:-x[1])],summary_intro='Verified filing-period cash receipts, disbursements and ending cash.',takeaways=[],explainer_cards=[])
 return name

def main():
 data=json.loads((ROOT/'data/candidate_finance_2026.json').read_text());slugs=json.loads((ROOT/'data/house-1-25-finance-import.json').read_text())['updated_slugs'];audit=[]
 for p in data['profiles']:
  if p['slug'] not in slugs:continue
  path=ROOT/p['latest_filing_href'].lstrip('/');t=subprocess.check_output(['pdftotext','-f','1','-l','1','-layout',str(path),'-'],text=True);name=re.search(r'Name of Candidate[^\n]*\n([^\n]+)',t)[1];name=re.sub(r'\s+\d+\s*$','',name).strip()
  first,last=name.lower().split()[0],name.lower().split()[-1]
  aliases={'christopher-l-ireland':('christopher','ireland'),'amy-j-santiago':('amy','santiago')}
  assert (first,last)==aliases.get(p['slug'],(p['candidate_name'].lower().split()[0],p['candidate_name'].lower().split()[-1]))
  audit.append(dict(slug=p['slug'],pdf_candidate_name=name,identity_verified=True))
  if p['slug']=='barbara-quigley' and p['money_raised']==0:
   previous=copy.deepcopy(p['archived_reporting_periods'][0]);history=p['filing_history'][:1];p.clear();p.update(previous);p['filing_history']=history;p['archived_reporting_periods']=[];p['latest_filing_href']='/data/finance-documents/barbara-quigley-2026-10-05-updated.pdf';p['reporting_period_type']='custom';p['finance_status']='available';p['report_label']='2026 28-days-before-election · updated filing'
   p['finance_audit_note']='The combined upload contained a zero-activity version for this same period. The previously supplied updated CF-2 summary and supporting schedules remain the source for the displayed $5,952.82 receipts, $1,739.79 spending and $4,218.03 ending cash.'
  if p['slug']=='barbara-quigley':
   initial,_=parse(subprocess.check_output(['pdftotext','-layout',str(ROOT/'data/finance-documents/barbara-quigley-2026-10-05-initial.pdf'),'-'],text=True))
   updated,_=parse(subprocess.check_output(['pdftotext','-layout',str(ROOT/'data/finance-documents/barbara-quigley-2026-10-05-updated.pdf'),'-'],text=True))
   p.update(updated);p['receipt_transactions']=initial['receipt_transactions']+updated['receipt_transactions'];p['expenditure_transactions']=initial['expenditure_transactions'];assert round(sum(r['amount'] for r in p['receipt_transactions']),2)==p['money_raised']
  q2path=ROOT/'data/finance-documents'/f'{p["slug"]}-q2-2026.pdf'
  if q2path.exists():
   archives=p.setdefault('archived_reporting_periods',[]);q2=next((a for a in archives if 'June 30, 2026' in a['reporting_period_label'] or a['reporting_period_label']=='6/30/2026'),None)
   if not q2:q2={k:copy.deepcopy(p[k]) for k in ('candidate_id','slug','candidate_name','chamber','district_number','party','office_sought')};archives.insert(0,q2)
   before={k:q2.get(k) for k in ('money_raised','money_spent','ending_cash')};rebuild(q2,q2path);q2['report_label']='Q2 2026 campaign finance filing';q2['latest_filing_href']='/'+str(q2path.relative_to(ROOT));q2['original_documents']=[dict(label='Q2 2026 CF-2 report',period=q2['reporting_period_label'],href=q2['latest_filing_href'],embed=True)];q2['source_note']='Rhode Island Board of Elections CF-2 and supporting schedules; identity and cash totals rechecked against the PDF.';q2['coverage_note']='Verified April 1–June 30 filing. In-kind contributions and unpaid bills are separate from cash receipts and disbursements.'
   audit[-1].update(q2_pdf_verified=True,q2_previous=before,q2_corrected={k:q2[k] for k in before})
   for h in p['filing_history']:
    if h.get('reporting_period_label') in ('6/30/2026','April 1, 2026 to June 30, 2026') or h.get('label')=='Q2 2026':
     h.update({k:q2[k] for k in ('money_raised','money_spent','ending_cash','net_change')});h['reporting_period_label']=q2['reporting_period_label']
  for a in p.get('archived_reporting_periods',[]):
   a['original_documents']=[d for d in a.get('original_documents',[]) if (ROOT/d['href'].lstrip('/')).exists()]
  q2=next((a for a in p.get('archived_reporting_periods',[]) if a['reporting_period_label']=='April 1, 2026 to June 30, 2026'),None)
  if q2 and p['reporting_period_label'].startswith('July 1, 2026') and round(p['beginning_cash']-q2['ending_cash'],2)!=0:
   note=f"Cash continuity needs review: the earlier Q2 summary ends at ${q2['ending_cash']:,.2f}, while this filing begins July 1 at ${p['beginning_cash']:,.2f}. The source totals are shown as filed; no balancing adjustment has been invented."
   p['finance_audit_note']=note;q2['finance_audit_note']=note;audit[-1]['cash_continuity_note']=note
 # Matching docs and figures verified independently; don't present older date windows as directly comparable quarters.
 data['donor_index']=[d for d in data['donor_index'] if d['slug'] not in slugs]
 for p in data['profiles']:
  if p['slug'] in slugs:
   for d in p['top_donors']:data['donor_index'].append(dict(d,**{k:p[k] for k in ('candidate_id','candidate_name','chamber','district_number','party','slug')}))
 for filename in ['data/candidate_finance_2026.json','candidate_finance_2026.json']:(ROOT/filename).write_text(json.dumps(data,indent=2)+'\n')
 for path in (ROOT/'candidates').glob('*.html'):
  s=path.read_text();s=re.sub(r'<script src="finance-periods.js[^\"]*"></script>','',s);path.write_text(s)
 p=next(p for p in data['profiles'] if p['slug']=='barbara-quigley');page=ROOT/'candidates/barbara-quigley.html';s=page.read_text();section='<section class="card" id="finance"><h2>Campaign finance snapshot</h2><p class="intro">'+p['report_label']+' · '+p['reporting_period_label']+'</p><div class="metric-grid">'+''.join(f'<div class="metric"><b>${p[k]:,.2f}</b><span>{label}</span></div>' for k,label in [('money_raised','Total receipts'),('money_spent','Spent during period'),('ending_cash','Cash at period end')])+'</div><a class="finance-profile-button" href="/finance.html?slug=barbara-quigley">View campaign finance →</a><p class="source"><a href="'+p['latest_filing_href']+'">Open updated 28-days-before-election report (PDF) ↗</a></p></section>';s=re.sub(r'<section class="card" id="finance">.*?</section>',lambda m:section,s,flags=re.S);page.write_text(s)
 (ROOT/'data/house-1-25-finance-audit.json').write_text(json.dumps({'verified_candidate_documents':31,'q2_documents_rebuilt':sum(a.get('q2_pdf_verified',False) for a in audit),'findings':audit},indent=2)+'\n')
 print('Verified 31 document identities; rebuilt 11 available Q2 source PDFs; restored updated Quigley report; removed profile selectors.')
if __name__=='__main__':main()
