"""Export separate House model estimates into the website widget's data schema."""
import csv,json,math
from pathlib import Path
ROOT=Path(__file__).parent
roster={r['name']:r for r in json.loads((ROOT/'representatives.json').read_text())}
def estimates(filename,uncertainty):
 out=[]
 for r in csv.DictReader((ROOT/'results'/filename).open()):
  name=r[''];v=r['coord1D']
  if v=='NA':continue
  meta=roster[name];se=r['se1D']
  out.append(dict(name=name,district=meta['district'],party=meta['party'],position=float(v),bootstrap_standard_error=float(se) if uncertainty and se!='NA' else None,recorded_votes_used=sum(int(float(r[k])) for k in ['correctYea','wrongYea','wrongNay','correctNay']),correct_classification=float(r['CC'])))
 return sorted(out,key=lambda r:r['position'])
status=json.loads((ROOT/'results/model_status.json').read_text());sensitivity=json.loads((ROOT/'results/sensitivity.json').read_text())
periods={'combined':estimates('legislator_estimates.csv',status['native_bootstrap_success']),'2025':estimates('year_2025_estimates.csv',False),'2026':estimates('year_2026_estimates.csv',False)}
data=dict(title='Rhode Island House voting patterns',period='2025–2026',latest_journal='2026-06-11',inventory_checked='2026-10-06',status='experimental website preview',scope=json.loads((ROOT/'summary.json').read_text()),model=dict(package='wnominate',version='1.5',dimensions=1,minority_cutoff=.025,minimum_votes=20,bootstrap_trials=50,native_bootstrap_success=status['native_bootstrap_success'],positive_anchor='Michael Chippendale',higher_is_better=False,interpretation='Relative positions within the House and vote set; not an effectiveness score. Liberal/conservative labels are provisional; separately fitted House and Senate coordinates are not directly comparable.'),sensitivity=sensitivity,positions=periods['combined'],periods=periods,period_counts={'combined':status['retained_votes'],'2025':sensitivity['year_2025']['votes_used'],'2026':sensitivity['year_2026']['votes_used']})
assert len(data['positions'])==75
(ROOT/'house_voting_positions_2025_2026.json').write_text(json.dumps(data,indent=2))
(ROOT.parent.parent/'candidates/house-voting-patterns/positions.json').write_text(json.dumps(data,indent=2))
print(next(r for r in data['positions'] if r['district']==35))
