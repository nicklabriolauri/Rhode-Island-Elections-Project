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
def build_baseline():
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

def label(margin):
    group=category(margin)
    return group if group=='Toss Up' else group+(' D' if margin>0 else ' R')
def build():
    data=build_baseline();defaults=json.loads((ROOT/'data/house_15_forecast_test_2026.json').read_text())['defaults']
    for r in data['races']:
        r['baseline_status']=r['status'];r['baseline_rating']=r['rating'];r['baseline_leading_party']=r['leading_party'];r['scenarios']=[];r['included']=r['status']=='Rated'
        parties={c['party'] for c in r.get('baseline_candidates',[])};current={c['party'] for c in r['candidates']}
        eligible=len(r['candidates'])>=2 and parties=={'DEM','REP'} and parties.issubset(current)
        if not eligible:
            if r['status']=='Rated':r['status']='Not modeled';r['rating']=None;r['notes'].insert(0,'The uniform Democratic-versus-Republican swing is not applied to this Democratic-versus-Independent race. Its historical baseline remains visible.')
            continue
        signed=r['margin_pp']*(1 if r['baseline_leading_party']=='DEM' else -1);r['baseline_dem_margin_pp']=signed;r['baseline_rating']=label(signed)
        for swing in [6,7,8]:
            dem=max(0,min(100,50+signed/2+swing));rep=100-dem;shares={'DEM':dem,'REP':rep};model='Uniform two-party swing'
            if r['chamber']=='house' and r['district']==15:
                fung=defaults['fung_share_pct'];from_r=defaults['fung_from_republican_pct']/100
                take_d=max(max(0,fung-rep),min(min(dem,fung),fung*(1-from_r)));shares={'DEM':dem-take_d,'REP':rep-(fung-take_d),'IND':fung};model='District 15 conditional three-candidate split'
            order=sorted(shares.items(),key=lambda x:x[1],reverse=True);gap=order[0][1]-order[1][1];leader=order[0][0];group=category(gap)
            rating=group if group=='Toss Up' else group+' '+{'DEM':'D','REP':'R','IND':'I'}[leader]
            r['scenarios'].append(dict(dem_vote_share_swing_pp=swing,dem_rep_margin_pp=shares['DEM']-shares['REP'],leader_margin_pp=gap,leading_party=leader,rating=rating,category=group,conditional_shares_pct=shares,method=model))
        midpoint=r['scenarios'][1];r['included']=r['included'] or any(x['leader_margin_pp']<=20 for x in r['scenarios'])
        r.update(rating=midpoint['rating'],category=midpoint['category'],leading_party=midpoint['leading_party'],status='Rated' if r['included'] else 'Outside 20-point window')
        r['notes']=[n for n in r['notes'] if not n.startswith('The existing District 15 conditional test')]
        r['notes'].insert(0,'The 6%, 7% and 8% scenarios mean percentage-point gains in Democratic vote share, not changes of that size in the D–R margin. They are user-specified scenarios, not measured forecasts.')
        if len(r['candidates'])>2:r['notes'].insert(1,'The Senate 17 scenarios shift the major-party baseline only; shares for the two independent candidates are unknown.' if r['chamber']=='senate' else f"Fung remains at {defaults['fung_share_pct']}% with {defaults['fung_from_republican_pct']}% of his support taken from Republicans, matching the existing conditional test. These are assumptions, not polling estimates.")
    data.update(title='2026 legislative race ratings · Democratic swing scenarios',default_dem_vote_share_swing_pp=7,scenario_swings_pp=[6,7,8],method='Apply user-assumed Democratic vote-share gains of 6, 7 and 8 percentage points to comparable contested 2024 D–R baselines. Each gain shifts the two-party margin by twice that amount. Keep previously rated races and add races entering the 20-point window in either scenario. The main rating uses the 7-point midpoint. Do not apply the D–R shift to independent-versus-Democratic matchups.',thresholds=[dict(label='Toss Up',min_pp=0,max_exclusive_pp=2),dict(label='Tilt',min_pp=2,max_exclusive_pp=5),dict(label='Lean',min_pp=5,max_exclusive_pp=10),dict(label='Likely',min_pp=10,max_exclusive_pp=15),dict(label='Solid',min_pp=15)],margin_definition='Scenario leader’s gap over the runner-up in percentage points. For two-party races this is the D–R margin; for District 15 it includes the assumed Fung share. The historical margin excludes write-ins.')
    data['races'].sort(key=lambda r:(not r['included'],r['scenarios'][1]['leader_margin_pp'] if r['scenarios'] else 999,r['chamber'],r['district']))
    return data

def render(data):
    table='';rated=[r for r in data['races'] if r['included'] and r['scenarios']]
    for r in data['races']:
        names='<br>'.join(esc(c['name'])+' <small>'+esc(c['party'])+'</small>' for c in r['candidates']);watch='<small class="watch">Your watch list</small>' if r['watch'] else ''
        baseline=esc(r['baseline_rating'] or r['baseline_status'])
        if r['margin_pp'] is not None:baseline+=f'<small>{r["baseline_leading_party"]} +{r["margin_pp"]:.2f} pp in 2024</small>'
        cells=''
        for swing in [6,7,8]:
            scenario=next((x for x in r['scenarios'] if x['dem_vote_share_swing_pp']==swing),None)
            if scenario:
                cls={'DEM':'dem','REP':'rep','IND':'ind'}[scenario['leading_party']] if scenario['category']!='Toss Up' else ''
                cells+=f'<td><span class="rating {cls}">{scenario["rating"]}</span><small>{scenario["leading_party"]} +{scenario["leader_margin_pp"]:.2f} pp</small></td>'
            else:cells+='<td>'+esc(r['status'])+'</td>'
        notes='<details><summary>Assumptions &amp; source votes</summary>'+''.join('<p>'+esc(n)+'</p>' for n in r['notes'])
        for c in r.get('baseline_candidates',[]):notes+='<p>2024: '+esc(c['name'])+' ('+esc(c['party'])+'): '+str(c['votes'])+' votes</p>'
        if r.get('model_url'):notes+='<a href="'+r['model_url']+'">District 15 conditional test →</a>'
        notes+='</details>'
        table+=f'<tr data-chamber="{r["chamber"]}" data-status="{r["status"]}" data-included="{str(r["included"]).lower()}" data-watch="{str(r["watch"]).lower()}"><td><a href="{r["race_url"]}"><strong>{r["chamber"].title()} {r["district"]}</strong></a>{watch}</td><td>{names}</td><td>{baseline}</td>{cells}<td>{notes}</td></tr>'
    body='<p>October 8, 2026 · Revised under an assumed <strong>6–8 percentage-point Democratic vote-share swing</strong>. This is a scenario test, not a measured national trend or calibrated election forecast.</p><div class="metrics"><div><b>'+str(len(rated))+'</b>Races with swing scenarios</div><div><b>+7 pp</b>Midpoint used on race pages</div><div><b>+12–16 pp</b>Change in two-party D–R margin</div></div><section><h2>What changed</h2><p>A Democratic share increasing from 45% to 51% is a six-point swing. The Republican share falls from 55% to 49%, so the margin moves from R +10 to D +2: a twelve-point change. If you meant a six-to-eight-point change in the margin itself, the corresponding vote-share swing would be only three to four points.</p><div class="legend"><span>Toss Up · under 2 pp</span><span>Tilt · 2 to under 5 pp</span><span>Lean · 5 to under 10 pp</span><span>Likely · 10 to under 15 pp</span><span>Solid · 15+ pp</span></div><p>We retain previously rated races and add races entering the 20-point window under either scenario. Races that become safer remain listed as Solid. House 41 now enters the window. Unopposed or historically unopposed races still have no contest-based swing rating.</p><p>District 15 uses its existing conditional third-party split: Fung at 20%, drawing equally from each major party. Senate 17 uses the D–R baseline only; its two independent candidates’ support is unknown. Senate 19 is a D–Independent contest, so it receives no automatic D–R swing adjustment.</p><p>The swing is an explicit assumption. Campaign finance, burn rate, endorsements and candidate quality are not given new numerical weights, and national swing may not reach every district equally.</p></section><div class="filters"><label>Chamber <select id="chamber"><option value="">All</option><option value="house">House</option><option value="senate">Senate</option></select></label><label>Show <select id="scope"><option value="rated">Previous ratings + newly competitive</option><option value="watch">Your watch list</option><option value="all">All races</option></select></label><label>Search <input id="search" type="search" placeholder="Name, district or rating"></label></div><p id="result-count" aria-live="polite"></p><div class="table-wrap"><table id="ratings-table"><thead><tr><th>Race</th><th>Candidates</th><th>2024 baseline</th><th>+6 pp D</th><th>+7 pp D · midpoint</th><th>+8 pp D</th><th>Calculation</th></tr></thead><tbody>'+table+'</tbody></table></div>'
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>2026 Race Ratings | Rhode Island Elections Project</title><link rel="stylesheet" href="/voter-guides.css"><link rel="stylesheet" href="/race-ratings.css"><script defer src="/race-ratings.js"></script></head><body><main><nav><a href="/">RIEP home</a><a href="/running.html">Races &amp; candidates</a><a href="/candidate-profiles.html">Candidate profiles</a></nav><h1>2026 race ratings · Democratic swing scenarios</h1>'+body+'</main></body></html>\n'

if __name__=='__main__':
    data=build();(ROOT/'data/race_ratings_2026.json').write_text(json.dumps(data,indent=2)+'\n');(ROOT/'race-ratings.html').write_text(render(data))
    for r in data['races']:
        if r['status']=='Rated':print(r['chamber'],r['district'],r['rating'],round(r['margin_pp'],2))
