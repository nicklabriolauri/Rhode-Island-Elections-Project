"""Render House challengers without transferring incumbent records."""
import json,re
from pathlib import Path
from build_candidate_pages import load,esc,link,metrics,candidate_name_matches
from candidate_profile_components import section,replace_section
ROOT=Path(__file__).resolve().parents[1]
SLUGS={'amy-j-santiago':7,'christopher-l-ireland':7,'brittany-m-kubicek':5}
def build():
 incumbent=ROOT/'candidates/anthony-j-desimone.html'
 incumbent.write_text(incumbent.read_text().replace('/running.html?chamber=house&amp;district=5&amp;election=general','/races/house-5.html'))
 roster=load('whos_running_2026')['chambers']['house'];registry={}
 for slug,district in SLUGS.items():
  c=next(c for c in roster[str(district)]['candidates'] if c['candidate_id'].endswith('-'+slug));name=c['name'];candidate_id=c['candidate_id'];registry[candidate_id]=slug
  research=next(r for r in load('candidate_research_2026_with_endorsements')['candidates'] if r['candidate_id']==candidate_id)
  party={'DEM':'Democratic','REP':'Republican','OTH':'Independent Socialist'}[c['party']]
  website=research.get('campaign_website','');finance=f'/finance.html?slug={slug}' if slug!='brittany-m-kubicek' else '/finance-candidates/'+candidate_id+'.html'
  page=(ROOT/'candidates/anthony-j-desimone.html').read_text().replace('Anthony J DeSimone',name).replace('anthony-j-desimone',slug).replace('District 5',f'District {district}').replace('district=5',f'district={district}').replace('/races/house-5.html',f'/races/house-{district}.html').replace('Democratic',party).replace('Democrat · Incumbent',party+' · Candidate')
  page=page.replace('Portrait of Rhode Island Representative '+name,'Portrait of '+name)
  page=replace_section(page,'voting-patterns','');page=page.replace('<a href="#voting-patterns">Voting patterns</a>','')
  page=re.sub(r'<link[^>]+href="house-voting-patterns/[^>]+>','',page);page=re.sub(r'<script src="house-voting-patterns/[^>]+></script>','',page)
  def replace(id,title,body):
   nonlocal page
   page=replace_section(page,id,section(id,title,body))
  replace('about','About this candidate',f'<p class="intro">{esc(party)} candidate for House District {district} · Providence.</p><div class="grid2"><div class="mini"><h3>At a glance</h3><p>Candidate in the 2026 general election. Campaign statements and public records are labeled by source and reporting period.</p></div><div class="mini"><h3>How to read this page</h3><p>A candidate without a General Assembly service record is not assigned a legislative score of zero.</p></div></div>'+('<p class="source">'+link(website,'Official campaign website ↗')+'</p>' if website else ''))
  priorities=research['priorities'];sources=sorted({(p['source_url'],p.get('source_label','Campaign source')) for p in priorities if p.get('source_url')})
  replace('priorities','Campaign priorities',('<div class="grid2">'+''.join(f'<div class="mini"><h3>{esc(p["title"])}</h3><p>{esc(p["summary"])}</p></div>' for p in priorities)+'</div><p class="source">'+' · '.join(link(u,label) for u,label in sources)+'. Campaign positions, not RIEP assessments.</p>') if priorities else '<div class="empty"><strong>Campaign priorities under construction</strong><p>No campaign priorities are currently recorded for this candidate in RIEP’s research. This section will be updated after verification.</p></div>')
  elections=[]
  for race in sorted(load('race_data').values(),key=lambda r:int(r['year']),reverse=True):
   if race['chamber'].lower()=='house' and int(race['district_number'])==district:
    for result in race['candidates']:
     if candidate_name_matches(name,result['name']):
      url=f'/map.html?mode=results&chamber=house&year={race["year"]}&view=party&district={district}'
      elections.append(f'<div class="election"><a class="year election-link" href="{esc(url)}">{race["year"]}</a><div><strong>{esc(result["role"])} · {esc(result["votes"])} votes</strong><small>Districtwide general election</small></div><span class="result">{esc(result["pct"])}</span></div>')
  replace('elections','Past electoral performance','<div class="timeline">'+(''.join(elections) or '<p class="intro">No earlier House general-election result is recorded for this candidate in RIEP’s historical dataset. The 2026 general election has not occurred.</p>')+'</div><p class="source">District history and other candidates’ results are separate from this candidate’s individual record.</p>')
  rows=[]
  for race in load('primary_results_2026')['races']:
   if race['chamber']=='house' and race['district']==district and race['party_code']==c['party']:
    for result in race['candidates']:
     if candidate_name_matches(name,result['name']):
      url=f'/races/house-{district}-'+('democratic' if c['party']=='DEM' else 'republican')+'.html'
      rows.append(f'<div class="election"><a class="year election-link" href="{url}">2026</a><div><strong>{result["votes"]:,} votes</strong><small>{esc(party)} primary · Unofficial September 10 snapshot</small></div><a class="result election-link" href="{url}">{result["pct"]}%</a></div>')
  replace('primaries','Primary history',('<p class="intro">Independent general-election candidate; a party-primary vote total is not assigned.</p>' if c['party']=='OTH' else '<div class="timeline">'+(''.join(rows) or '<p>Primary vote totals are under construction. No vote total is assigned from another race.</p>')+'</div><p class="source">2026 figures, where shown, use RIEP’s unofficial September 10 snapshot. Earlier primary years are under construction.</p>'))
  if c['party']=='OTH':
   fin=next(r for r in load('independent_finance_supplement_2026')['candidates'] if r['name']==name)
   period='Year to date through June 30, 2026 · Q1 and Q2 filings';items=[('Raised in 2026',fin['ytd_receipts']),('Spent in 2026',fin['ytd_campaign_expenses']),('Cash at period end',fin['cash_on_hand'])]
  else:
   fin=next(r for r in load('candidate_finance_2026')['profiles'] if r['slug']==slug);period=fin['report_label']+' · '+fin['reporting_period_label'];items=[('Raised during period',fin['money_raised']),('Spent during period',fin['money_spent']),('Cash at period end',fin['ending_cash'])]
  replace('finance','Campaign finance snapshot',f'<p class="intro">{esc(period)}. Figures describe the stated reporting period.</p>'+metrics([(label,f'${value:,.2f}') for label,value in items]).replace('record-grid','metric-grid')+f'<a class="finance-profile-button" href="{esc(finance)}">View {esc(name)}’s campaign finance →</a>')
  replace('record','Record in office','<div class="empty"><strong>General Assembly record not applicable · Candidate</strong><p>No Rhode Island General Assembly service record is attributed to this candidate in RIEP’s dataset. Legislative sponsorship, attendance and committee roles are not assigned.</p></div>')
  replace('bills','Bills &amp; votes','<p class="intro">No General Assembly sponsored-bill or roll-call record is attributed to this candidate. Campaign positions are shown above.</p>')
  replace('ratings','Outside ratings &amp; scorecards','<p class="intro">CEL legislative-effectiveness scores, the RIEP legislative progress index and W-NOMINATE voting positions require a legislative record. They are not applicable to this candidate, and no incumbent’s or district-level score is transferred here.</p>')
  endorsements=research['endorsements']
  replace('endorsements','Endorsements',('<p class="intro">Published endorsements from outside organizations. Select an organization to view its source.</p>' if endorsements else '<p class="intro">No published endorsements are currently recorded for this candidate in RIEP’s research.</p>')+''.join(f'<div class="endorsement-entry"><a class="endorsement-chip" href="{esc(e["source_url"])}" target="_blank" rel="noopener">{esc(e["endorser"])} ↗</a><p class="endorsement-period">2026 election · House District {district}</p></div>' for e in endorsements)+'<p class="source">Outside endorsements, not RIEP endorsements.</p>')
  replace('sources','Under construction','<p class="intro">This candidate profile is under construction. Additional campaign information, election history and digital-footprint research will be added after verification.</p>')
  replace('contact','Contact &amp; district','<dl class="details">'+''.join(f'<div><dt>{label}</dt><dd>{value}</dd></div>' for label,value in [('District',f'House District {district}'),('Community','Providence'),('Roster contact phone',link('tel:+1'+re.sub('[^0-9]','',c['phone']),c['phone'])),('Roster contact email',link('mailto:'+c['email'],c['email']))])+'</dl><p class="source">2026 Department of State candidate roster.</p>')
  portraits=load('candidate_portrait_sources_2026');portrait=next((p for p in portraits if p['slug']==slug),None)
  if portrait:
   if slug=='brittany-m-kubicek':page=page.replace('class="portrait"','class="portrait" style="object-position:25% top"')
   page=re.sub(r'<p class="photo-note">.*?</p>', '<p class="photo-note">Portrait: '+link(portrait['biography_url'],portrait['credit']+' ↗')+'</p>',page)
   page=re.sub(r'(class="portrait"[^>]*?)width="[0-9]+" height="[0-9]+"',lambda m:m[1]+f'width="{portrait["width"]}" height="{portrait["height"]}"',page)
  else:page=re.sub(r'<div><img class="portrait".*?</div>','<div class="mini"><h2>Candidate portrait</h2><p>Photo under construction</p></div>',page,flags=re.S)
  page=re.sub(r'href="/finance.html\?slug='+re.escape(slug)+r'"',lambda m:'href="'+finance+'"',page)
  page=re.sub(r'href="/running.html\?chamber=house(?:&amp;|&)district='+str(district)+r'(?:&amp;|&)election=general"',f'href="/races/house-{district}.html"',page)
  assert 'data-voting-widget' not in page and 'riep-legislative-index' not in page and 'rep-desimone' not in page
  (ROOT/'candidates'/f'{slug}.html').write_text(page)
 for filename in ['ballot.html','running.html']:
  p=ROOT/filename;s=p.read_text()
  def extend(m):
   entries=json.loads(m[1]);entries.update(registry);return 'const candidateProfile = ('+json.dumps(entries,separators=(',',':'))+')[candidate.candidate_id]'
  s,n=re.subn(r'const candidateProfile = \((\{.*?\})\)\[candidate.candidate_id\]',extend,s);assert n==1;p.write_text(s)
 all_registry=json.loads(re.search(r'const candidateProfile = \((\{.*?\})\)\[candidate.candidate_id\]',(ROOT/'ballot.html').read_text())[1])
 houses={d:[] for d in roster}
 for d,race in roster.items():
  for candidate in race['candidates']:
   if candidate['candidate_id'] in all_registry:houses[d].append([candidate['name'].split()[-1].lower(),all_registry[candidate['candidate_id']]])
 p=ROOT/'index.html';s=p.read_text();block='      if(candidate?.chamber === "house") {\n        const profiles = '+json.dumps(houses,separators=(',',':'))+';\n        const profile = (profiles[Number(candidate.district_number)] || []).find(p=>normalizeSearchText(candidate.name || "").split(" ").includes(p[0]));\n        return profile ? `candidates/${profile[1]}.html` : "";\n      }\n'
 s,n=re.subn(r'      if\(candidate\?\.chamber === "house"\) \{\n.*?\n      \}\n',lambda m:block,s,count=1,flags=re.S);assert n==1;p.write_text(s)
if __name__=='__main__':build()
