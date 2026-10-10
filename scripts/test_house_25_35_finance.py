"""Verify imported totals, identities, split boundaries, archives and public controls."""
import json, re, subprocess, csv
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
EXPECTED={
 'lawrence-paul-almagno-jr':(8845.42,7104.43,8993.60),
 'justine-caldwell':(230,1031.38,27282.52),
 'angela-s-coburn':(11235,7520.72,4959.28),
 'robert-e-craven-jr':(2474,1016.59,57514.39),
 'jessica-drew-day':(1125,6192.31,244.30),
 'kathleen-a-fogarty':(900,350,11271.40),
 'carol-hagan-mcentee':(3350,11339.79,75993.13),
 'george-a-nardone':(100,500,5054.95),
 'jennifer-p-nerbonne':(2946.50,860.50,4325.16),
 'earl-a-read-iii':(100,2446.41,31147.04),
 'sherry-l-roberts':(.01,2071.35,2483.87),
 'james-c-sheehan':(791.25,4082.38,204.28),
 'teresa-a-tanzi':(0,5611.60,506.35)}
data=json.loads((ROOT/'data/candidate_finance_2026.json').read_text())
assert data==json.loads((ROOT/'candidate_finance_2026.json').read_text())
before=json.loads(subprocess.check_output(['git','show','HEAD:data/candidate_finance_2026.json'],cwd=ROOT,text=True))
manifest=json.loads((ROOT/'data/house-25-35-finance-import.json').read_text())
assert len(manifest['findings'])==13
profiles={p['slug']:p for p in data['profiles']}
cent=lambda n:round(n*100)
for slug,expected in EXPECTED.items():
 p=profiles[slug]
 assert tuple(p[k] for k in ['money_raised','money_spent','ending_cash'])==expected,slug
 assert cent(p['beginning_cash']+p['money_raised']-p['money_spent'])==cent(p['ending_cash']),slug
 for rows,key in [('receipt_transactions','money_raised'),('source_buckets','money_raised'),('expenditure_transactions','money_spent'),('spending_categories','money_spent'),('in_kind_transactions','in_kind_contributions')]:
  assert cent(sum(r['amount'] for r in p[rows]))==cent(p[key]),(slug,rows)
 assert cent(p['ending_cash']-p['total_liabilities'])==cent(p['total_fund_balance'])
 page=(ROOT/'candidates'/f'{slug}.html').read_text()
 section=re.search(r'<section class="card" id="finance">.*?</section>',page,re.S)[0]
 for key in ['money_raised','money_spent','ending_cash']:assert f'${p[key]:,.2f}' in section,(slug,key)
 assert p['latest_filing_href'] in section
 assert 'finance-periods.js' not in page and 'lwv-voter-guide' not in page
 assert any(d['href']==p['latest_filing_href'] for d in p['original_documents'])
 for a in p.get('archived_reporting_periods',[]):
  for d in a.get('original_documents',[]):assert (ROOT/d['href'].lstrip('/')).is_file()
 for doc in p['original_documents']:assert (ROOT/doc['href'].lstrip('/')).is_file()
 assert p['archived_reporting_periods'],slug
for old in before['profiles']:
 if old['slug'] not in EXPECTED:assert old==profiles[old['slug']],old['slug']
almagno=profiles['lawrence-paul-almagno-jr']
assert almagno['in_kind_contributions']==752.48
assert almagno['loan_proceeds']==0 and almagno['loans_payable']==100
assert almagno['beginning_cash']==7252.61
assert '6,440.11' in almagno['finance_audit_note']
assert profiles['james-c-sheehan']['loan_proceeds']==300
assert profiles['james-c-sheehan']['refunds_rebates']==241.25
csvrows=list(csv.DictReader((ROOT/'data/finance-28-day-coverage-2026-all.csv').open()))
for r in csvrows:
 if r['finance_url'].split('slug=')[-1] in EXPECTED:assert r['status']=='Already on site' and r['document_urls']
assert 'financeFilingSelect' in (ROOT/'finance.html').read_text()
print('PASS: all 13 PDF totals, receipt/expense/in-kind breakdowns, liabilities, source links, previous snapshots, no profile selectors, coverage and unchanged other candidates')

if len(__import__('sys').argv)>1:
 source=PdfReader(__import__('sys').argv[1]);count=0
 for finding in manifest['findings']:
  p=profiles[finding['slug']];split=PdfReader(ROOT/p['latest_filing_href'].lstrip('/'))
  start,stop=finding['source_start_page']-1,finding['source_end_page']
  assert len(split.pages)==stop-start
  assert sum('SUMMARY OF CAMPAIGN ACTIVITY' in pg.extract_text() for pg in split.pages)==1
  for a,b in zip(split.pages,source.pages[start:stop]):assert a.extract_text()==b.extract_text()
  count+=len(split.pages)
 assert count==len(source.pages)==121
 print('PASS: 121 source pages preserved exactly across 13 correctly bounded candidate PDFs')
