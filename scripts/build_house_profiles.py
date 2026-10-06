"""Build the published Providence-area House profiles from existing, dated RIEP records."""
import json, re
from urllib.parse import quote
from pathlib import Path
import build_candidate_pages as base
from candidate_profile_components import section, replace_section, ratings, bill_sections, current_index
ROOT=Path(__file__).resolve().parents[1]
CONFIGS=[('Edith H Ajello','edith-h-ajello',1,'ajello','edith_ajello', '(401) 222-2296'),('Christopher R Blazejewski','christopher-r-blazejewski',2,'blazejewski','christopher_blazejewski','(401) 222-2466'),('Nathan W Biah','nathan-w-biah',3,'biah','nathan_biah','(401) 222-1224'),('Rebecca M Kislak','rebecca-m-kislak',4,'Kislak','rebecca_kislak','(401) 222-1591')]
CONFIGS += [('Raymond A Hull','raymond-a-hull',6,'Hull','raymond_hull','(401) 222-1723'),('John Joseph Lombardi','john-joseph-lombardi',8,'lombardi','john_lombardi','(401) 222-1721'),('Enrique George Sanchez','enrique-george-sanchez',9,'Sanchez','enrique_sanchez','(401) 222-1162'),('Scott A Slater','scott-a-slater',10,'slater','scott_slater','(401) 222-1591')]

def build():
 # The shared component withholds the House index until all district records exist.
 base.current_index=current_index
 fogarty=(ROOT/'candidates/kathleen-a-fogarty.html').read_text()
 widget=re.search(r'<section class="card voting-pilot" id="voting-patterns">.*?</section>',fogarty,re.S).group()
 portraits=json.loads((ROOT/'data/candidate_portrait_sources_2026.json').read_text())
 records=base.load('incumbent_records_2026')['records']
 primary=base.load('primary_results_2026')['races']
 registry={}
 for name,slug,district,surname,image,phone in CONFIGS:
  bio=f'https://www.rilegislature.gov/representatives/{surname}/Pages/Biography.aspx'
  community='Providence, North Providence' if district==6 else 'Providence'
  email=f'rep-{surname.lower()}@rilegislature.gov'
  base.build(name,slug,district,community,email,phone,'house')
  path=ROOT/'candidates'/f'{slug}.html';page=path.read_text()
  rec=next(r for r in records if r['chamber']=='house' and r['district_number']==district)
  registry[rec['candidate_id']]=slug
  page=replace_section(page,'bills',bill_sections(rec,slug))
  page=replace_section(page,'ratings',ratings(rec))
  page=replace_section(page,'about',section('about','About this candidate',f'<p class="intro">{base.esc(name)} represents House District {district} · {base.esc(community)}.</p><div class="grid2"><div class="mini"><h3>At a glance</h3><p>Democratic incumbent in the 2026 candidate roster.</p></div><div class="mini"><h3>How to read this page</h3><p>Campaign positions, election returns, campaign finance and outside scorecards are labeled by source and period.</p></div></div><p class="source">'+base.link(bio,'Official General Assembly biography ↗')+'</p>'))
  contact=section('contact','Contact &amp; district','<dl class="details">'+''.join(f'<div><dt>{k}</dt><dd>{v}</dd></div>' for k,v in [('District',f'House District {district}'),('Community',base.esc(community)),('Phone',base.link('tel:+1'+re.sub('[^0-9]','',phone),phone)),('Legislative email',base.link('mailto:'+email,email))])+'</dl><p class="source">'+base.link(bio,'Official General Assembly contact details ↗')+'</p>')
  page=re.sub(r'(<aside class="side"[^>]*>)<section class="card">.*?</section>',lambda m:m[1]+contact,page,count=1,flags=re.S)
  rows=[]
  for race in primary:
   if race['chamber']!='house' or int(race['district'])!=district or race['party_code']!='DEM':continue
   for c in race['candidates']:
    if c['name']!=name:continue
    url=f'/races/house-{district}-democratic.html'
    rows.append(f'<div class="election"><a class="year election-link" href="{url}">2026</a><div><strong>{c["votes"]:,} votes</strong><small>Democratic primary · Unofficial September 10 snapshot</small></div><a class="result election-link" href="{url}">{c["pct"]}%</a></div>')
  body=f'<p class="intro">House District {district} · Share of votes cast for named candidates.</p><div class="timeline">'+(''.join(rows) or '<p>Primary vote totals are under construction. No vote total is assigned from a different race.</p>')+'</div><p class="source">'+('2026 figures use RIEP’s unofficial September 10 snapshot. Earlier primary years are under construction. ' if rows else '')+base.link('https://electionresults.ri.gov/results/public/rhodeisland/elections/RI2026StatewidePrimary','Official 2026 Board of Elections results ↗')+'</p>'
  page=replace_section(page,'primaries',section('primaries','Democratic primary history',body))
  research=next(r for r in base.load('candidate_research_2026_with_endorsements')['candidates'] if r['candidate_id']==rec['candidate_id'])
  endorsements=research['endorsements']
  page=replace_section(page,'endorsements',section('endorsements','Endorsements',('<p class="intro">Published endorsements from outside organizations. Select an organization to view its endorsement source.</p>' if endorsements else '<p class="intro">No published endorsements are currently recorded for this candidate in RIEP’s research. Additional endorsements will be added after verification.</p>')+''.join(f'<div class="endorsement-entry"><a class="endorsement-chip" href="{base.esc(e["source_url"])}" target="_blank" rel="noopener">{base.esc(e["endorser"])} ↗</a><p class="endorsement-period">2026 election · House District {district}</p></div>' for e in endorsements)+'<p class="source">Outside organizations’ endorsements, not RIEP endorsements. Sources may include organization lists and voter-guide records.</p>'))
  selected=widget.replace('Kathleen A Fogarty',name).replace('Kathleen%20A%20Fogarty',quote(name))
  page=page.replace('<section class="card" id="bills">',selected+'<section class="card" id="bills">',1)
  page=page.replace('href="voting-patterns/pilot.css','href="house-voting-patterns/pilot.css')
  page=page.replace('</body>','<script src="candidate-profile.js"></script><script src="house-voting-patterns/pilot.js?v=20261006-house"></script></body>')
  page=page.replace('Rhode Island Senator','Rhode Island Representative').replace('chamber=senate','chamber=house').replace('October 4, 2026','October 6, 2026')
  page=re.sub(r'<p class="photo-note">.*?</p>','<p class="photo-note">Portrait: '+base.link(bio,'Rhode Island General Assembly ↗')+'</p>',page)
  from PIL import Image
  w,h=Image.open(ROOT/'candidates'/f'{slug}.png').size
  page=re.sub(r'(class="portrait"[^>]*?)width="[0-9]+" height="[0-9]+"',lambda m:m[1]+f'width="{w}" height="{h}"',page)
  page=page.replace('<aside class="side">','<aside class="side" aria-label="Candidate details and navigation">').replace('<h3>Session attendance</h3>','<h3 class="subheading">Session attendance</h3>')
  start=page.index('<section class="card" id="finance">');end=page.index('<section class="card" id="record">');page=page[:start]+page[start:end].replace('class="record-grid"','class="metric-grid"')+page[end:]
  page=re.sub(r'<p><strong>Leadership:</strong> (.*?)</p><p><strong>Committees:</strong> (.*?)</p>',r'<dl class="office-details"><div><dt>Leadership</dt><dd>\1</dd></div><div><dt>Committees</dt><dd>\2</dd></div></dl>',page)
  if district==2:page=page.replace('<dd></dd>','<dd>No committee assignments listed in the recorded roster.</dd>')
  assert 'chamber=senate' not in page and 'Senate District' not in page
  path.write_text(page)
  entry={'slug':slug,'portrait_url':f'https://www.rilegislature.gov/LegislationPictures/{image}.jpg','biography_url':bio,'retrieved_at':'2026-10-06','credit':'Rhode Island General Assembly','width':w,'height':h}
  portraits=[r for r in portraits if r['slug']!=slug]+[entry]
 (ROOT/'data/candidate_portrait_sources_2026.json').write_text(json.dumps(portraits,indent=2)+'\n')
 for filename in ['ballot.html','running.html']:
  path=ROOT/filename;page=path.read_text()
  def extend(m):
   entries=json.loads(m[1]);entries.update(registry)
   return 'const candidateProfile = ('+json.dumps(entries,separators=(',',':'))+')[candidate.candidate_id]'
  page,n=re.subn(r'const candidateProfile = \((\{.*?\})\)\[candidate.candidate_id\]',extend,page);assert n==1
  path.write_text(page)
 path=ROOT/'index.html';page=path.read_text();marker='      if(candidate?.chamber !== "senate") return "";'
 profiles={district:[name.split()[-1].lower(),slug] for name,slug,district,*_ in CONFIGS}
 house='      if(candidate?.chamber === "house") {\n        const profiles = '+json.dumps(profiles,separators=(',',':'))+';\n        const profile = profiles[Number(candidate.district_number)];\n        return profile && normalizeSearchText(candidate.name || "").split(" ").includes(profile[0]) ? `candidates/${profile[1]}.html` : "";\n      }\n'
 pattern=r'      if\(candidate\?\.chamber === "house"\) \{\n.*?\n      \}\n'
 if re.search(pattern,page,re.S):page=re.sub(pattern,lambda m:house,page,count=1,flags=re.S)
 else:page=page.replace(marker,house+marker,1)
 path.write_text(page)
if __name__=='__main__':build()
