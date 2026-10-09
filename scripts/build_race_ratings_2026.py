"""Generate historical-baseline race ratings, with auditable vote-margin cutoffs."""
import json
from html import escape as esc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
THRESHOLDS=[(2,'Toss Up'),(5,'Tilt'),(10,'Lean'),(15,'Likely'),(float('inf'),'Solid')]
RATING_WINDOW_PP=30
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
            elif row['margin_pp']>RATING_WINDOW_PP:row['status']='Outside 30-point window'
            elif len({c['party'] for c in named})!=2 or not {c['party'] for c in named}.issubset({c['party'] for c in candidates}):row['notes'].append('The historical party matchup cannot be transferred to the current field.')
            else:
                row['status']='Rated';row['category']=category(row['margin_pp']);abbr={'DEM':'D','REP':'R','IND':'I','OTH':'Other'}.get(row['leading_party'],row['leading_party']);row['rating']=row['category']+(' '+abbr if row['category']!='Toss Up' else '')
                if len(candidates)>2:row['notes'].append('The current race has more than two candidates. This label uses the historical two-candidate baseline; third-party vote shares and vote transfers are not estimated.')
            if chamber=='house' and int(district)==15:
                row['model_url']='/house-15-election-test.html';row['notes'].append('The existing District 15 conditional test also starts at Toss Up under its default assumptions: zero Democratic swing, zero campaign adjustment, Fung at 20%, and half of his support taken from each major party. These third-party assumptions are adjustable, not measured support.')
            row['notes'].append('Candidate changes, cash burn, endorsements and national trends are not given unvalidated numerical bonuses. This is a starting classification, not a calibrated win probability.')
            rows.append(row)
    rows.sort(key=lambda r:(r['status']!='Rated',r['margin_pp'] if r['status']=='Rated' else 1000,r['chamber'],r['district']))
    return dict(updated='2026-10-08',title='2026 legislative race ratings · baseline test',method='Carry forward the 2024 top-two named-candidate margin, excluding write-ins, when the historical party matchup remains represented in the 2026 field. Rate only current contested races with a comparable margin of 30 percentage points or less. Incumbency is already embedded in historical results; no additional incumbent bonus is applied.',thresholds=[dict(label='Toss Up',min_pp=0,max_exclusive_pp=2),dict(label='Tilt',min_pp=2,max_exclusive_pp=5),dict(label='Lean',min_pp=5,max_exclusive_pp=10),dict(label='Likely',min_pp=10,max_exclusive_pp=15),dict(label='Solid',min_pp=15,max_inclusive_pp=RATING_WINDOW_PP)],margin_definition='Difference between the top two candidates as a share of their combined votes, in percentage points. Ratings are party-level historical baselines, not candidate polling estimates.',races=rows)

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
        midpoint=r['scenarios'][1];r['included']=r['included'] or any(x['leader_margin_pp']<=RATING_WINDOW_PP for x in r['scenarios'])
        r.update(rating=midpoint['rating'],category=midpoint['category'],leading_party=midpoint['leading_party'],status='Rated' if r['included'] else 'Outside 30-point window')
        r['notes']=[n for n in r['notes'] if not n.startswith('The existing District 15 conditional test')]
        r['notes'].insert(0,'The 6%, 7% and 8% scenarios mean percentage-point gains in Democratic vote share, not changes of that size in the D–R margin. They are user-specified scenarios, not measured forecasts.')
        if len(r['candidates'])>2:r['notes'].insert(1,'The Senate 17 scenarios shift the major-party baseline only; shares for the two independent candidates are unknown.' if r['chamber']=='senate' else f"Fung remains at {defaults['fung_share_pct']}% with {defaults['fung_from_republican_pct']}% of his support taken from Republicans, matching the existing conditional test. These are assumptions, not polling estimates.")
    data.update(title='28 Days Before Elections Ratings',publication_status='Preliminary',final_ratings_notice='Final ratings will be published before Election Day.',default_dem_vote_share_swing_pp=7,scenario_swings_pp=[6,7,8],method='Apply user-assumed Democratic vote-share gains of 6, 7 and 8 percentage points to comparable contested 2024 D–R baselines. Each gain shifts the two-party margin by twice that amount. Include comparable races within 30 points in 2024 or in any selected swing scenario. The main rating uses the 7-point midpoint. Do not apply the D–R shift to independent-versus-Democratic matchups.',thresholds=[dict(label='Toss Up',min_pp=0,max_exclusive_pp=2),dict(label='Tilt',min_pp=2,max_exclusive_pp=5),dict(label='Lean',min_pp=5,max_exclusive_pp=10),dict(label='Likely',min_pp=10,max_exclusive_pp=15),dict(label='Solid',min_pp=15)],margin_definition='Scenario leader’s gap over the runner-up in percentage points. For two-party races this is the D–R margin; for District 15 it includes the assumed Fung share. The historical margin excludes write-ins.')
    overrides={('house',15):'Lean D',('senate',34):'Toss Up'}
    for r in data['races']:
        r['race_url']=f'/running.html?chamber={r["chamber"]}&district={r["district"]}&election=general'
        r['model_rating']=r['rating']
        if (r['chamber'],r['district']) in overrides:
            r['rating']=overrides[r['chamber'],r['district']]
            r['category']='Toss Up' if r['rating']=='Toss Up' else 'Lean'
            r['leading_party']=None if r['rating']=='Toss Up' else 'DEM'
            r['editorial_override']=True
            r['notes'].insert(0,'Published editorial rating selected by RIEP; underlying model calculations are retained separately.')
        r['projected_flip']=bool(r['included'] and r['rating'] and r['rating']!='Toss Up' and r['leading_party']!=r['baseline_leading_party'])
    history=json.loads((ROOT/'data/race_data.json').read_text())
    for r in data['races']:
        r['within_competitive_window']=r['included']
        if r['included'] and r['rating']:
            continue
        parties={c['party'] for c in r['candidates']}
        prior=sorted([c for c in history.get(f'{r["chamber"]}|2024|{r["district"]}',{}).get('candidates',[]) if 'write' not in c['name'].lower()],key=lambda c:number(c['votes']),reverse=True)
        party=next(iter(parties)) if len(parties)==1 else (prior[0]['party'] if prior and prior[0]['party'] in parties else 'DEM' if 'DEM' in parties else 'REP')
        r.update(rating='Safe '+{'DEM':'D','REP':'R','IND':'Independent'}.get(party,party),category='Safe',leading_party=party,included=True,status='Rated',projected_flip=False,coverage_classification=True)
        r['notes'].insert(0,'RIEP editorial safe-seat classification based on the current field and historical winning party; this is not a modeled vote margin or win probability.')
    data['publication_status']='Preliminary prediction'
    data['prediction_dem_vote_share_swing_pp']=7
    data['races'].sort(key=lambda r:(not r['included'],r['scenarios'][1]['leader_margin_pp'] if r['scenarios'] else 999,r['chamber'],r['district']))
    return data

def render(data):
    def surname(name):
        parts=name.split()
        while len(parts)>1 and parts[-1].rstrip('.').lower() in {'jr','sr','ii','iii','iv'}:
            parts.pop()
        return parts[-1]
    labels=['Solid D','Likely D','Lean D','Tilt D','Toss Up','Tilt R','Lean R','Likely R','Solid R']
    boards=''
    for swing in [7]:
        for chamber in ['house','senate']:
            rows=[r for r in data['races'] if r['included'] and r['chamber']==chamber and r['category']!='Safe']
            columns=[]
            for label_text in labels:
                matches=sorted([r for r in rows if r['rating']==label_text],key=lambda r:r['district'])
                cls=label_text.lower().replace(' ','-');items=''
                for r in matches:
                    names=' / '.join(surname(c['name']) for c in r['candidates']);prefix='HD' if chamber=='house' else 'SD'
                    flip=' <em class="flip-label">(Flip)</em>' if r['projected_flip'] else ''
                    items+=f'<li><a href="{r["race_url"]}" aria-label="{chamber.title()} District {r["district"]}: {esc(names)}"><strong>{prefix} {r["district"]}{flip}</strong><span>{esc(names)}</span></a></li>'
                count_label='race' if len(matches)==1 else 'races'
                columns.append((f'<th scope="col" class="{cls}">{label_text}<small>{len(matches)} {count_label}</small></th>',f'<td><ul>{items}</ul></td>'))
            boards+=f'<section class="ratings-board" data-swing="{swing}" data-chamber="{chamber}"'+(' hidden' if swing!=7 else '')+f'><h2>State {chamber.title()}</h2><div class="board-scroll"><table aria-label="Published {chamber.title()} predictions"><thead><tr>'+''.join(c[0] for c in columns)+'</tr></thead><tbody><tr>'+''.join(c[1] for c in columns)+'</tr></tbody></table></div></section>'
    safe_boards=''
    for chamber in ['house','senate']:
        groups=''
        for safe_rating in ['Safe D','Safe R','Safe Independent']:
            rows=sorted([r for r in data['races'] if r['chamber']==chamber and r['rating']==safe_rating],key=lambda r:r['district'])
            if not rows:continue
            cls=safe_rating.lower().replace(' ','-')
            items=''.join(f'<li><a href="{r["race_url"]}"><strong>{"HD" if chamber=="house" else "SD"} {r["district"]}</strong><span>{esc(" / ".join(surname(c["name"]) for c in r["candidates"]))}</span></a></li>' for r in rows)
            groups+=f'<section class="safe-group {cls}"><h3>{safe_rating} <small>{len(rows)} seats</small></h3><ul>{items}</ul></section>'
        safe_boards+=f'<section class="ratings-board safe-board" data-chamber="{chamber}"><h2>State {chamber.title()} · Safe seats</h2><div class="safe-groups">{groups}</div></section>'
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>28 Days Before Elections Ratings | RIEP</title><link rel="stylesheet" href="/race-ratings.css"><script defer src="/race-ratings.js"></script></head><body><header><nav><a class="brand" href="/">Rhode Island Elections Project</a><a href="/running.html">Races &amp; candidates</a><a href="/index.html#homeSearchSection">Who’s on my ballot?</a><a href="/candidate-profiles.html">Candidate profiles</a></nav></header><main><h1>28 Days Before Elections Ratings</h1><p class="edition">October 8, 2026 · Published preliminary predictions</p><p class="publication-note">Final ratings will be published before Election Day.</p><div class="controls"><label>Chamber <select id="chamber"><option value="">House &amp; Senate</option><option value="house">House</option><option value="senate">Senate</option></select></label></div><p class="assumption">Our published preliminary predictions. <b>(Flip)</b> indicates a projected change from the party that won in 2024. Select a district to view the race.</p>'+boards+safe_boards+'<details class="method"><summary>Prediction methodology</summary><p>These fixed preliminary predictions start with contested 2024 results and use an assumed 7-percentage-point increase in Democratic vote share, equivalent to a 14-point shift in a two-party margin. This assumption is the basis of this edition; visitors cannot adjust the published ratings. The model has not been calibrated to win probabilities and does not use district polling. Published ratings also include RIEP editorial decisions: House 15 is Lean D and Senate 34 is Toss Up. These decisions override the model label without changing its underlying arithmetic.</p><p>Rating cutoffs use the leader’s margin: Toss Up under 2 points; Tilt 2–under 5; Lean 5–under 10; Likely 10–under 15; Solid 15 or more. Contested races within 30 points for either party in 2024 remain included; races entering that window under a swing scenario are added. Other seats are listed separately as Safe D, Safe R, or Safe Independent. These are editorial classifications based on the current field and historical winning party, including unopposed seats and races without comparable contested results; no numerical margin is inferred for them.</p><p>House 15 holds Fung at an assumed 20%, drawing equally from both major parties. Senate 17 shifts the major-party baseline only; support for its independent candidates is unknown. Senate 19 is a Democratic-versus-independent race, so no automatic D–R swing adjustment is applied. Campaign finance and candidate characteristics remain context rather than separately estimated adjustments.</p></details></main><footer>Rhode Island Elections Project · Independent election information</footer></body></html>\n'

if __name__=='__main__':
    data=build();(ROOT/'data/race_ratings_2026.json').write_text(json.dumps(data,indent=2)+'\n');(ROOT/'race-ratings.html').write_text(render(data))
    for r in data['races']:
        if r['status']=='Rated' and r.get('category')!='Safe':print(r['chamber'],r['district'],r['rating'],round(r['margin_pp'],2) if r['margin_pp'] is not None else 'Editorial')
