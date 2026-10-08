"""Validate the six supplied October 5 filings and new D57/58 profiles."""
import json,subprocess,re,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads((ROOT/p).read_text())
def previous(p):return json.loads(subprocess.check_output(['git','show','e7f7407:'+p],cwd=ROOT))
main=load('data/candidate_finance_2026.json');old=previous('data/candidate_finance_2026.json');mirror=load('candidate_finance_2026.json')
expected={'suzanna-l-alba':(14135,118.26,20234.84,72,1),'paul-m-santucci':(3617,5694.6,32781.17,5,12),'william-w-o-brien':(2050,4847.7,47027.27,5,34),'arthur-j-corvese':(3850,10345.46,6751.84,11,17),'brandon-t-voas':(3350,12036.8,11341.22,7,12),'cherie-l-cruz':(225,968.93,18467.61,2,7)}
cent=lambda n:round(n*100)
for p in main['profiles']:
 slug=p['slug'];prior=next(x for x in old['profiles'] if x['slug']==slug)
 if slug not in expected:assert p==prior,slug;continue
 raised,spent,end,receipts,expenses=expected[slug]
 assert p==next(x for x in mirror['profiles'] if x['slug']==slug)
 assert (p['money_raised'],p['money_spent'],p['ending_cash'])==(raised,spent,end)
 assert cent(p['beginning_cash']+raised-spent)==cent(end)
 assert cent(sum(x['amount'] for x in p['receipt_transactions']))==cent(raised)
 assert cent(sum(x['amount'] for x in p['expenditure_transactions']))==cent(spent)
 assert cent(sum(x['amount'] for x in p['source_buckets']))==cent(raised)
 assert cent(sum(x['amount'] for x in p['spending_categories']))==cent(spent)
 assert len(p['receipt_transactions'])==receipts and len(p['expenditure_transactions'])==expenses
 assert p['filing_history'][:-1]==prior['filing_history'];assert p['archived_reporting_periods'][-1]['ending_cash']==prior['ending_cash']
 assert cent(p['ending_cash']-p['total_liabilities'])==cent(p['total_fund_balance'])
 assert p['reporting_period_start']==('2026-09-02' if slug=='brandon-t-voas' else '2026-07-01');assert p['reporting_period_end']=='2026-10-05'
 pdf=ROOT/p['latest_filing_href'].lstrip('/');assert pdf.read_bytes().startswith(b'%PDF-');assert p['original_documents'][-1]['embed']
 page=(ROOT/'candidates'/f'{slug}.html').read_text();assert p['reporting_period_label'] in page;assert p['latest_filing_href'] in page;assert '<iframe' in page
 for value in [raised,spent,end]:assert f'${value:,.2f}' in page
 if slug in ['brandon-t-voas','cherie-l-cruz']:
  d=57 if slug=='brandon-t-voas' else 58
  assert 'data-voting-widget' in page and 'of 75 House district records' in page
  assert 'riep-legislative-index' in page and 'Center for Effective Lawmaking' in page and 'Session attendance' in page
  assert f'/running.html?chamber=house&amp;district={d}&amp;election=general' in page
  assert ('839 votes' in page and '61.74%' in page) if d==57 else ('985 votes' in page and '100%' in page)
  assert 'Senate District' not in page
  for route in ['ballot.html','running.html','race-page.js','index.html','candidate-profiles.html']:assert slug in (ROOT/route).read_text()
for path in ['data/candidate_finance_2026.json','candidate_finance_2026.json']:
 prior=previous(path);now=load(path)
 for key in prior.keys()-{'profiles','generated_at','donor_index','discrepancies'}:assert now[key]==prior[key],key
unchanged=lambda rows:[x for x in rows if x['slug'] not in expected]
assert unchanged(main['donor_index'])==unchanged(old['donor_index'])
assert main['discrepancies'][:-2]==old['discrepancies']
assert any(x['amount']==-1300 for x in next(p for p in main['profiles'] if p['slug']=='arthur-j-corvese')['expenditure_transactions'])
assert next(p for p in main['profiles'] if p['slug']=='paul-m-santucci')['in_kind_contributions']==282.56
assert len(next(p for p in main['profiles'] if p['slug']=='paul-m-santucci')['in_kind_transactions'])==1
print('PASS: six finance reports reconcile, history retained, unrelated records preserved, D57/58 profiles and routes correct')
