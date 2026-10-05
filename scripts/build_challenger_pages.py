"""Render challenger pages in the shared candidate layout, without office-holder data."""
import json,re
from pathlib import Path
from build_candidate_pages import esc,link,metrics,load
from candidate_profile_components import section,replace_section
ROOT=Path(__file__).resolve().parents[1]
def build_burdette():
 name='Nelly Burdette';slug='nelly-burdette';candidate_id='senate-17-dem-primary-nelly-burdette'
 page=(ROOT/'candidates/thomas-j-paolino.html').read_text()
 # Reuse the established page shell. Every candidate-content section is replaced below.
 page=page.replace('Thomas J Paolino',name).replace('thomas-j-paolino',slug).replace('Republican','Democratic').replace('Incumbent','Challenger').replace('Portrait of Rhode Island Senator Nelly Burdette','Portrait of Nelly Burdette')
 page=re.sub(r'<p class="photo-note">.*?</p>','<p class="photo-note">Portrait: <a href="https://electnelly.com/">Nelly Burdette campaign ↗</a></p>',page)
 portrait=next(x for x in load('candidate_portrait_sources_2026') if x['slug']==slug)
 page=page.replace('width="450" height="600"',f'width="{portrait["width"]}" height="{portrait["height"]}"')
 research=next(r for r in load('candidate_research_2026_with_endorsements')['candidates'] if r['candidate_id']==candidate_id)
 def replace(id,title,body):
  nonlocal page
  page=replace_section(page,id,section(id,title,body))
 replace('about','About this candidate','<p class="intro">Democratic candidate for Senate District 17 · Lincoln, North Smithfield and North Providence.</p><div class="grid2"><div class="mini"><h3>At a glance</h3><p>Burdette’s campaign describes her as a psychologist and first-generation immigrant with two decades of experience helping people navigate healthcare, housing and economic challenges.</p></div><div class="mini"><h3>How to read this page</h3><p>Campaign statements, election returns, finance and endorsements are labeled by source and period. A challenger’s lack of a legislative record is not a score of zero.</p></div></div><p class="source"><a href="https://electnelly.com/about">Official campaign biography ↗</a></p>')
 replace('priorities','Campaign priorities','<div class="grid2">'+''.join('<div class="mini"><h3>'+esc(p['title'])+'</h3><p>'+esc(p['summary'])+'</p></div>' for p in research['priorities'])+'</div><p class="source"><a href="https://electnelly.com/">Official campaign website ↗</a> · Campaign positions, not RIEP assessments.</p>')
 replace('elections','Past electoral performance','<p class="intro">No earlier State Senate general-election result is recorded for Burdette in RIEP’s historical dataset. The 2026 general election has not occurred.</p><a class="score-comparison-link" href="/map.html?mode=results&amp;chamber=senate&amp;year=2024&amp;view=party&amp;district=17">Explore District 17 historical general-election results →</a><p class="source">District history is separate from Burdette’s individual electoral record.</p>')
 entries=load('candidate_profile_primary_returns_2026')[slug]
 replace('primaries','Democratic primary history','<p class="intro">Senate District 17 · Select the year or share to view this primary result.</p><div class="timeline">'+''.join(f'<div class="election"><a class="year election-link" href="{esc(e["source_url"])}">{e["year"]}</a><div><strong>Advanced · {e["votes"]:,} votes</strong><small>Uncontested Democratic primary · Official results</small></div><a class="result election-link" href="{esc(e["source_url"])}">{esc(e["share"])}</a></div>' for e in entries)+'</div><p class="source">Official Rhode Island Board of Elections returns. An uncontested 100% is the share of named-candidate votes, excluding undervotes.</p>')
 fin=next(r for r in load('candidate_finance_2026')['profiles'] if r['slug']==slug)
 replace('finance','Campaign finance snapshot',f'<p class="intro">{esc(fin["report_label"])} · {esc(fin["reporting_period_label"])}.</p>'+metrics([(label,f'${fin[k]:,.2f}') for label,k in [('Raised during period','money_raised'),('Spent during period','money_spent'),('Cash at period end','ending_cash')]]).replace('record-grid','metric-grid')+'<a class="finance-profile-button" href="/finance.html?slug=nelly-burdette">View Nelly Burdette’s campaign finance →</a>')
 replace('record','Record in office','<div class="empty"><strong>Not applicable · Challenger</strong><p>Burdette does not have a Rhode Island General Assembly service record in RIEP’s current dataset. Sponsorship counts and legislative attendance are not assigned to her.</p></div>')
 replace('bills','Bills &amp; votes','<p class="intro">No Rhode Island General Assembly sponsored-bill or roll-call record is attributed to Burdette in this dataset. Her campaign positions appear above.</p>')
 replace('ratings','Outside ratings &amp; scorecards','<p class="intro">Legislative-effectiveness scores and the experimental RIEP index are not applicable to this challenger. No legislator’s record or district-level score is transferred to Burdette.</p>')
 replace('endorsements','Endorsements','<p class="intro">Published endorsements from outside organizations. Select an organization to view its source.</p>'+''.join(f'<div class="endorsement-entry"><a class="endorsement-chip" href="{esc(e["source_url"])}" target="_blank" rel="noopener">{esc(e["endorser"])} ↗</a><p class="endorsement-period">2026 election · Senate District 17</p></div>' for e in research['endorsements'])+'<p class="source">Outside endorsements, not RIEP endorsements.</p>')
 replace('sources','Under construction','<p class="intro">This candidate profile is still under construction. Further election history, campaign information and digital-footprint research will be added after verification.</p>')
 replace('contact','Contact &amp; district','<dl class="details"><div><dt>District</dt><dd>Senate District 17</dd></div><div><dt>Community</dt><dd>Lincoln, North Smithfield, North Providence</dd></div><div><dt>Campaign phone</dt><dd><a href="tel:+14018303826">(401) 830-3826</a></dd></div><div><dt>Campaign email</dt><dd><a href="mailto:nelly@electnelly.com">nelly@electnelly.com</a></dd></div></dl>')
 page=page.replace('<a href="legislative-comparison.html">2023–2024 score comparison →</a>','<a href="https://electnelly.com/">Campaign website ↗</a>')
 (ROOT/'candidates'/f'{slug}.html').write_text(page)



def build_challenger(slug):
 """Render Senate challengers without transferring an opponent's office records."""
 chamber='house' if slug=='jennifer-p-nerbonne' else 'senate'
 configs={
  'jennifer-p-nerbonne':('Jennifer P Nerbonne',35,'REP','South Kingstown','jen.nerbonne@gmail.com','(401) 862-0251','https://jennerbonne.com/','https://jennerbonne.com/','Nerbonne is the Republican candidate for House District 35. Her campaign positions appear below, attributed to her published campaign website.'),
  'james-p-pierson':('James P Pierson',33,'REP','Coventry, West Greenwich','jamespierson.ri@gmail.com','(401) 237-0363','https://www.jamespiersonri.com/','https://www.jamespiersonri.com/about-james','Pierson’s campaign biography describes his twelve years on the Coventry School Committee, including service as chairman. He is seeking election to the State Senate.'),
  'samantha-r-wilcox':('Samantha R Wilcox',34,'DEM','Hopkinton, Charlestown, Exeter, Richmond, West Greenwich','samwilcoxri@gmail.com','(401) 644-9789','https://samwilcoxforri.com/','https://samwilcoxforri.com/','Wilcox’s campaign identifies her as Richmond Town Council President. She is seeking election to the State Senate. Municipal service is separate from the General Assembly records presented for incumbent senators.')}
 name,district,party,community,email,phone,website,bio,about=configs[slug]
 candidate_id=f'{chamber}-{district}-{party.lower()}-primary-{slug}'
 party_label='Republican' if party=='REP' else 'Democratic'
 page=(ROOT/'candidates/nelly-burdette.html').read_text().replace('Nelly Burdette',name).replace('nelly-burdette',slug).replace('District 17',f'District {district}').replace('district=17',f'district={district}').replace('Lincoln, North Smithfield, North Providence',community).replace('Democratic',party_label)
 page=re.sub(r'<p class="photo-note">.*?</p>',f'<p class="photo-note">Portrait: <a href="{esc(website)}">Official campaign website ↗</a></p>',page)
 portrait=next(x for x in load('candidate_portrait_sources_2026') if x['slug']==slug)
 page=re.sub(r'(class="portrait"[^>]*?)width="[0-9]+" height="[0-9]+"',lambda m:m[1]+f'width="{portrait["width"]}" height="{portrait["height"]}"',page)
 research=next(r for r in load('candidate_research_2026_with_endorsements')['candidates'] if r['candidate_id']==candidate_id)
 supplied=next((r for r in load('candidate_profiles_2026')['profiles'] if r['candidate_id']==candidate_id),{})
 def replace(id,title,body):
  nonlocal page
  page=replace_section(page,id,section(id,title,body))
 replace('about','About this candidate',f'<p class="intro">{party_label} candidate for Senate District {district} · {esc(community)}.</p><div class="grid2"><div class="mini"><h3>At a glance</h3><p>{esc(about)}</p></div><div class="mini"><h3>How to read this page</h3><p>Campaign statements, election returns, finance and endorsements are labeled by source and period. A Senate challenger’s lack of a General Assembly record is not a score of zero.</p></div></div><p class="source">'+link(bio,'Official campaign biography ↗')+'</p>')
 priorities=supplied.get('priorities') or research['priorities']
 source=esc(supplied.get('source_note','Campaign response submitted directly to RIEP.')) if supplied.get('priorities') else link(website,'Official campaign website ↗')
 replace('priorities','Campaign priorities','<div class="grid2">'+''.join('<div class="mini"><h3>'+esc(p['title'])+'</h3><p>'+esc(p['summary'])+'</p></div>' for p in priorities)+'</div><p class="source">'+source+' · Campaign positions, not RIEP assessments.</p>')
 elections=[]
 for r in sorted(load('race_data').values(),key=lambda r:int(r['year']),reverse=True):
  if r['chamber'].lower()==chamber and int(r['district_number'])==district:
   for c in r['candidates']:
    if name.split()[-1].lower() in c['name'].lower():
     url=f'/map.html?mode=results&chamber=senate&year={r["year"]}&view=party&district={district}'
     elections.append(f'<div class="election"><a class="year election-link" href="{esc(url)}">{r["year"]}</a><div><strong>{esc(c["role"])} · {esc(c["votes"])} votes</strong><small>Districtwide general election</small></div><span class="result">{esc(c["pct"])}</span></div>')
 intro='Districtwide State Senate general-election returns. Select a year to view RIEP’s results map. The 2026 general election has not occurred.' if elections else 'No earlier State Senate general-election result is recorded for this candidate in RIEP’s historical dataset. The 2026 general election has not occurred. Municipal service is described separately above.'
 replace('elections','Past electoral performance','<p class="intro">'+intro+'</p><div class="timeline">'+''.join(elections)+'</div>'+f'<a class="score-comparison-link" href="/map.html?mode=results&amp;chamber=senate&amp;year=2024&amp;view=party&amp;district={district}">Explore District {district} historical general-election results →</a><p class="source">District history is separate from this candidate’s individual electoral record.</p>')
 entries=load('candidate_profile_primary_returns_2026')[slug]
 replace('primaries',party_label+' primary history',f'<p class="intro">Senate District {district} · Select a year or vote share to view this primary result.</p><div class="timeline">'+''.join(f'<div class="election"><a class="year election-link" href="{esc(e["source_url"])}">{e["year"]}</a><div><strong>Advanced · {e["votes"]:,} votes</strong><small>{"Uncontested" if e["uncontested"] else "Contested"} {party_label} primary · Official results</small></div><a class="result election-link" href="{esc(e["source_url"])}">{esc(e["share"])}</a></div>' for e in entries)+'</div><p class="source">Official Rhode Island Board of Elections returns. An uncontested 100% is the share of named-candidate votes, excluding undervotes. Additional earlier years are under construction.</p>')
 if not entries:
  replace('primaries',party_label+' primary history','<p class="intro">Primary returns are under construction. No primary vote total is assigned from a different race.</p><p class="source"><a href="https://electionresults.ri.gov/results/public/rhodeisland/elections/RI2026StatewidePrimary">Official 2026 Board of Elections results ↗</a></p>')
 fin=next(r for r in load('candidate_finance_2026')['profiles'] if r['slug']==slug)
 replace('finance','Campaign finance snapshot',f'<p class="intro">{esc(fin["report_label"])} · {esc(fin["reporting_period_label"])}.</p>'+metrics([(label,f'${fin[k]:,.2f}') for label,k in [('Raised during period','money_raised'),('Spent during period','money_spent'),('Cash at period end','ending_cash')]]).replace('record-grid','metric-grid')+f'<a class="finance-profile-button" href="/finance.html?slug={slug}">View {esc(name)}’s campaign finance →</a>')
 replace('record','Record in office','<div class="empty"><strong>General Assembly record not applicable · Senate challenger</strong><p>This candidate does not have a Rhode Island General Assembly service record in RIEP’s current dataset. General Assembly sponsorship counts and legislative attendance are not assigned. Prior municipal service is described above.</p></div>')
 replace('bills','Bills &amp; votes','<p class="intro">No Rhode Island General Assembly sponsored-bill or roll-call record is attributed to this candidate in this dataset. Campaign positions appear above.</p>')
 replace('ratings','Outside ratings &amp; scorecards','<p class="intro">Legislative-effectiveness scores and the experimental RIEP index are not applicable to this Senate challenger. No incumbent’s record or district-level score is transferred to this candidate.</p>')
 endorsements=research['endorsements']
 replace('endorsements','Endorsements','<p class="intro">'+('Published endorsements from outside organizations. Select an organization to view its source.' if endorsements else 'No published endorsements are currently recorded for this candidate in RIEP’s research. Additional endorsements will be added after verification.')+'</p>'+''.join(f'<div class="endorsement-entry"><a class="endorsement-chip" href="{esc(e["source_url"])}" target="_blank" rel="noopener">{esc(e["endorser"])} ↗</a><p class="endorsement-period">2026 election · Senate District {district}</p></div>' for e in endorsements)+'<p class="source">Outside endorsements, not RIEP endorsements.</p>')
 replace('sources','Under construction','<p class="intro">This candidate profile is still under construction. Further election history, campaign information and digital-footprint research will be added after verification.</p>')
 replace('contact','Contact &amp; district','<dl class="details">'+''.join(f'<div><dt>{label}</dt><dd>{value}</dd></div>' for label,value in [('District',f'Senate District {district}'),('Community',esc(community)),('Campaign phone',link('tel:+1'+re.sub('[^0-9]','',phone),phone)),('Campaign email',link('mailto:'+email,email))])+'</dl>')
 page=page.replace('https://electnelly.com/',website)
 if chamber=='house': page=page.replace('Rhode Island Senate','Rhode Island House').replace('Senate District','House District').replace('State Senate','State House').replace('Senate challenger','House challenger').replace('chamber=senate','chamber=house').replace('Prior municipal service is described above.','').replace('Municipal service is described separately above.','').replace('General Assembly record not applicable · House challenger','General Assembly record not applicable · House challenger')
 (ROOT/'candidates'/f'{slug}.html').write_text(page)

if __name__=='__main__':
 build_burdette()
 for slug in ['james-p-pierson','samantha-r-wilcox']:build_challenger(slug)
