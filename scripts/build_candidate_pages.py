"""Generate reviewed candidate profiles from existing RIEP data (no network)."""
import json, html, re, unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(n): return json.loads((ROOT/'data'/f'{n}.json').read_text())
def esc(v): return html.escape(str(v),quote=True)
def link(url,text): return f'<a href="{esc(url)}">{esc(text)}</a>'
def metrics(items): return '<div class="record-grid">'+''.join(f'<div class="metric"><b>{esc(v)}</b><span>{esc(k)}</span></div>' for k,v in items)+'</div>'
def section(id,title,body): return f'<section class="card" id="{id}"><h2>{title}</h2>{body}</section>'
def details(title,body): return f'<details class="profile-fold"><summary>{esc(title)}</summary><div class="fold-content">{body}</div></details>'
def current_index(record):
 peers=[r for r in load('incumbent_records_2026')['records'] if r['chamber']=='senate']; keys=['prime_sponsored','passed_chamber','became_law']; totals=[sum(r['legislation'][k] for r in peers) for k in keys]
 assert len(peers)==38 and len({r['district_number'] for r in peers})==38
 calc=lambda r:len(peers)/3*sum(r['legislation'][k]/t for k,t in zip(keys,totals))
 score=calc(record); rank=1+sum(calc(p)>score for p in peers)
 return f'<section class="riep-progress"><p class="eyebrow">Experimental RIEP index · 2025–2026</p><h3>Legislative progress index</h3>{metrics([("RIEP index",f"{score:.2f}"),("Senate record rank",f"{rank} / 38")])}<p>Equal weight for lead-sponsored bills, bills passed by the Senate and bills that became law. A score of 1 is the average of the 38 current Senate district records. This is an RIEP calculation, separate from CEL.</p>'+details('Calculation and coverage',f'<p>38 ÷ 3 × ({" + ".join(str(record["legislation"][k])+" ÷ "+str(t) for k,t in zip(keys,totals))}) = {score:.6f}.</p><p>Snapshot updated August 30, 2026. Resolutions and cosponsorship excluded. This current-roster comparison does not include every person who served during the session.</p>')+'</section>'
def candidate_name_matches(candidate_name,result_name):
 tokens=lambda value:re.findall(r"[a-z]+",unicodedata.normalize('NFKD',value.lower()).encode('ascii','ignore').decode())
 candidate=tokens(candidate_name);result=tokens(result_name)
 return bool(candidate and result and candidate[0]==result[0] and candidate[-1]==result[-1])
def build(name,slug,district,community,email,phone,chamber="senate"):
 label="House" if chamber=="house" else "Senate"
 template=(ROOT/'candidates/john-burke.html').read_text(); head=template.split('<body>')[0]; head=head.replace('John Burke',name).replace('Senate District 9',f'{label} District {district}')
 if 'href="candidate-additions.css"' not in head: head=head.replace('</head>','<link rel="stylesheet" href="candidate-additions.css">\n</head>')
 roster=load('whos_running_2026')['chambers'][chamber][str(district)]['candidates']; candidate=next(r for r in roster if r['candidate_id'].endswith('-'+slug)); surname=candidate['last_name']
 rec=next(r for r in load('incumbent_records_2026')['records'] if r['chamber']==chamber and r['candidate_id']==candidate['candidate_id'])
 research=next(r for r in load('candidate_research_2026_with_endorsements')['candidates'] if r['candidate_id']==candidate['candidate_id'])
 supplied=next((r for r in load('candidate_profiles_2026')['profiles'] if r['candidate_id']==candidate['candidate_id']),{})
 fin=next(r for r in load('candidate_finance_2026')['profiles'] if r['slug']==slug)
 # Official RI AFL-CIO 2026 primary endorsement list checked October 2, 2026.
 if district in (7,8): research['endorsements']=[e for e in research['endorsements'] if 'AFL-CIO' not in e['endorser']] + [{'endorser':'Rhode Island AFL-CIO · 2026 primary endorsement','source_url':'https://rhodeislandaflcio.org/candidate-endorsement-applications-2026/'}]
 race=f'/running.html?chamber={chamber}&district={district}&election=general'; finance=f'/finance.html?slug={slug}'
 header=template[template.index('<header'):template.index('<main')]; header=header.replace('<nav aria-label="Site navigation">','<nav aria-label="Site navigation"><a href="/candidate-profiles.html">All profiles</a>'); header=header.replace('John Burke',name).replace('john-burke.png',slug+'.png').replace('john-burke',slug).replace('District 9',f'District {district}').replace('district=9',f'district={district}').replace('West Warwick',community);header=re.sub(r'<span class="tag">2024 general election unopposed</span>','',header);header=header.replace('September 2026','October 5, 2026' if district in (14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,38) else 'October 4, 2026')
 if candidate['party']=='REP': header=header.replace('Democratic','Republican').replace('Democrat','Republican')
 if not (ROOT/'candidates'/f'{slug}.png').exists():
  header=re.sub(r'<div><img class="portrait".*?</div>', '<div class="mini"><h2>Candidate portrait</h2><p>Photo under construction</p></div>',header,flags=re.S)
 body=section('about','About this candidate',f'<p class="intro">{esc(name)} represents Senate District {district} ({esc(community)}). Campaign positions, public records and outside scorecards are shown with their source and reporting period.</p>'+ ('<p>First elected in November 2024; first legislative session: 2025–2026.</p>' if district==8 else '')+f'<p class="source">{link("https://www.rilegislature.gov/senators/"+surname+"/Pages/Biography.aspx","Official General Assembly biography")}</p>')
 priorities=supplied.get('priorities') or research['priorities']
 if slug=='ana-b-quezada':
  prioritybody='<div class="empty"><strong>Campaign priorities not provided</strong><p>As of October 4, 2026, Ana B. Quezada has not responded to RIEP’s written or verbal requests for campaign priorities.</p></div><p class="source">Outreach status reported by RIEP. This section will be updated if a response is received.</p>'
 elif slug=='jessica-de-la-cruz' and not priorities:
  prioritybody='<div class="empty"><strong>Campaign priorities under construction</strong><p>De la Cruz’s campaign website was checked on October 5, 2026, but its domain is not currently connected to a website. Campaign priorities will be added when an accessible campaign source can be verified.</p></div>'
 elif not priorities:
  prioritybody='<div class="empty"><strong>Campaign priorities under construction</strong><p>No campaign priorities are currently recorded for this candidate in RIEP’s research. This section will be updated after verification.</p></div>'
 else:
  sources={(p.get('source_url'),p.get('source_label','Priority source')) for p in priorities if p.get('source_url')}
  prioritybody='<div class="grid2">'+''.join(f'<div class="mini"><h3>{esc(p["title"])}</h3><p>{esc(p["summary"])}</p></div>' for p in priorities)+'</div>'
  prioritybody+=('<p class="source">'+esc(supplied.get('source_note','Campaign response submitted directly to RIEP.'))+'</p>' if supplied.get('priorities') else '<p class="source">'+ ' · '.join(link(url,label) for url,label in sorted(sources)) +'. Summaries attributed to the sources shown.</p>')
 body+=section('priorities','Campaign priorities',prioritybody)
 elections=[]
 for r in sorted(load('race_data').values(),key=lambda r:int(r['year']),reverse=True):
  if r['chamber'].lower()==chamber and int(r['district_number'])==district:
   for c in r['candidates']:
    if candidate_name_matches(name,c["name"]):
     url=f"/map.html?mode=results&chamber={chamber}&year={r['year']}&view=party&district={district}"
     elections.append(f'<div class="election"><a class="year election-link" href="{esc(url)}" aria-label="View {r["year"]} Senate District {district} general election results">{r["year"]}</a><div><strong>{esc(c["role"])} · {esc(c["votes"])} votes</strong><small>Districtwide general election</small></div><span class="result">{esc(c["pct"])}</span></div>')
 body+=section('elections','Past electoral performance','<p class="intro">Districtwide general election results. Select a year to open RIEP’s results map.</p><div class="timeline">'+''.join(elections)+'</div>')
 primary=[]
 for r in load('primary_results_2026')['races']:
  if r['chamber']==chamber and r['district']==district:
   for c in r['candidates']:
    if name.split()[-1].lower() in c['name'].lower(): primary.append(f'<p><strong>2026 · {c["votes"]:,} votes · {c["pct"]}%</strong></p>')
 if district==7:
  primary.extend(['<p><strong>2024 · 548 votes · 100%</strong> · Uncontested</p><p class="source"><a href="https://www.ri.gov/election/results/2024/statewide_primary/races/59.html">Official 2024 primary returns</a></p>', '<p><strong>2020 · 973 votes · 100%</strong> · Uncontested</p><p class="source"><a href="https://www.ri.gov/election/results/2020/statewide_primary/races/309.html">Official 2020 primary returns</a></p>'])
 body+=section('primaries','Democratic primary history',''.join(primary)+('<p>2026 figures are the project’s unofficial September 10 snapshot.</p>' if district==8 else '<p>2026 and 2022 primary returns are under construction. An uncontested 100% is the share of votes for named candidates, excluding undervotes.</p>')+f'<p>{link("/primary-results.html", "Explore RIEP primary results →")}</p>')
 body+=section('finance','Campaign finance snapshot',f'<p class="intro">{esc(fin["report_label"])} · {esc(fin["reporting_period_label"])}. Figures describe this reporting period.</p>'+metrics([(label,f'${fin[k]:,.2f}') for label,k in [('Raised during period','money_raised'),('Spent during period','money_spent'),('Cash at period end','ending_cash')]])+f'<a class="finance-profile-button" href="{esc(finance)}">View {esc(name)}’s campaign finance →</a>')
 counts=rec['legislation']; attendance=rec.get('attendance',{}); body+=section('record','Record in office · 2025–2026 General Assembly',metrics([(label,counts[k]) for label,k in [('Lead-sponsored bills','prime_sponsored'),('Bills cosponsored','cosponsored'),('Lead bills passed chamber','passed_chamber'),('Lead bills became law','became_law')]])+'<h3>Session attendance</h3>'+metrics([(label,(str(attendance[k]).removesuffix('.0')+'%' if k=='attendance_rate_pct' and k in attendance else attendance.get(k,'Not available'))) for label,k in [('Sessions eligible','sessions_eligible'),('Sessions present','sessions_present'),('Sessions absent','sessions_absent'),('Attendance rate','attendance_rate_pct')]])+'<p class="source">Presence recorded in official Senate Journals. “Not Voting” on a floor vote is not treated as an absence. Attendance rate is a percentage.</p><p><strong>Leadership:</strong> '+esc(' · '.join(rec['leadership']) or 'No leadership role listed')+'</p><p><strong>Committees:</strong> '+esc(' · '.join(c['name']+(' — '+c['role'] if c.get('role') else '') for c in rec['committees']))+'</p><p class="source">'+link(rec['sources'][0],'Official committee roster')+' · Dataset updated August 30, 2026.</p>')
 bills=rec['legislation_detail']; passed={(x['year'],x['bill']) for x in bills['passed_chamber']}; laws={(x['year'],x['bill']) for x in bills['became_law']}
 billbody='<div class="bill-scroll" tabindex="0" aria-label="Lead-sponsored bill records"><table><thead><tr><th>Year</th><th>Bill</th><th>Progress</th></tr></thead><tbody>'+''.join(f'<tr><td>{b["year"]}</td><td>{esc(b["bill"])}</td><td>{"Became law" if (b["year"],b["bill"]) in laws else "Passed Senate" if (b["year"],b["bill"]) in passed else "Introduced"}</td></tr>' for b in bills['lead_sponsored'])+'</tbody></table></div>'
 body+=section('bills','Bills &amp; votes',details('Lead-sponsored records · 2025–2026',billbody)+'<p class="source">Official Bill Status/History records in RIEP’s August 30 snapshot. Individual floor-vote records are under construction; advocacy-selected votes appear under scorecards.</p>')
 ratings=[r for r in load('outside_ratings_2026')['ratings'] if r['chamber']==chamber and r['district_number']==district]; ratingbody=''
 for r in ratings:
  ratingbody+=f'<section class="mini"><h3>{esc(r["organization"])}</h3><p><strong>{esc(r["rating"])}</strong> · {esc(r["year"])}</p><p>{esc(r["measure"])}</p>'
  if r.get('bills'):
   ratingbody+=metrics([(k.replace('_',' ').capitalize(),v) for k,v in r['bills'].items()])+details('Full CEL categories and historical scores','<div class="table-scroll"><table><thead><tr><th>Category</th><th>Introduced</th><th>Committee</th><th>Beyond committee</th><th>Passed</th><th>Law</th></tr></thead><tbody>'+''.join('<tr><td>'+esc(c['label'])+'</td>'+''.join(f'<td>{c[k]}</td>' for k in ['introduced','committee_action','beyond_committee','passed_chamber','became_law'])+'</tr>' for c in r['bill_categories'])+'</tbody></table></div><p>Expected benchmark: '+str(r['benchmark'])+f' · {esc(r["expectation"])} · Party rank {r["party_rank"]} of {r["party_total"]} {esc(r["comparison_group"])}.</p>'+''.join(f'<p>{esc(h["term"])}: {h["score"]:.2f} · Party rank {esc(h["rank"])}</p>' for h in r['history']))
  if r.get('votes'): ratingbody+=details('View 11 individual ACLU-selected votes','<ul>'+''.join(f'<li>{esc(v["issue"])}: {esc(v["status"])}</li>' for v in r['votes'])+'</ul>')
  ratingbody+=f'<p class="source">{esc(r.get("note",""))}</p><p>{link(r["source_url"],"Source report ↗")}</p></section>'
  if r['organization']=='Center for Effective Lawmaking': ratingbody+=current_index(rec)
 if not any(r['organization']=='Center for Effective Lawmaking' for r in ratings): ratingbody= '<p>No 2023–2024 CEL score is available in the project dataset for this candidate.</p>'+current_index(rec)+ratingbody
 body+=section('ratings','Legislative scores &amp; voting records',ratingbody+'<p class="source">RIEP does not combine outside ratings into an overall candidate score. Organizations select different issues and methodologies.</p>')
 body+=section('endorsements','Endorsements',''.join('<div class="mini"><h3>'+esc(e['endorser'])+'</h3><p>'+link(e['source_url'],'View endorsement source ↗')+'</p></div>' for e in research['endorsements'])+'<p class="source">Entries from the project’s endorsement research; a linked voter guide is labeled by its source and is not an RIEP endorsement.</p>')
 body+=section('sources','Under construction','<p>Additional bill summaries, floor votes, earlier primary results and digital footprint research will be added after review.</p>')
 aside=f'<aside class="side"><section class="card"><h2>Contact &amp; district</h2><p>Senate District {district} · {esc(community)}</p><p>{link("mailto:"+email,email)}</p><p>{link("tel:"+re.sub(r"[^+0-9]","",phone),phone)}</p></section><section class="card"><h2>Explore more</h2><div class="linklist">{link(race,"Race & opponents →")}{link(finance,"Campaign finance →")}{link("legislative-comparison.html","2023–2024 score comparison →")}</div></section></aside>'
 out=head+'<body>'+header+'<main class="shell"><div class="layout"><div class="stack">'+body+'</div>'+aside+'</div></main><footer class="footer"><div class="shell">Rhode Island Elections Project · Source dates and reporting periods shown by section.</div></footer></body></html>'
 if chamber=='house': out=out.replace('Rhode Island Senate','Rhode Island House').replace('Senate District','House District').replace('Passed Senate','Passed House').replace('Senate Journals','House Journals').replace('/senators/','/representatives/')
 (ROOT/'candidates'/f'{slug}.html').write_text(out)
NEW_PROFILES = [('Tiara T Mack','tiara-t-mack',6,'Providence','tiaramackri@gmail.com','(401) 288-1288'),('Samuel W Bell','samuel-w-bell',5,'Providence','swbell11@gmail.com','(301) 351-6650'),('Stefano V Famiglietti','stefano-v-famiglietti',4,'North Providence','sfamiglietti@yahoo.com','(401) 215-3462')]
NEW_PROFILES += [('Samuel D Zurier','samuel-d-zurier',3,'Providence','sen-zurier@rilegislature.gov','(401) 644-0925'),('Ana B Quezada','ana-b-quezada',2,'Providence','sen-quezada@rilegislature.gov','(401) 255-0345'),('Jacob Bissaillon','jacob-bissaillon',1,'Providence','sen-bissaillon@rilegislature.gov','(401) 276-5563')]
NEW_PROFILES += [('Walter S Felag Jr','walter-s-felag-jr',10,'Warren, Bristol, Tiverton','sen-felag@rilegislature.gov','(401) 245-7521'),('Linda L Ujifusa','linda-l-ujifusa',11,'Portsmouth, Bristol','sen-ujifusa@rilegislature.gov','(401) 472-4721'),('Louis DiPalma','louis-dipalma',12,'Middletown, Little Compton, Newport, Tiverton','sen-dipalma@rilegislature.gov','(401) 847-8540'),('Dawn Euer','dawn-euer',13,'Newport, Jamestown','sen-euer@rilegislature.gov','(401) 276-5589')]
NEW_PROFILES += [('Valarie Jean Lawson', 'valarie-jean-lawson', 14, 'East Providence', 'sen-lawson@rilegislature.gov', '(401) 222-4901'), ('Meghan E Kallman', 'meghan-e-kallman', 15, 'Pawtucket, Providence', 'sen-kallman@rilegislature.gov', '(401) 648-9422'), ('Jonathon Acosta', 'jonathon-acosta', 16, 'Central Falls, Pawtucket', 'sen-acosta@rilegislature.gov', '(401) 305-0545')]
NEW_PROFILES += [('Robert Britto', 'robert-britto', 18, 'East Providence, Pawtucket', 'sen-britto@rilegislature.gov', '(401) 447-4226'), ('Ryan W Pearson', 'ryan-w-pearson', 19, 'Cumberland, Lincoln', 'sen-pearson@rilegislature.gov', '(401) 276-5535'), ('Brian J Thompson', 'brian-j-thompson', 20, 'Woonsocket, Cumberland', 'sen-thompson@rilegislature.gov', '(401) 276-5568')]
NEW_PROFILES += [('Gordon E Rogers', 'gordon-e-rogers', 21, 'Foster, Coventry, Scituate, West Greenwich', 'sen-rogers@rilegislature.gov', '(401) 222-2708'), ('David P Tikoian', 'david-p-tikoian', 22, 'Smithfield, North Providence, Lincoln', 'sen-tikoian@rilegislature.gov', '(401) 276-5563'), ('Jessica de la Cruz', 'jessica-de-la-cruz', 23, 'North Smithfield, Burrillville, Glocester', 'sen-delacruz@rilegislature.gov', '(401) 484-0155')]
NEW_PROFILES += [('Melissa Murray', 'melissa-murray', 24, 'Woonsocket, North Smithfield', 'sen-murray@rilegislature.gov', '(401) 276-5568'), ('Andrew R Dimitri', 'andrew-r-dimitri', 25, 'Johnston', 'sen-dimitri@rilegislature.gov', '(401) 276-5563'), ('Todd M Patalano', 'todd-m-patalano', 26, 'Cranston', 'sen-patalano@rilegislature.gov', '(401) 276-5592'), ('Hanna M Gallo', 'hanna-m-gallo', 27, 'Cranston, West Warwick', 'sen-gallo@rilegislature.gov', '(401) 222-4901')]
NEW_PROFILES += [('Lammis J Vargas', 'lammis-j-vargas', 28, 'Cranston, Providence', 'sen-vargas@rilegislature.gov', '(401) 276-5584'), ('Peter A Appollonio Jr', 'peter-a-appollonio-jr', 29, 'Warwick', 'sen-appollonio@rilegislature.gov', '(401) 276-5589'), ('Mark McKenney', 'mark-mckenney', 30, 'Warwick', 'sen-mckenney@rilegislature.gov', '(401) 578-6258'), ('Matthew L LaMountain', 'matthew-l-lamountain', 31, 'Warwick, Cranston', 'sen-lamountain@rilegislature.gov', '(401) 206-0822'), ('Thomas J Paolino', 'thomas-j-paolino', 17, 'Lincoln, North Smithfield, North Providence', 'sen-paolino@rilegislature.gov', '(401) 222-2708')]
NEW_PROFILES += [('Pamela J Lauria', 'pamela-j-lauria', 32, 'Barrington, Bristol, East Providence', 'sen-lauria@rilegislature.gov', '(401) 431-0013'), ('Leonidas Peter Raptakis', 'leonidas-peter-raptakis', 33, 'Coventry, West Greenwich', 'sen-raptakis@rilegislature.gov', '(401) 276-5567'), ('Elaine J Morgan', 'elaine-j-morgan', 34, 'Hopkinton, Charlestown, Exeter, Richmond, West Greenwich', 'sen-morgan@rilegislature.gov', '(401) 222-2708'), ('Bridget G Valverde', 'bridget-g-valverde', 35, 'North Kingstown, East Greenwich, South Kingstown', 'sen-valverde@rilegislature.gov', '(401) 276-5561')]
NEW_PROFILES += [('Alana M DiMario', 'alana-m-dimario', 36, 'Narragansett, North Kingstown, New Shoreham', 'sen-dimario@rilegislature.gov', '(401) 276-5568'), ('Victoria Gu', 'victoria-gu', 38, 'Charlestown, Westerly, South Kingstown', 'sen-gu@rilegislature.gov', '(401) 388-0696')]
if __name__=='__main__':
 build('Lori Urso','lori-urso',8,'Pawtucket','sen-urso@rilegislature.gov','(401) 276-5567')
 build('Frank A Ciccone','frank-a-ciccone',7,'Providence, Johnston','sen-ciccone@rilegislature.gov','(401) 276-5579')

if __name__ == "__main__":
 from candidate_profile_components import harmonize
 for slug in ["lori-urso", "frank-a-ciccone"]: harmonize(slug)

if __name__ == '__main__':
 for name,slug,district,community,email,phone in NEW_PROFILES:
  build(name,slug,district,community,email,phone)
  harmonize(slug)

if __name__ == '__main__':
 from build_challenger_pages import build_burdette, build_challenger
 build_burdette()
 build_challenger("james-p-pierson")
 build_challenger("samantha-r-wilcox")

if __name__ == "__main__":
 import runpy
 runpy.run_path(str(ROOT / "scripts/build_south_kingstown_profiles.py"))
