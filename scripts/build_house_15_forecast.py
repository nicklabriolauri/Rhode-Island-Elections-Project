"""Build an auditable conditional D15 scenario baseline; no fitted third-party forecast."""
import json,math,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
races=json.loads((ROOT/'data/race_data.json').read_text())
def votes(c):return int(str(c['votes']).replace(',',''))
def eligible(r):
 c=r['candidates'];named=[x for x in c if 'write' not in x['name'].lower()]
 if r['chamber']!='House' or r['is_uncontested'] or len(named)!=2 or {x['party'] for x in named}!={'DEM','REP'}:return None
 total=int(str(r['district_total_votes']).replace(',',''));allvotes=sum(votes(x) for x in c);namedvotes=sum(votes(x) for x in named)
 if total not in (allvotes,namedvotes):return None
 return sum(votes(x) for x in named if x['party']=='DEM')/namedvotes
valid={(r['year'],r['district_number']):eligible(r) for r in races.values() if eligible(r) is not None}
pairs=[]
for before,after in [(2012,2014),(2014,2016),(2016,2018),(2018,2020),(2022,2024)]:
 for district in range(1,76):
  if (before,district) in valid and (after,district) in valid:pairs.append(dict(before=before,after=after,district=district,change_pp=100*(valid[(after,district)]-valid[(before,district)])))
training=[x for x in pairs if x['after']<=2020];holdout=[x for x in pairs if x['after']==2024];errors=[x['change_pp'] for x in training];mean=statistics.mean(errors);centered=[x-mean for x in errors]
def metrics(rows):
 errors=[x['change_pp'] for x in rows]
 return dict(n=len(errors),mae_pp=statistics.mean(abs(x) for x in errors),rmse_pp=math.sqrt(statistics.mean(x*x for x in errors)),mean_error_pp=statistics.mean(errors)) if errors else dict(n=0)
history=[]
for year in range(2012,2026,2):
 r=races[f'house|{year}|15'];named=[x for x in r['candidates'] if 'write' not in x['name'].lower()];history.append(dict(year=year,uncontested=r['is_uncontested'],winner=r['winner_candidate'],party=r['winner_party'],candidates=[dict(name=x['name'],party=x['party'],votes=votes(x)) for x in named],two_party_dem_share=eligible(r),note='Excluded from baseline: uncontested.' if r['is_uncontested'] else 'Historical boundaries before 2022; context only.' if year<2022 else 'Current-boundary baseline.' if year==2024 else 'Context only.'))
model=dict(updated='2026-10-08',as_of='2026-10-05',district=15,title='District 15 conditional election test',baseline=dict(year=2024,dem_share=valid[(2024,15)],dem_votes=4319,rep_votes=4341,total_major_party_votes=8660,margin_votes=22,source='/data/race_data.json',method='Carry forward the 2024 Democratic share of Democratic + Republican votes, before any scenario adjustments. Incumbent performance is already embedded; no additional incumbent bonus is applied.'),defaults=dict(dem_swing_pp=0,campaign_adjustment_pp=0,fung_share_pct=20,fung_from_republican_pct=50,fung_uncertainty_pp=10),uncertainty=dict(method='Resample centered changes in Democratic two-party vote share among eligible adjacent-cycle contested House races through 2020. Perturb assumed Fung support with a uniform ±10-point range by default; that range is a user-adjustable assumption, not an estimate.',historical_errors_pp=centered,training=metrics(training),holdout_2024=metrics(holdout),pairs=pairs,excluded_boundary_transition='2020 to 2022 excluded because district boundaries changed.',limitations='These checks validate a simple two-party persistence baseline, not the three-candidate model or candidate win probabilities. A sample drawn from contested races is selective. Earlier boundary regimes and candidate changes limit transferability.'),history=history,missing_inputs=['No D15 horse-race poll in the model.','No presidential or statewide results reaggregated to current D15 boundaries in the repository.','No measured district-level support or vote-source split for Fung.','No historically estimated finance-to-vote coefficient.','No verified numerical national swing input; default is zero.'],candidate_context=[dict(name='Christopher G Paplauskas',party='REP',note='Republican incumbent; 2024 D15 result is the baseline.'),dict(name='Colleen M Crudele',party='DEM',note='Democratic challenger; 2024 baseline belongs to Maria Bucci, not Crudele.'),dict(name='Allan W Fung',party='IND',note='Independent challenger. Repository biography records prior service as mayor of Cranston. No personal vote bonus is estimated from that biography.')],finance_source='/data/house_15_finance_model_2026.json',simulation_count=10000,seed=1502026)
(ROOT/'data/house_15_forecast_test_2026.json').write_text(json.dumps(model,indent=2)+'\n')
print('Training:',model['uncertainty']['training'],'Holdout:',model['uncertainty']['holdout_2024'])
