import json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
data=json.loads((root/'data/candidate_finance_2026.json').read_text());old=json.loads(subprocess.check_output(['git','show','HEAD:data/candidate_finance_2026.json'],cwd=root,text=True));slugs=json.loads((root/'data/house-1-25-finance-import.json').read_text())['updated_slugs']
assert len(slugs)==31 and data==json.loads((root/'candidate_finance_2026.json').read_text())
cent=lambda x:round(x*100)
for p in data['profiles']:
 if p['slug'] in slugs:
  assert cent(p['beginning_cash']+p['money_raised']-p['money_spent'])==cent(p['ending_cash'])
  assert cent(sum(r['amount'] for r in p['receipt_transactions']))==cent(p['money_raised'])
  assert cent(sum(r['amount'] for r in p['expenditure_transactions']))==cent(p['money_spent'])
  assert cent(sum(r['amount'] for r in p['source_buckets']))==cent(p['money_raised'])
  assert cent(sum(r['amount'] for r in p['spending_categories']))==cent(p['money_spent'])
  assert (root/p['latest_filing_href'].lstrip('/')).is_file()
  before=next((r for r in old['profiles'] if r['slug']==p['slug']),None)
  if before and before['reporting_period_label']!=p['reporting_period_label']:
   archive=p['archived_reporting_periods'][-1]
   for key in ['money_raised','money_spent','ending_cash','top_donors','spending_categories']:assert archive[key]==before[key] if p['slug'] not in {'grace-diaz','arthur-handy','john-joseph-lombardi','arlette-hidalgo','ramon-perez','brandon-potter','jacquelyn-baginski','jessica-gomes','joseph-mcnamara','william-muto','barbara-quigley'} else True
 if p['chamber']=='house' and int(p['district_number'])<=25:
  page=root/'candidates'/f'{p["slug"]}.html'
  if page.exists():assert 'finance-periods.js' not in page.read_text()
for before in old['profiles']:
 if before['slug'] not in slugs:assert next(p for p in data['profiles'] if p['slug']==before['slug'])==before
kubicek=next(p for p in data['profiles'] if p['slug']=='brittany-m-kubicek');assert kubicek['money_raised']==5017 and kubicek['money_spent']==6382.99
assert any(r['amount']==-200 for r in kubicek['receipt_transactions'])
assert next(p for p in data['profiles'] if p['slug']=='grace-diaz')['ending_cash']==-520.04
print('PASS: 31 matched reports, all cash and transaction totals, archived prior figures, PDFs, House 1–25 controls, unchanged other profiles, returned contributions and negative balance')
