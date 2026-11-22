"""Static Cranston sponsorship presentation from extracted public records.

Run python scripts/cranston_sponsorship.py. No third-party dependencies.
Counts are observed member-item credits, not introductions or effectiveness.
"""
from pathlib import Path
from html import escape as e
import csv, hashlib, io, json, re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'data/cranston/sponsorship-2026.json'
CATEGORIES = {'ordinance':'Ordinances', 'position':'Policy-position resolutions',
              'symbolic':'Symbolic display policy', 'recognition':'Recognition and commemoration'}
ROLE_LABELS = {'sponsor':'Named sponsor / joint sponsor','cosponsor':'Explicit cosponsor'}

def normalize(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip()

def attribution(title, members):
    m = re.search(r'(?<![\w-])Sponsored by\s+', title, re.I)
    if not m: return [], [], ''
    chunks = re.split(r'Co[- ]Sponsored by\s+', title[m.end():], maxsplit=1, flags=re.I)
    stop = r'(?:\s+[–—]\s+|\s+[-–]\s+as\b|\s*\(|;|\.\s+(?:A representative|To Be|Council|It was|Several))'
    primary = re.split(stop,chunks[0],maxsplit=1,flags=re.I)[0]
    co = re.split(stop,chunks[1],maxsplit=1,flags=re.I)[0] if len(chunks)>1 else ''
    def names(clause):
        clause=re.sub('Bu0onanno','Buonanno',clause,flags=re.I)
        return [m['id'] for m in members if re.search(r'\b'+re.escape(m['surname'])+r'\b',clause,re.I)]
    return names(primary), names(co), primary+('; Co-sponsored by '+co if co else '')

def category(title):
    if re.search(r'\b(honoring|in memory|commemorat\w*|celebrat\w*|proclaim\w*|recogniz\w*)\b',title,re.I):return 'recognition'
    if 'flying and display' in title.lower():return 'symbolic'
    return 'position' if title.lower().lstrip(' •').startswith('resolution') else 'ordinance'

def build():
    d=json.loads((ROOT/'data/cranston/records-2026/records.json').read_text())
    review=json.loads((ROOT/'data/cranston/sponsorship-review.json').read_text())
    registry=json.loads((ROOT/'data/local_representatives.json').read_text())
    profiles={p['slug']:p for p in registry['profiles']}
    members=d['members']; byname={m['surname']:m['id'] for m in members}
    resolutions={mid:r for r in d['resolutions'] for mid in r['motion_ids']}
    proposals={}; motion_keys={}
    for motion in d['motions']:
        title=normalize(motion['title']); primary, co, clause=attribution(title,members)
        if not clause:continue
        num=re.match(r'^[ •]*(\d{1,2})-(\d{1,2})-(\d{2}[A-Za-z]?)\b',title)
        resolution=resolutions.get(motion['id'])
        if num:key='ordinance-'+f'{int(num[1]):02}-{int(num[2]):02}-{num[3].upper()}'
        elif resolution:key='resolution-'+resolution['number']
        else:
            base=re.split('Sponsored by',title,flags=re.I)[0]
            key='title-'+hashlib.sha256(re.sub(r'\W+','',base.lower()).encode()).hexdigest()[:12]
        short=re.split('Sponsored by',title,maxsplit=1,flags=re.I)[0].strip(' ;.')
        p=proposals.setdefault(key,{'id':key,'title':short,'category':category(title),'sponsors':[], 'cosponsors':[], 'observations':[], 'adopted_text':resolution['source_url'] if resolution else None,
            'carryover':bool(num and num[2]=='25')})
        p['sponsors']=sorted(set(p['sponsors'])|set(primary))
        p['cosponsors']=sorted(set(p['cosponsors'])|set(co))
        p['observations'].append({'motion_id':motion['id'],'date':motion['date'],'action':motion['action'],'source_url':motion['source_url'],'source_page':motion['source_page'],'minutes_status':motion.get('minutes_status',''),'attribution':clause})
        motion_keys[motion['id']]=key
    motion_by_id={m['id']:m for m in d['motions']}
    for addition in review['additions']:
        mid=addition['motion_id']
        if mid not in motion_by_id:raise ValueError('Missing reviewed motion: '+mid)
        key=addition.get('proposal_id') or motion_keys[mid]
        p=proposals[key]
        p['cosponsors']=sorted(set(p['cosponsors'])|{byname[n] for n in addition['surnames']})
        m=motion_by_id[mid]
        p.setdefault('cosponsor_evidence',[]).append({'motion_id':mid,'date':m['date'],'context':m['title'],'excerpt':m['source_excerpt'],'source_url':m['source_url'],'source_page':m['source_page']})
    for p in proposals.values():
        p['cosponsors']=sorted(set(p['cosponsors'])-set(p['sponsors']))
        p['observations'].sort(key=lambda x:(x['date'],x['motion_id']))
    for m in members:
        ps=[p for p in proposals.values() if m['id'] in p['sponsors']]
        co=[p for p in proposals.values() if m['id'] in p['cosponsors']]
        m['counts']={'sponsor':len(ps),'cosponsor':len(co),**{k:sum(p['category']==k for p in ps) for k in CATEGORIES}}
        m['profile_url']='/candidates/'+m['id']+'.html#sponsorship' if m['id'] in profiles else None
    data={'schema_version':1,'year':2026,'reviewed':review['reviewed'],'records_retrieved':d['retrieved_at'],'source_dataset':'/data/cranston/records-2026/records.json','coverage':'Minimum observed sponsorships in extracted full-council records. Incomplete attribution; no productivity ranking or effectiveness score.', 'meeting_count':len(d['meetings']),'motion_count':len(d['motions']),'members':members,'proposals':list(proposals.values())}
    DATA.write_text(json.dumps(data,indent=2)+'\n')
    output=io.StringIO();wr=csv.writer(output);wr.writerow(['Member','2026 office','Proposal ID','Role','Category','Title','Observed dates','Source URLs'])
    for p in data['proposals']:
        for role,key in [('sponsor','sponsors'),('cosponsor','cosponsors')]:
            for mid in p[key]:
                m=next(m for m in members if m['id']==mid)
                wr.writerow([m['name'],m['office_2026'],p['id'],ROLE_LABELS[role],CATEGORIES[p['category']],p['title'],'; '.join(o['date'] for o in p['observations']),'; '.join(sorted({o['source_url'] for o in p['observations']}))])
    (ROOT/'data/cranston/sponsorship-2026.csv').write_text(output.getvalue())
    (ROOT/'cranston-sponsorship.html').write_text(overview(data))
    return data

def method():
    return '''<details class="sponsorship-method"><summary>How sponsorship is counted</summary><p>Each identified measure counts once per member, even when it appears at several meetings. Members explicitly listed together as sponsors receive joint sponsor credit; the first-listed name is not assumed to be the lead author. Explicit cosponsors are shown separately. Moving, seconding or voting for a motion does not establish sponsorship.</p><p>Recognition and commemorative items are separated from ordinances, policy-position resolutions and symbolic display policy. These categories describe the activity; they are not significance weights. Items first introduced in an earlier year can appear here when considered in 2026. Counts are not the number of bills introduced in 2026.</p><p>This pilot uses sponsorship clauses in the extracted records, plus a small set of checked cosponsor additions. Some source minutes contain sponsorships missing from those extracted fields. A missing entry does not mean a member did no work. No complete introduction denominator, passage rate, rank or overall effectiveness score is calculated.</p><p><a href="https://thelawmakers.org/methodology">Research background: Center for Effective Lawmaking</a>. Its effectiveness framework also measures legislative progress and substantive importance; these municipal activity counts are not CEL scores.</p></details>'''

def measure(p,data,role=None,full=False):
    members={m['id']:m for m in data['members']}
    names=lambda ids:', '.join(members[i]['name'] for i in ids)
    labels='<span class="sponsorship-type">'+e(CATEGORIES[p['category']])+'</span>'
    if role:labels+=' <span class="sponsorship-role">'+e(ROLE_LABELS[role])+'</span>'
    if p['carryover']:labels+=' <span class="sponsorship-role">Earlier-year item considered in 2026</span>'
    content='<p class="sponsorship-labels">'+labels+'</p><h4>'+e(p['title'])+'</h4>'
    if full:
        content+='<p><strong>Named sponsors:</strong> '+e(names(p['sponsors']) or 'No council member identified in the extracted clause')+'</p>'
        if p['cosponsors']:content+='<p><strong>Explicit cosponsors:</strong> '+e(names(p['cosponsors']))+'</p>'
    content+='<details class="sponsorship-events"><summary>Read recorded actions and attribution</summary><ul>'
    for o in p['observations']:
        href=o['source_url']+('#page='+str(o['source_page']) if o['source_page'] else '')
        content+='<li><strong>'+e(o['date'])+'</strong><p>'+e(o['action'])+'</p><p class="source">Attribution: '+e(o['attribution'])+'</p><a href="'+e(href)+'">Source minutes'+(', p. '+str(o['source_page']) if o['source_page'] else '')+'</a> · '+e(o['minutes_status'])+'</li>'
    for o in p.get('cosponsor_evidence',[]):
        href=o['source_url']+('#page='+str(o['source_page']) if o['source_page'] else '')
        content+='<li><strong>'+e(o['date'])+' · Additional cosponsor evidence</strong><p>'+e(o['context'])+'</p><p>'+e(o['excerpt'])+'</p><a href="'+e(href)+'">Source minutes</a></li>'
    content+='</ul><p class="source">An approved motion to continue, refer or amend is not final adoption of the underlying policy.</p></details>'
    if p.get('adopted_text'):content+='<p class="source"><a href="'+e(p['adopted_text'])+'">Adopted resolution text</a></p>'
    return content

def render_profile(text,slug,data):
    m=next((m for m in data['members'] if m['id']==slug),None)
    if m:
        c=m['counts']
        metrics=[(c['sponsor'],'Named / joint sponsorships'),(c['ordinance'],'Ordinances'),(c['position']+c['symbolic'],'Policy positions / display policy'),(c['recognition'],'Recognition / commemoration'),(c['cosponsor'],'Additional cosponsorships')]
        body='<p class="intro">2026 council service: <strong>'+e(m['office_2026'])+'</strong>. Measures explicitly attributed to '+e(m['name'])+' in the extracted full-council records.</p>'
        body+='<div class="lawmaker-grid sponsorship-stats">'+''.join('<div><b>'+str(v)+'</b><span>'+label+'</span></div>' for v,label in metrics)+'</div>'
        body+='<p class="sponsorship-coverage"><strong>Partial record of activity.</strong> These are minimum documented counts, not an effectiveness score or a ranking. Sponsorships missing from the extracted records are not counted.</p>'
        for role,key,label in [('sponsor','sponsors','Named and joint sponsorships'),('cosponsor','cosponsors','Additional explicit cosponsorships')]:
            items=sorted([p for p in data['proposals'] if slug in p[key]],key=lambda p:(p['observations'][-1]['date'],p['id']),reverse=True)
            body+='<details class="sponsorship-list"><summary>'+label+' ('+str(len(items))+')</summary><div class="sponsorship-items">'+''.join('<article class="sponsorship-item">'+measure(p,data,role)+'</article>' for p in items)+'</div></details>'
    else:
        body='<p>This profile has no sponsorship count in the 2026 council dataset. The incoming term begins January 4, 2027. The outgoing council’s activity is not assigned to this member.</p>'
        if slug=='steven-a-stycos':body+='<p>Stycos’s earlier council service is outside this 2026 dataset.</p>'
    body+=method()+'<p class="source">Coverage: '+str(data['meeting_count'])+' available full council meeting records. Pilot reviewed November 22, 2026. <a href="/cranston-sponsorship.html">Explore all 2026 council members and the methodology</a> · <a href="/data/cranston/sponsorship-2026.csv" download>Download sponsorship data (CSV)</a></p>'
    section='<section class="card" id="sponsorship"><h2>Observed sponsorship activity</h2>'+body+'</section>'
    text=re.sub(r'<section class="card" id="sponsorship">.*?</section>\s*','',text,flags=re.S)
    assert '<section class="card" id="votes">' in text
    text=text.replace('<section class="card" id="votes">',section+'\n<section class="card" id="votes">',1)
    text=text.replace('A member-specific sponsorship history has not yet been compiled.','Observed sponsorships and their source records appear below.')
    text=re.sub(r'<p class="source municipal-record-links">.*?</p>','<p class="source municipal-record-links"><a href="#sponsorship">Sponsorship activity</a><a href="#votes">Council votes and attendance</a></p>',text,flags=re.S)
    return text

def overview(data):
    rows=[];options=[]
    identified=len(data['proposals'])
    attributed=sum(bool(p['sponsors'] or p['cosponsors']) for p in data['proposals'])
    for m in data['members']:
        c=m['counts'];href=m['profile_url'] or '?member='+m['id']+'#measures'
        rows.append('<tr><th scope="row"><a href="'+e(href)+'">'+e(m['name'])+'</a></th><td>'+e(m['office_2026'])+'</td>'+''.join('<td>'+str(c[k])+'</td>' for k in ['sponsor','ordinance','position','symbolic','recognition','cosponsor'])+'</tr>')
        options.append('<option value="'+m['id']+'">'+e(m['name'])+'</option>')
    cards=[]
    for p in sorted(data['proposals'],key=lambda p:(p['observations'][-1]['date'],p['id']),reverse=True):
        cards.append('<article class="sponsorship-item" id="'+e(p['id'])+'" data-category="'+p['category']+'" data-sponsors="'+' '.join(p['sponsors'])+'" data-cosponsors="'+' '.join(p['cosponsors'])+'">'+measure(p,data,full=True)+'</article>')
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cranston Council Sponsorship Activity, 2026 | RIEP</title><meta name="description" content="Explore documented Cranston council sponsorships by member and measure type, with source minutes and transparent coverage limits."><link rel="canonical" href="https://www.rhodeislandelectionsproject.org/cranston-sponsorship.html"><link rel="icon" href="/favicon.ico"><link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700;800&family=Sora:wght@600;700&display=swap" rel="stylesheet"><link rel="stylesheet" href="/cranston-records.css"><link rel="stylesheet" href="/candidates/municipal-profile.css?v=20261122-sponsorship"></head><body class="sponsorship-directory"><a class="skip-link" href="#main">Skip to content</a><header><div class="wrap"><a class="brand" href="/"><img src="/riep-logo-light.png" alt=""><span>Rhode Island<br>Elections Project</span></a><nav aria-label="Site navigation"><a href="/cranston-map.html">Cranston map</a><a href="/cranston-records.html">Council votes and attendance</a><a href="/candidate-profiles.html">Candidate profiles</a></nav></div></header><main class="wrap" id="main"><h1>Cranston council sponsorship activity</h1><p class="intro">2026 · A record of measures that members explicitly sponsored or cosponsored.</p><p class="sponsorship-coverage"><strong>Partial coverage, not a productivity ranking.</strong> Counts describe identified activity in extracted full-council records. The original minutes include some sponsorships absent from this extract. No complete introduction count, passage rate or effectiveness score is available.</p><section class="panel"><h2>Documented activity by member</h2><p>Members are listed in the source roster’s order, not ranked. Office labels show their 2026 service. Several members move offices or leave the council in January 2027.</p><div class="table-scroll"><table><caption>Minimum observed member–measure counts. A jointly sponsored measure counts once for each named member.</caption><thead><tr><th scope="col">Member</th><th scope="col">2026 office</th><th scope="col">Named / joint sponsor</th><th scope="col">Ordinances</th><th scope="col">Policy positions</th><th scope="col">Display policy</th><th scope="col">Recognition</th><th scope="col">Additional cosponsor</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div><p><a href="/data/cranston/sponsorship-2026.csv" download>Download individual sponsorship credits (CSV)</a> · <a href="/data/cranston/sponsorship-2026.json">Structured data (JSON)</a></p></section><section class="panel" id="measures"><h2>Browse identified measures</h2><p>Repeated appearances are grouped into one item. Recorded actions remain visible, including amendments and continuances.</p><div class="filters" id="sponsorship-filters" hidden><label>Council member<select id="sponsorship-member"><option value="">All members / all identified items</option>'''+''.join(options)+'''</select></label><label>Role<select id="sponsorship-role"><option value="any">Either role</option><option value="sponsors">Named / joint sponsor</option><option value="cosponsors">Explicit cosponsor</option></select></label><label>Measure type<select id="sponsorship-category"><option value="">All types</option>'''+''.join('<option value="'+k+'">'+v+'</option>' for k,v in CATEGORIES.items())+'''</select></label></div><p id="sponsorship-count" aria-live="polite">'''+str(len(cards))+''' identified measures</p><div id="sponsorship-results">'''+''.join(cards)+'''</div><noscript><p>All items are displayed. Enable JavaScript to filter by member and type.</p></noscript></section><section class="panel" id="methodology"><h2>Coverage and methodology</h2><p>'''+str(data['meeting_count'])+''' available full council meeting records; '''+str(data['motion_count'])+''' extracted motions. The pilot identifies '''+str(identified)+''' measures with formal sponsorship clauses, including mayor-sponsored items; '''+str(attributed)+''' have an explicit council-member sponsorship or cosponsorship. Reviewed November 22, 2026.</p>'''+method()+'''<p>Classification and source boundaries remain under review. Some generic motion titles omit sponsors, late cosponsor additions are not exhaustively recovered, and one recognition resolution appears inside the preceding item’s excerpt. These gaps can affect members differently. An item displayed here is not necessarily newly introduced in 2026 or finally adopted.</p><p><a href="/cranston-records.html#coverage-details">Meeting coverage and unresolved source records</a> · <a href="/data/cranston/records-2026/records.json">Underlying extracted records</a> · <a href="https://clerkshq.com/cranston-ri">Official archive</a></p></section></main><footer><div class="wrap">Rhode Island Elections Project · Independent, nonpartisan public information</div></footer><script src="/cranston-sponsorship.js" defer></script></body></html>'''

def publish():
    data=build()
    registry=json.loads((ROOT/'data/local_representatives.json').read_text())
    for person in registry['profiles']:
        path=ROOT/'candidates'/(person['slug']+'.html')
        if person['slug'] not in ['avery-therese-mangahas','sara-jane-haupt','andy-m-andujar','frank-j-ritz-jr','michael-a-traficante','daniel-robert-wall','emilia-vaziri','steven-a-stycos','kristen-e-haroian']:continue
        path.write_text(render_profile(path.read_text(),person['slug'],data))
    print('Built sponsorship data, overview and nine profile sections')

if __name__=='__main__':publish()
