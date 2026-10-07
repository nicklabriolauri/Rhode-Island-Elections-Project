"""Render House challengers without transferring incumbent records."""
import json,re
from pathlib import Path
from build_candidate_pages import load,esc,link,metrics,candidate_name_matches
from candidate_profile_components import section,replace_section
ROOT=Path(__file__).resolve().parents[1]
SLUGS={'amy-j-santiago':7,'christopher-l-ireland':7,'brittany-m-kubicek':5}
SLUGS.update({'arlette-hidalgo':12,'derick-a-reels':13,'colleen-m-crudele':15,'allan-w-fung':15})
SLUGS.update({'zakary-j-pereira':22,'barbara-quigley':22,'william-muto':23,'dana-james-traversie':23,'angela-s-coburn':27,'lawrence-paul-almagno-jr':27})
SLUGS.update({'james-c-sheehan':31,'robert-e-craven-jr':32,'jessica-drew-day':33})
SLUGS.update({'christopher-m-stanton':37,'jasmin-roy':39})
SLUGS.update({'shaina-n-smith':41,'michael-j-riley':41,'edward-w-stravato':42})
def build(slugs=None):
 incumbent=ROOT/'candidates/anthony-j-desimone.html'
 incumbent.write_text(incumbent.read_text().replace('/running.html?chamber=house&amp;district=5&amp;election=general','/races/house-5.html'))
 roster=load('whos_running_2026')['chambers']['house'];registry={}
 for slug,district in SLUGS.items():
  if slugs is not None and slug not in slugs:continue
  c=next(c for c in roster[str(district)]['candidates'] if c['candidate_id'].endswith('-'+slug));name=c['name'];candidate_id=c['candidate_id'];registry[candidate_id]=slug
  research=next(r for r in load('candidate_research_2026_with_endorsements')['candidates'] if r['candidate_id']==candidate_id)
  party={'DEM':'Democratic','REP':'Republican','OTH':'Independent Socialist','IND':'Independent'}[c['party']]
  community=research.get('district_community') or c.get('hometown','Providence')
  website=research.get('campaign_website','');finance=('/finance-candidates/'+candidate_id+'.html' if c['party'] in ('OTH','IND') else f'/finance.html?slug={slug}')
  page=(ROOT/'candidates/anthony-j-desimone.html').read_text().replace('Anthony J DeSimone',name).replace('anthony-j-desimone',slug).replace('District 5',f'District {district}').replace('district=5',f'district={district}').replace('/races/house-5.html',f'/races/house-{district}.html').replace('Democratic',party).replace('Democrat · Incumbent',party+' · Candidate')
  page=page.replace('· Candidate · Providence','· Candidate · '+community)
  page=page.replace('Portrait of Rhode Island Representative '+name,'Portrait of '+name)
  page=replace_section(page,'voting-patterns','');page=page.replace('<a href="#voting-patterns">Voting patterns</a>','')
  page=re.sub(r'<link[^>]+href="house-voting-patterns/[^>]+>','',page);page=re.sub(r'<script src="house-voting-patterns/[^>]+></script>','',page)
  def replace(id,title,body):
   nonlocal page
   page=replace_section(page,id,section(id,title,body))
  replace('about','About this candidate',f'<p class="intro">{esc(party)} candidate for House District {district} · {esc(community)}.</p><div class="grid2"><div class="mini"><h3>At a glance</h3><p>Candidate in the 2026 general election. Campaign statements and public records are labeled by source and reporting period.</p></div><div class="mini"><h3>How to read this page</h3><p>A candidate without a General Assembly service record is not assigned a legislative score of zero.</p></div></div>'+('<p class="source">'+link(website,'Official campaign website ↗')+'</p>' if website else ''))
  if research.get('race_context'):
   old=re.search(r'<section class="card" id="about">.*?</section>',page,re.S).group()
   context=research['race_context']
   page=page.replace(old,old.replace('</section>',f'<p class="intro">{esc(context["summary"])}</p><p class="source">'+link(context['source_url'],context['source_label']+' ↗')+'</p></section>'))
  if research.get('prior_public_service'):
   prior=research['prior_public_service']
   old=re.search(r'<section class="card" id="about">.*?</section>',page,re.S).group()
   page=page.replace(old,old.replace('</section>',f'<div class="mini"><h3>Earlier public service</h3><p>{esc(prior["summary"])}</p><p class="source">'+link(prior['source_url'],prior['source_label']+' ↗')+'</p></div></section>'))
  supplied=next((p for p in load('candidate_profiles_2026')['profiles'] if p['candidate_id']==candidate_id),{})
  priorities=supplied.get('priorities') or research['priorities'];sources=sorted({(p['source_url'],p.get('source_label','Campaign source')) for p in priorities if p.get('source_url')})
  priority_sources=('Campaign response submitted directly to RIEP' if supplied.get('priorities') else ' · '.join(link(u,label) for u,label in sources))
  replace('priorities','Campaign priorities',('<div class="grid2">'+''.join(f'<div class="mini"><h3>{esc(p["title"])}</h3><p>{esc(p["summary"])}</p></div>' for p in priorities)+'</div><p class="source">'+priority_sources+'. Campaign positions, not RIEP assessments.</p>') if priorities else '<div class="empty"><strong>Campaign priorities under construction</strong><p>No campaign priorities are currently recorded for this candidate in RIEP’s research. This section will be updated after verification.</p></div>')
  elections=[]
  for race in sorted(load('race_data').values(),key=lambda r:int(r['year']),reverse=True):
   if race['chamber'].lower()=='house' and int(race['district_number'])==district:
    for result in race['candidates']:
     if candidate_name_matches(name,result['name']):
      url=f'/map.html?mode=results&chamber=house&year={race["year"]}&view=party&district={district}'
      elections.append(f'<div class="election"><a class="year election-link" href="{esc(url)}">{race["year"]}</a><div><strong>{esc(result["role"])} · {esc(result["votes"])} votes</strong><small>Districtwide general election</small></div><span class="result">{esc(result["pct"])}</span></div>')
  replace('elections','Past electoral performance','<div class="timeline">'+(''.join(elections) or '<p class="intro">No earlier House general-election result is recorded for this candidate in RIEP’s historical dataset. The 2026 general election has not occurred.</p>')+'</div><p class="source">District history and other candidates’ results are separate from this candidate’s individual record.</p>')
  rows=[]
  official=load('candidate_profile_primary_returns_2026').get(slug,[])
  if isinstance(official,dict):official=[official]
  for result in official:
   url=result['source_url'];label=('Uncontested ' if result.get('uncontested') else '')+result['party']+' primary · Official results'
   rows.append(f'<div class="election"><a class="year election-link" href="{esc(url)}">{result["year"]}</a><div><strong>{result["votes"]:,} votes</strong><small>{esc(label)}</small></div><a class="result election-link" href="{esc(url)}">{esc(result["share"])}</a></div>')
  for race in load('primary_results_2026')['races']:
   if not official and race['chamber']=='house' and race['district']==district and race['party_code']==c['party']:
    for result in race['candidates']:
     if candidate_name_matches(name,result['name']):
      url=f'/races/house-{district}-'+('democratic' if c['party']=='DEM' else 'republican')+'.html'
      rows.append(f'<div class="election"><a class="year election-link" href="{url}">2026</a><div><strong>{result["votes"]:,} votes</strong><small>{esc(party)} primary · Unofficial September 10 snapshot</small></div><a class="result election-link" href="{url}">{result["pct"]}%</a></div>')
  primary_source=(' · '.join(link(r['source_url'],r['source_label']+' ↗') for r in official)+'. Official 2026 results updated September 15, 2026. Earlier primary years are under construction.' if official else '2026 figures, where shown, use RIEP’s unofficial September 10 snapshot. Earlier primary years are under construction.')
  replace('primaries','Primary history',('<p class="intro">Independent general-election candidate; a party-primary vote total is not assigned.</p>' if c['party'] in ('OTH','IND') else '<div class="timeline">'+(''.join(rows) or '<p>Primary vote totals are under construction. No vote total is assigned from another race.</p>')+'</div><p class="source">'+primary_source+'</p>'))
  if c['party'] in ('OTH','IND'):
   fin=next((r for r in load('independent_finance_supplement_2026')['candidates'] if r['name']==name),{})
   period='Year to date through June 30, 2026 · Q1 and Q2 filings';items=[('Raised in 2026',fin.get('ytd_receipts')),('Spent in 2026',fin.get('ytd_campaign_expenses')),('Cash at period end',fin.get('cash_on_hand'))]
  else:
   fin=next(r for r in load('candidate_finance_2026')['profiles'] if r['slug']==slug);period=fin['report_label']+' · '+fin['reporting_period_label'];items=[(fin.get('receipts_label','Raised during period'),fin['money_raised']),('Spent during period',fin['money_spent']),('Cash at period end',fin['ending_cash'])]
  finance_body=(f'<p class="intro">{esc(period)}. Figures describe the stated reporting period.</p>'+metrics([(label,f'${value:,.2f}') for label,value in items]).replace('record-grid','metric-grid') if all(value is not None for _,value in items) else '<div class="empty"><strong>Campaign finance details under construction</strong><p>No financial summary is currently available in RIEP’s dataset for this candidate. Missing figures are not treated as zero.</p></div>')
  if fin.get('finance_status')=='available_historical':finance_body='<p class="intro">Historical filing only. No 2026 campaign-finance summary is available in RIEP’s dataset.</p>'+finance_body
  replace('finance','Campaign finance snapshot',finance_body+f'<a class="finance-profile-button" href="{esc(finance)}">View {esc(name)}’s campaign finance →</a>')
  if fin.get('latest_filing_href'):
   old=re.search(r'<section class="card" id="finance">.*?</section>',page,re.S).group()
   page=page.replace(old,old.replace('</section>',('<p class="intro">'+esc(fin['finance_snapshot_note'])+'</p>' if fin.get('finance_snapshot_note') else '')+'<p class="source">'+link(fin['latest_filing_href'],'Open 28-days-before-election financial report (PDF) ↗')+'</p></section>'))
  replace('record','Record in office','<div class="empty"><strong>General Assembly record not applicable · Candidate</strong><p>No Rhode Island General Assembly service record is attributed to this candidate in RIEP’s dataset. Legislative sponsorship, attendance and committee roles are not assigned.</p></div>')
  replace('bills','Bills &amp; votes','<p class="intro">No General Assembly sponsored-bill or roll-call record is attributed to this candidate. Campaign positions are shown above.</p>')
  replace('ratings','Outside ratings &amp; scorecards','<p class="intro">CEL legislative-effectiveness scores, the RIEP legislative progress index and W-NOMINATE voting positions require a legislative record. They are not applicable to this candidate, and no incumbent’s or district-level score is transferred here.</p>')
  endorsements=research['endorsements']
  replace('endorsements','Endorsements',('<p class="intro">Published endorsements from outside organizations. Select an organization to view its source.</p>' if endorsements else '<p class="intro">No published endorsements are currently recorded for this candidate in RIEP’s research.</p>')+''.join(f'<div class="endorsement-entry"><a class="endorsement-chip" href="{esc(e["source_url"])}" target="_blank" rel="noopener">{esc(e["endorser"])} ↗</a><p class="endorsement-period">2026 election · House District {district}</p></div>' for e in endorsements)+'<p class="source">Outside endorsements, not RIEP endorsements.</p>')
  replace('sources','Under construction','<p class="intro">This candidate profile is under construction. Additional campaign information, election history and digital-footprint research will be added after verification.</p>')
  contact=research.get('campaign_contact',{})
  phone=contact.get('phone') or c.get('phone');email=contact.get('email') or c.get('email')
  replace('contact','Contact &amp; district','<dl class="details">'+''.join(f'<div><dt>{label}</dt><dd>{value}</dd></div>' for label,value in [('District',f'House District {district}'),('Community',esc(community)),('Campaign phone' if contact.get('phone') else 'Roster contact phone',link('tel:+1'+re.sub('[^0-9]','',phone),phone) if phone else 'Not listed'),('Campaign email' if contact.get('email') else 'Roster contact email',link('mailto:'+email,email) if email else 'Not listed')])+'</dl><p class="source">'+(link(contact['source_url'],'Official campaign contact details ↗') if contact else '2026 Department of State candidate roster.')+'</p>')
  portraits=load('candidate_portrait_sources_2026');portrait=next((p for p in portraits if p['slug']==slug),None)
  if portrait:
   page=page.replace(slug+'.png',portrait.get('file_name',slug+'.png'))
   if slug=='jasmin-roy':page=page.replace('class="portrait"','class="portrait" style="height:auto;object-fit:contain"')
   if slug=='christopher-m-stanton':page=page.replace('class="portrait"','class="portrait" style="object-position:20% top"')
   if slug=='brittany-m-kubicek':page=page.replace('class="portrait"','class="portrait" style="object-position:25% top"')
   page=re.sub(r'<p class="photo-note">.*?</p>', '<p class="photo-note">Portrait: '+link(portrait['biography_url'],portrait['credit']+' ↗')+'</p>',page)
   page=re.sub(r'(class="portrait"[^>]*?)width="[0-9]+" height="[0-9]+"',lambda m:m[1]+f'width="{portrait["width"]}" height="{portrait["height"]}"',page)
  else:page=re.sub(r'<div><img class="portrait".*?</div>','<div class="mini"><h2>Candidate portrait</h2><p>Photo under construction</p></div>',page,flags=re.S)
  page=re.sub(r'href="/finance.html\?slug='+re.escape(slug)+r'"',lambda m:'href="'+finance+'"',page)
  page=re.sub(r'href="/running.html\?chamber=house(?:&amp;|&)district='+str(district)+r'(?:&amp;|&)election=general"',f'href="/races/house-{district}.html"',page)
  assert 'data-voting-widget' not in page and 'riep-legislative-index' not in page and 'rep-desimone' not in page
  if district in (15,22,23,27,31,32,33,37,39,41,42):page=page.replace(f'href="/races/house-{district}.html"',f'href="/running.html?chamber=house&amp;district={district}&amp;election=general"')
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
