"""Generate historical-baseline race ratings, with auditable vote-margin cutoffs."""
import json
from html import escape as esc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
THRESHOLDS=[(2,'Toss Up'),(5,'Tilt'),(10,'Lean'),(15,'Likely'),(float('inf'),'Solid')]
WATCH={('house',n) for n in (15,39,41,42,44,53)}|{('senate',17),('senate',34)}
def category(margin):
    return next(label for cutoff,label in THRESHOLDS if abs(margin)<cutoff)
def number(value):return int(str(value).replace(',',''))
def build():
    history=json.loads((ROOT/'data/race_data.json').read_text());roster=json.loads((ROOT/'data/whos_running_2026.json').read_text());rows=[]
    for chamber,districts in roster['chambers'].items():
        for district,record in districts.items():
            active={c['name']:c for c in record.get('candidates',[])+record.get('general_candidates',[]) if c.get('election_status')=='general_candidate' or (c.get('on_election_ballot') and c.get('election_status') not in ('lost_primary','withdrawn','removed'))}
            candidates=list(active.values());race=history.get(f'{chamber}|2024|{district}',{});named=sorted([c for c in race.get('candidates',[]) if 'write' not in c['name'].lower()],key=lambda c:number(c['votes']),reverse=True)
            row=dict(chamber=chamber,district=int(district),candidates=[dict(name=c['name'],party=c['party']) for c in candidates],watch=(chamber,int(district)) in WATCH,source_year=2024,source_url='/data/race_data.json',race_url=f'/races/{chamber}-{district}.html',rating=None,status='No comparable baseline',margin_pp=None,leading_party=None,notes=[])
            if len(named)==2 and not race.get('is_uncontested'):
                total=sum(number(c['votes']) for c in named)
                if total>0:
                    row.update(margin_pp=100*(number(named[0]['votes'])-number(named[1]['votes']))/total,leading_party=named[0]['party'],baseline_candidates=[dict(name=c['name'],party=c['party'],votes=number(c['votes'])) for c in named])
            if len(candidates)<2:row['status']='Unopposed' if len(candidates)==1 else 'No active candidate'
            elif row['margin_pp'] is None:row['notes'].append('The 2024 race was unopposed or lacks a comparable two-candidate result. An unopposed vote share is not a competitiveness estimate.')
            elif row['margin_pp']>20:row['status']='Outside 20-point window'
            elif len({c['party'] for c in named})!=2 or not {c['party'] for c in named}.issubset({c['party'] for c in candidates}):row['notes'].append('The historical party matchup cannot be transferred to the current field.')
            else:
                row['status']='Rated';row['category']=category(row['margin_pp']);abbr={'DEM':'D','REP':'R','IND':'I','OTH':'Other'}.get(row['leading_party'],row['leading_party']);row['rating']=row['category']+(' '+abbr if row['category']!='Toss Up' else '')
                if len(candidates)>2:row['notes'].append('The current race has more than two candidates. This label uses the historical two-candidate baseline; third-party vote shares and vote transfers are not estimated.')
            if chamber=='house' and int(district)==15:
                row['model_url']='/house-15-election-test.html';row['notes'].append('The existing District 15 conditional test also starts at Toss Up under its default assumptions: zero Democratic swing, zero campaign adjustment, Fung at 20%, and half of his support taken from each major party. These third-party assumptions are adjustable, not measured support.')
            row['notes'].append('Candidate changes, cash burn, endorsements and national trends are not given unvalidated numerical bonuses. This is a starting classification, not a calibrated win probability.')
            rows.append(row)
    rows.sort(key=lambda r:(r['status']!='Rated',r['margin_pp'] if r['status']=='Rated' else 1000,r['chamber'],r['district']))
    return dict(updated='2026-10-08',title='2026 legislative race ratings · baseline test',method='Carry forward the 2024 top-two named-candidate margin, excluding write-ins, when the historical party matchup remains represented in the 2026 field. Rate only current contested races with a comparable margin of 20 percentage points or less. Incumbency is already embedded in historical results; no additional incumbent bonus is applied.',thresholds=[dict(label='Toss Up',min_pp=0,max_exclusive_pp=2),dict(label='Tilt',min_pp=2,max_exclusive_pp=5),dict(label='Lean',min_pp=5,max_exclusive_pp=10),dict(label='Likely',min_pp=10,max_exclusive_pp=15),dict(label='Solid',min_pp=15,max_inclusive_pp=20)],margin_definition='Difference between the top two candidates as a share of their combined votes, in percentage points. Ratings are party-level historical baselines, not candidate polling estimates.',races=rows)

def render(data):
    rated=[r for r in data['races'] if r['status']=='Rated']; table=''
    for r in data['races']:
        party={'DEM':'dem','REP':'rep','IND':'ind'}.get(r['leading_party'],'') if r.get('category')!='Toss Up' else ''
        label=r['rating'] or r['status'];margin=f"{r['margin_pp']:.2f} pp" if r['margin_pp'] is not None else 'Unavailable'
        names='<br>'.join(esc(c['name'])+' <small>'+esc(c['party'])+'</small>' for c in r['candidates'])
        notes='<details><summary>Basis &amp; limits</summary>'+''.join('<p>'+esc(n)+'</p>' for n in r['notes'])
        if r.get('baseline_candidates'): notes+='<p><strong>2024 source votes</strong></p>'+''.join('<p>'+esc(c['name'])+' ('+esc(c['party'])+'): '+str(c['votes'])+'</p>' for c in r['baseline_candidates'])
        if r.get('model_url'):notes+='<p><a href="'+r['model_url']+'">Explore the District 15 conditional test →</a></p>'
        notes+='</details>'
        watch='<small class="watch">Your watch list</small>' if r['watch'] else ''
        table+=f'<tr data-chamber="{r["chamber"]}" data-status="{r["status"]}" data-watch="{str(r["watch"]).lower()}"><td><a href="{r["race_url"]}"><strong>{r["chamber"].title()} {r["district"]}</strong></a>{watch}</td><td>{names}</td><td><span class="rating {party}">{esc(label)}</span><small>Historical baseline</small></td><td>{margin}<small>2024 top-two vote margin</small></td><td>{notes}</td></tr>'
    body='<p>October 8, 2026 · A first set of party-level ratings for current contested House and Senate races with a comparable historical margin of <strong>20 percentage points or less</strong>. These labels carry forward the 2024 result. They are not polling estimates or calibrated win probabilities.</p><div class="metrics"><div><b>'+str(len(rated))+'</b>Races rated</div><div><b>'+str(sum(r['chamber']=='house' for r in rated))+'</b>House races</div><div><b>'+str(sum(r['chamber']=='senate' for r in rated))+'</b>Senate races</div></div><section><h2>How to read the ratings</h2><div class="legend"><span>Toss Up · under 2 pp</span><span>Tilt · 2 to under 5 pp</span><span>Lean · 5 to under 10 pp</span><span>Likely · 10 to under 15 pp</span><span>Solid · 15–20 pp</span></div><p>D = Democratic, R = Republican, I = Independent. The margin is the difference between the top two named candidates divided by their combined votes; write-ins are excluded. A vote-share swing of one point between two parties moves the margin by two points.</p><p>Unopposed races receive an “Unopposed” label. Historical unopposed results do not produce a rating, and races outside the requested window remain visible under “All races.” Current candidate changes and third-party entries limit the transferability of the baseline.</p><p>Our existing model is a District 15 conditional test. We have not estimated statewide coefficients for national trends, campaign spending, cash burn, endorsements, primaries or campaign quality. These factors remain context rather than invented numerical adjustments. Historical incumbent performance is already included; adding another incumbent bonus would double-count it.</p><p><a href="/house-15-election-test.html">District 15 conditional model →</a> · <a href="/finance.html">Campaign finance →</a></p></section><div class="filters"><label>Chamber <select id="chamber"><option value="">All</option><option value="house">House</option><option value="senate">Senate</option></select></label><label>Show <select id="scope"><option value="rated">Within 20 points · rated races</option><option value="watch">Your watch list</option><option value="all">All races</option></select></label><label>Search <input id="search" type="search" placeholder="Name, district or rating"></label></div><p id="result-count" aria-live="polite"></p><div class="table-wrap"><table id="ratings-table"><thead><tr><th>Race</th><th>2026 candidates</th><th>Rating</th><th>Baseline margin</th><th>Calculation</th></tr></thead><tbody>'+table+'</tbody></table></div>'
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>2026 Race Ratings | Rhode Island Elections Project</title><link rel="stylesheet" href="/voter-guides.css"><link rel="stylesheet" href="/race-ratings.css"><script defer src="/race-ratings.js"></script></head><body><main><nav><a href="/">RIEP home</a><a href="/running.html">Races &amp; candidates</a><a href="/candidate-profiles.html">Candidate profiles</a></nav><h1>2026 legislative race ratings</h1>'+body+'</main></body></html>\n'

if __name__=='__main__':
    data=build();(ROOT/'data/race_ratings_2026.json').write_text(json.dumps(data,indent=2)+'\n');(ROOT/'race-ratings.html').write_text(render(data))
    for r in data['races']:
        if r['status']=='Rated':print(r['chamber'],r['district'],r['rating'],round(r['margin_pp'],2))
