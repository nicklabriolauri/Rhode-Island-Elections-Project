"""Import the supplied 42 Senate filings; reconcile every schedule before writing."""
import copy, datetime, html, json, re, subprocess, sys
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from import_house_1_25_finance import parse, norm, period
from import_house_25_35_finance import enrich, verify, update_coverage, RECEIPT_LINES
ROOT=Path(__file__).resolve().parents[1]
RECEIPT_LINES.append('12. Other')
def main(source):
 source=Path(source);reader=PdfReader(source)
 pages=subprocess.check_output(['pdftotext','-layout',str(source),'-'],text=True).split('\f')
 starts=[i for i,t in enumerate(pages) if 'SUMMARY OF CAMPAIGN ACTIVITY' in t]
 assert len(starts)==42
 data=json.loads((ROOT/'data/candidate_finance_2026.json').read_text())
 aliases={'FRANK A CICCONE III':'frank-a-ciccone','V SUSAN SOSNOWSKI':'virginia-susan-sosnowski'}
 records=[]
 for j,start in enumerate(starts):
  stop=starts[j+1] if j+1<len(starts) else len(reader.pages)
  text='\f'.join(pages[start:stop]);name=re.search(r'Name of Candidate[^\n]*\n([^\n]+)',text)[1]
  name=re.sub(r'\s+\d+\s*$','',name).strip()
  if name=='BRIAN G COOGAN':
   p=dict(candidate_id='senate-14-ind-general-brian-g-coogan',slug='brian-g-coogan',candidate_name='Brian G Coogan',chamber='senate',district_number='14',party='IND',party_label='Independent',office_sought='State Senator',original_documents=[],filing_history=[])
   assert not any(x['slug']==p['slug'] for x in data['profiles'])
   data['profiles'].append(p)
   data['directory'].append({k:p[k] for k in ['candidate_id','slug','candidate_name','chamber','district_number','party','office_sought']}|{'has_profile':True})
  else:
   matches=[p for p in data['profiles'] if p['chamber']=='senate' and (p['slug']==aliases.get(name) or norm(name)==norm(p['candidate_name']) or norm(name.split()[0])==norm(p['candidate_name'].split()[0]) and norm(name.split()[-1])==norm(p['candidate_name'].split()[-1]))]
   assert len(matches)==1,(name,matches);p=matches[0]
  values,dates=parse(text);verify(text,values)
  assert dates[1]=='10/05/2026';assert (p['party_label'] in pages[start] or p['party']=='IND' and 'Unaffiliated' in pages[start]),name
  assert all(dates[0]<=r['date']<=dates[1] for field in ['receipt_transactions','expenditure_transactions'] for r in values[field]),name
  records.append(dict(profile=p,values=values,dates=dates,name=name,start=start,stop=stop))
 for r in records:
  p=r['profile'];v=r['values'];dates=r['dates'];slug=p['slug']
  if p.get('reporting_period_label'):
   previous={k:copy.deepcopy(v) for k,v in p.items() if k not in ['archived_reporting_periods','filing_history']}
   q2=ROOT/'data/finance-documents'/f'{slug}-q2-2026.pdf'
   qverified=False
   if q2.is_file():
    qt=subprocess.check_output(['pdftotext','-layout',str(q2),'-'],text=True)
    try:qv,qd=parse(qt);verify(qt,qv);qverified=True
    except AssertionError:pass
   if qverified:
    enrich(previous,qv)
    previous.update(reporting_period_label=period(qd),latest_filing_href='/'+str(q2.relative_to(ROOT)),original_documents=[dict(label='Q2 2026 CF-2 report',period=period(qd),href='/'+str(q2.relative_to(ROOT)),embed=True)])
   else:
    # Earlier donor/category summaries may be cumulative; never present them as verified Q2 detail.
    for k in ['top_donors','source_buckets','spending_categories','receipt_transactions','expenditure_transactions','in_kind_transactions','accounts_payable_transactions','takeaways','explainer_cards']:previous[k]=[]
    previous['original_documents']=[d for d in previous.get('original_documents',[]) if isinstance(d,dict) and (ROOT/d['href'].lstrip('/')).is_file() and d.get('period')==previous['reporting_period_label']]
    previous['finance_audit_note']='Previously published summary totals retained for comparison. Its period-specific donor and expense details have not been verified from a source PDF, so those details are not displayed.'
   p.setdefault('archived_reporting_periods',[]).append(previous)
  for k in ['finance_source_note','finance_snapshot_note','finance_audit_note','itemized_contribution_records','individual_contribution_records','pac_contribution_records','receipts_label']:p.pop(k,None)
  enrich(p,v)
  href=f'/data/finance-documents/{slug}-28-days-before-election-2026.pdf'
  p.update(report_label='2026 28-days-before-election',reporting_period_label=period(dates),reporting_period_type='custom',reporting_period_start=datetime.datetime.strptime(dates[0],'%m/%d/%Y').strftime('%Y-%m-%d'),reporting_period_end='2026-10-05',latest_filing_href=href,finance_status='available',source_note='Supplied Rhode Island Board of Elections CF-2 and supporting schedules; candidate identity and cash summary verified.',coverage_note='Receipts include loans, refunds, interest and other reported cash activity; returned contributions reduce net receipts. In-kind contributions and unpaid liabilities are separate from cash activity.')
  p['original_documents']=[dict(label='28 days before election 2026 CF-2 report',period=period(dates),href=href,embed=True)]
  p.setdefault('filing_history',[]).append(dict(label='28 days before election 2026',reporting_period_label=period(dates),**{k:v[k] for k in ['money_raised','money_spent','ending_cash','net_change']},notes='Supplied report; schedules reconciled to cash summary.'))
  archives=p.get('archived_reporting_periods',[])
  if archives and dates[0]=='07/01/2026' and round(archives[-1]['ending_cash']-v['beginning_cash'],2):
   p['finance_audit_note']=f'The earlier published snapshot shows ${archives[-1]["ending_cash"]:,.2f} at June 30; this report gives ${v["beginning_cash"]:,.2f} opening cash on July 1. Both source values are retained; the earlier balance needs source review.'
  writer=PdfWriter()
  for pg in reader.pages[r['start']:r['stop']]:writer.add_page(pg)
  writer.write(ROOT/href.lstrip('/'))
  path=ROOT/'candidates'/f'{slug}.html'
  if path.exists():
   esc=html.escape
   metrics=''.join(f'<div class="metric"><b>${p[k]:,.2f}</b><span>{label}</span></div>' for k,label in [('money_raised','Net cash receipts'),('money_spent','Spent during period'),('ending_cash','Cash at period end')])
   section=f'<section class="card" id="finance"><h2>Campaign finance snapshot</h2><p class="intro">{esc(p["report_label"])} · {esc(p["reporting_period_label"])}</p><div class="metric-grid">{metrics}</div><a class="finance-profile-button" href="/finance.html?slug={slug}">View campaign finance →</a><p class="source">Choose reporting periods on the campaign finance page to compare totals, donors and expenses.</p><p class="source"><a href="{href}">Open selected financial report (PDF) ↗</a></p><details><summary>Read the financial report on this page</summary><iframe title="{esc(p["candidate_name"])} campaign finance report" src="{href}" loading="lazy" style="width:100%;height:640px;border:1px solid #dbe4ef;margin-top:12px"></iframe></details></section>'
   text,n=re.subn(r'<section class="card" id="finance">.*?</section>',lambda m:section,path.read_text(),flags=re.S);assert n==1,(slug,n);path.write_text(text)
  elif slug=='brian-g-coogan':
   path=ROOT/'finance-candidates/senate-14-ind-general-brian-g-coogan.html'
   path.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=/finance.html?slug=brian-g-coogan"><title>Brian G Coogan campaign finance</title></head><body><a href="/finance.html?slug=brian-g-coogan">Open Brian G Coogan campaign finance and reporting periods</a></body></html>')
  print(slug,p['money_raised'],p['money_spent'],p['ending_cash'])
 slugs={r['profile']['slug'] for r in records}
 data['donor_index']=[x for x in data['donor_index'] if x['slug'] not in slugs]
 for r in records:
  p=r['profile']
  for donor in p['top_donors']:data['donor_index'].append(dict(donor,**{k:p[k] for k in ['candidate_id','candidate_name','chamber','district_number','party','slug']}))
 for f in ['data/candidate_finance_2026.json','candidate_finance_2026.json']:(ROOT/f).write_text(json.dumps(data,indent=2)+'\n')
 (ROOT/'data/senate-october-finance-import.json').write_text(json.dumps(dict(source=source.name,report_count=42,source_pages=len(reader.pages),findings=[dict(slug=r['profile']['slug'],candidate_name=r['profile']['candidate_name'],pdf_candidate_name=r['name'],start_page=r['start']+1,end_page=r['stop'],period=period(r['dates']),identity_verified=True,schedules_reconciled=True,**{k:r['values'][k] for k in ['beginning_cash','money_raised','money_spent','ending_cash','in_kind_contributions']}) for r in records]),indent=2)+'\n')
 update_coverage([r['profile'] for r in records])
if __name__=='__main__':main(sys.argv[1])
