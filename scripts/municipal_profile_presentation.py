"""Shared, idempotent municipal profile presentation; no inferred scores or posts."""
from pathlib import Path
from html import escape as e
import json,re
ROOT=Path(__file__).resolve().parents[1]
def replace_section(s, ident, html):
 pattern=rf'<section class="card" id="{ident}">.*?</section>'
 if re.search(pattern,s,re.S):return re.sub(pattern,lambda _:html,s,count=1,flags=re.S)
 return s.replace('<section class="card" id="primaries">',html+'<section class="card" id="primaries">',1) if ident=='election-history' else s.replace('<section class="card" id="sources">',html+'<section class="card" id="sources">',1)
def refresh():
 registry=json.loads((ROOT/'data/local_representatives.json').read_text())
 extras=json.loads((ROOT/'data/cranston/profile-enrichment-2026.json').read_text())
 history=json.loads((ROOT/'data/cranston/election-history.json').read_text())
 for p in registry['profiles']:
  slug=p['slug']; rating=extras['bffi']['ratings'].get(slug)
  if not rating:continue
  path=ROOT/'candidates'/(slug+'.html');s=path.read_text()
  tone={'For':'for','Against':'against','N/A':'unavailable'}[rating]
  note={'For':'The Womxn Project places this candidate in its category for support of reproductive rights, gender-affirming care and LGBTQ+ rights.','Against':'The Womxn Project places this candidate in its category opposing its bodily freedom criteria.','N/A':'The Womxn Project reports insufficient information for this candidate. N/A does not mean opposition.'}[rating]
  card=f'''<section class="card" id="ratings"><h2>Outside scorecards and ratings</h2><div class="municipal-bffi bffi-{tone}"><div class="municipal-bffi-head"><div><p class="eyebrow">The Womxn Project · 2026 general election</p><h3>Bodily Freedom Forever Index</h3><p class="intro">Reproductive rights and LGBTQ+ rights · BFFI</p></div><strong class="municipal-bffi-badge">{e(rating)}</strong></div><p><strong>{e(p['name'])}: {e(rating)}.</strong> {note}</p><details><summary>What the rating means &amp; how it is assigned</summary><p>This is the publisher’s categorical voter-guide rating, reproduced from its Cranston listing. It is not a percentage, a legislative effectiveness score or an endorsement by RIEP. “For”, “Against” and “N/A” retain the publisher’s labels. N/A indicates insufficient information.</p><p><a href="https://thewomxnproject.org/bffi/">Read the publisher’s methodology ↗</a></p></details><p class="source"><a href="{e(extras['bffi']['source'])}">Cranston candidate listing ↗</a> · Reviewed {e(extras['reviewed'])}. Dated snapshot of the published guide.</p></div></section>'''
  s=replace_section(s,'ratings',card)
  endorsement=extras['endorsements'].get(slug)
  if endorsement:
   card=f'''<section class="card" id="endorsements"><h2>Endorsements</h2><p class="intro">Published endorsements from outside organizations. Select an organization to view its source.</p><div class="endorsement-entry"><a class="endorsement-chip" href="{e(endorsement['source'])}">{e(endorsement['organization'])} ↗</a><p class="endorsement-period">2026 City Council election</p><p>Reviewed {e(extras['reviewed'])}. Listed separately from issue ratings; inclusion is not an endorsement by RIEP.</p></div></section>'''
   s=replace_section(s,'endorsements',card)
  # Match an individual's own recorded name, never the district winner or predecessor.
  general=p.get('general',{})
  ballot_name={'avery-therese-mangahas':'Avery Mangahas','frank-j-ritz-jr':'Frank Ritz','daniel-robert-wall':'Daniel Wall'}.get(slug,p['name'])
  own=next((c for c in general.get('candidates',[]) if c['name']==ballot_name),None)
  assert own is not None, f'Missing individual ballot match: {slug}'
  entries=[]
  if own:entries.append({'year':2026,'votes':own['votes'],'share':own['share'],'office':('Citywide · three seats' if general.get('seats')==3 else 'Ward '+str(p['ward'])+' · one seat'),'source':general['source'],'map':('/cranston-map.html?colors=returns#citywide-title' if general.get('seats')==3 else '/cranston-map.html?ward='+str(p['ward'])+'&colors=returns'),'unofficial':not general.get('is_official')})
  entries+=history['candidates'].get(slug,[])
  rows=[]
  for x in entries:
   url=x.get('map',x['source']);label='View map →' if x.get('map') else 'Official returns ↗'
   rows.append(f'''<div class="election"><a class="year municipal-year" href="{e(url)}" aria-label="{x['year']} {e(x['office'])} results">{x['year']}<small>{label}</small></a><div><strong>Winner · {x['votes']:,} votes</strong><small>Cranston City Council · {e(x['office'])}</small><small>{'Unofficial vote snapshot · ' if x.get('unofficial') else ''}<a href="{e(x['source'])}">{x['year']} source returns ↗</a></small></div><span class="result">{x['share']:.1f}%</span></div>''')
  body=''.join(rows) or '<p>No earlier election results have been verified for this candidate.</p>'
  card='<section class="card" id="election-history"><h2>Past electoral performance</h2><p class="intro">Verified general-election results for this individual, with the office held in each election.</p><div class="timeline">'+body+'</div><p class="source">Shares include reported write-in votes. In citywide contests, shares are of all candidate votes across a three-seat race, not the percentage of voters; they are not directly comparable with single-seat ward shares. Coverage currently includes 2026 and verified 2024 ward results. Earlier elections remain under review.</p></section>'
  s=replace_section(s,'election-history',card)
  links=[f'<a class="button secondary" href="{e(x["url"])}">{e(x["label"])} ↗</a>' for x in p.get('social_links',[])]
  if p.get('sources',{}).get('campaign'):links.append(f'<a class="button secondary" href="{e(p["sources"]["campaign"])}">Campaign website ↗</a>')
  if p.get('sources',{}).get('council'):links.append(f'<a class="button secondary" href="{e(p["sources"]["council"])}">Council information ↗</a>')
  card='<section class="card" id="communications"><h2>Digital Listening</h2><p class="intro">Read this member’s public statements at the source.</p><div class="actions">'+''.join(links)+'</div><details><summary>About the planned digital listening feature</summary><p>RIEP is developing a way to explore public posts by topic, date and platform, with links to the original statements. A live post feed is not connected yet. These source links do not represent an exhaustive archive, a sentiment score or an ideology rating.</p></details></section>'
  s=replace_section(s,'communications',card)
  nav="<nav class=\"tabs\" aria-label=\"Profile sections\"><div class=\"shell\"><a href=\"#about\">Overview</a><a href=\"#priorities\">Priorities</a><a href=\"#elections\">Elections</a><a href=\"#finance\">Finance</a><a href=\"#record\">Council record</a><a href=\"#ratings\">Scorecards</a><a href=\"#endorsements\">Endorsements</a><a href=\"#communications\">Digital Listening</a><a href=\"#sources\">Sources</a></div></nav>"
  s=re.sub(r'<nav class="tabs".*?</nav>',lambda _:nav,s,count=1,flags=re.S)
  s=s.replace('Public communications','Digital Listening').replace('Public Communications','Digital Listening')
  s=re.sub(r'<p class="source municipal-election-links">.*?</p>','',s,flags=re.S)
  s=re.sub(r'(<section class="card" id="elections"><h2>.*?</h2>)',lambda m:m[1]+"<p class=\"source municipal-election-links\"><a href=\"#elections\">2026 results</a><a href=\"#election-history\">Past results</a><a href=\"#primaries\">Primary history</a></p>",s,count=1,flags=re.S)
  s=re.sub(r'<p class="source municipal-record-links">.*?</p>','',s,flags=re.S)
  s=re.sub(r'(<section class="card" id="record"><h2>.*?</h2>)',lambda m:m[1]+"<p class=\"source municipal-record-links\"><a href=\"#votes\">Council votes and attendance</a></p>",s,count=1,flags=re.S)
  # Keep sponsorship cards through every records/presentation refresh.
  from cranston_sponsorship import render_profile, DATA
  if DATA.exists():s=render_profile(s,slug,json.loads(DATA.read_text()))
  s=re.sub(r'municipal-profile.css\?v=[^"\s]+','municipal-profile.css?v=20261122-sponsorship',s)
  path.write_text(s)
if __name__=='__main__':refresh()

