"""Full-chamber House calculation, independent of candidate-profile coverage."""
import json,html,re
from pathlib import Path
from fractions import Fraction
from datetime import date
ROOT=Path(__file__).resolve().parents[1]
KEYS=('prime_sponsored','passed_chamber','became_law')
esc=lambda v:html.escape(str(v),quote=True)

def dataset():
 data=json.loads((ROOT/'data/house_legislative_progress_2025_2026.json').read_text())
 records=data['records']
 assert data['chamber']=='house' and data['member_count']==75 and len(records)==75
 assert {r['district_number'] for r in records}==set(range(1,76))
 for r in records:
  counts=r['legislation']
  assert all(type(counts[k]) is int and counts[k]>=0 for k in KEYS)
  assert counts['became_law']<=counts['passed_chamber']<=counts['prime_sponsored']
 by_district={r['district_number']:r for r in records}
 # Ensure the calculation agrees with every published incumbent bill count.
 incumbents=json.loads((ROOT/'data/incumbent_records_2026.json').read_text())['records']
 for r in incumbents:
  if r['chamber']=='house':assert all(r['legislation'][k]==by_district[r['district_number']]['legislation'][k] for k in KEYS)
 # This historical House roster also supplies the party labels for the dot plot.
 roster=json.loads((ROOT/'candidates/house-voting-patterns/positions.json').read_text())['positions']
 assert len(roster)==75 and {r['district'] for r in roster}==set(range(1,76))
 surname=lambda s:re.sub(r'\b(jr|sr|ii|iii)\b','',re.sub('[^a-z ]','',s.lower())).split()[-1]
 for r in roster:assert surname(r['name'])==surname(by_district[r['district']]['candidate_name'])
 parties={r['district']:r['party'] for r in roster}
 totals={k:sum(r['legislation'][k] for r in records) for k in KEYS}
 assert all(totals.values())
 scores={r['district_number']:Fraction(75,3)*sum(Fraction(r['legislation'][k],totals[k]) for k in KEYS) for r in records}
 assert sum(scores.values())==75
 ranks={d:1+sum(s>value for s in scores.values()) for d,value in scores.items()}
 party_ranks={d:1+sum(scores[other]>scores[d] for other in scores if parties[other]==parties[d]) for d in scores}
 return data,by_district,parties,totals,scores,ranks,party_ranks

def house_current_index(rec):
 data,records,parties,totals,scores,ranks,party_ranks=dataset()
 d=rec['district_number'];r=records[d];s=scores[d];counts=r['legislation'];party=parties[d]
 assert all(rec['legislation'][k]==counts[k] for k in KEYS)
 n_party=sum(p==party for p in parties.values());group={'DEM':'Democrats','REP':'Republicans','IND':'Independents'}[party]
 label='Above House average' if s>1 else 'Below House average' if s<1 else 'At House average'
 stamp=date.fromisoformat(data['updated_at']).strftime('%B %d, %Y').replace(' 0',' ')
 formula=' + '.join(f'{counts[k]} ÷ {totals[k]}' for k in KEYS)
 metrics=''.join(f'<div><strong>{counts[k]}</strong><span>{title}</span></div>' for k,title in zip(KEYS,['Lead-sponsored','Passed House','Became law']))
 return f'''<section class="riep-progress" id="riep-legislative-index" aria-labelledby="riep-progress-title"><div class="lawmaker-head"><div><span class="eyebrow">Experimental RIEP calculation · 2025–2026</span><h3 id="riep-progress-title">Three-stage legislative progress index</h3></div><div class="lawmaker-score"><strong>{float(s):.2f}</strong><small>#{ranks[d]} of 75 House district records</small></div></div><p class="lawmaker-tags"><span>#{party_ranks[d]} of {n_party} House {group}</span><span>{label}</span></p><p><a class="score-comparison-link" href="current-riep-house-ranking.html#district-{d}">View entire 2025–2026 House ranking →</a></p><div class="score-context"><h4>Why RIEP publishes a current-session index</h4><p>CEL’s Legislative Effectiveness Score is our research benchmark. The CEL data presented here cover 2023–2024 and have not been extended to the 2025–2026 session. RIEP’s provisional index provides a current-session view of bill sponsorship and advancement while that historical score remains available for context.</p><p>RIEP uses three equally weighted stages and a House average of 1. It does not reproduce CEL’s five-stage method, bill-significance weights or expected-performance model. “Above” or “below House average” describes this index only; it is not a CEL expectations label.</p><a class="score-comparison-link" href="legislative-comparison.html">Compare RIEP and CEL scores for the same 2023–2024 session →</a></div><p class="intro">Lead-sponsored bills, bills passed by the House, and bills that became law, compared with all 75 House district records. A score of 1 represents the comparison-set average.</p><div class="riep-progress-metrics">{metrics}</div><details><summary>View calculation and methodology</summary><p>Each stage receives equal weight. Divide {esc(r['candidate_name'])}’s count at each stage by the corresponding House total, average the three shares, and multiply by 75. Rank uses unrounded scores; equal scores share a rank. Bills that become law contribute at each stage they reach. Cosponsored bills and resolutions are excluded.</p><p>75 ÷ 3 × ({formula}) = {float(s):.6f}.</p><p>House totals: {totals['prime_sponsored']:,} lead-sponsored bills; {totals['passed_chamber']:,} bills passed by the House; {totals['became_law']:,} bills became law.</p><p>Dataset updated: {stamp}. The complete House calculation dataset includes all 75 district records, including representatives not running in 2026. These snapshot counts are not a live legislative feed.</p><p><strong>Prototype only.</strong> This is a separate RIEP progress index, not an update to the Center for Effective Lawmaking’s score or an overall assessment of a legislator. It does not include committee-action stages or bill-significance weights. Party comparisons use the 2025–2026 House roster.</p></details><p class="source">Underlying bill records: <a href="https://status.rilegislature.gov/" target="_blank" rel="noopener">Official Rhode Island Bill Status/History ↗</a></p></section>'''
