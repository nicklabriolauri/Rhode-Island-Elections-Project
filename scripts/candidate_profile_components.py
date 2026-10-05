"""Use Burke's presentation components for all generated candidate profiles."""
import json,re,html
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def esc(v):return html.escape(str(v),quote=True)
def load(n):return json.loads((ROOT/'data'/f'{n}.json').read_text())
def section(id,title,body):return f'<section class="card" id="{id}"><h2>{title}</h2>{body}</section>'
def replace_section(page,id,replacement):
 start=re.search(r'<section\b[^>]*\bid="'+re.escape(id)+r'"[^>]*>',page)
 assert start,id
 depth=0
 for tag in re.finditer(r'</?section\b[^>]*>',page[start.start():]):
  depth+=-1 if tag.group().startswith('</') else 1
  if depth==0:return page[:start.start()]+replacement+page[start.start()+tag.end():]
 raise ValueError('Unclosed section '+id)
def metrics(items,cls='record-grid'):
 return f'<div class="{cls}">'+''.join(f'<div class="metric"><b>{esc(value)}</b><span>{esc(label)}</span></div>' for label,value in items)+'</div>'
def bill_sections(rec,slug):
 name=rec['candidate_name'];payload_names={'lori-urso':'lori_urso_supplied_records_2026','frank-a-ciccone':'frank_a_ciccone_supplied_records_2026'};payload=load(payload_names[slug]) if slug in payload_names else None
 body=f'<p class="intro">{esc(name)}’s {rec["legislation"]["prime_sponsored"]} lead-sponsored bills in the 2025–2026 General Assembly, from RIEP’s official-source research. Passage and law status reflect the recorded snapshot; “Not recorded” does not describe the current disposition of a bill.</p>'
 if payload:
  bills=payload['sponsored_bills'];body+=f'<details class="bill-records bill-foldout"><summary>Sponsored bills &amp; resolutions · 2026 <span class="foldout-count">{len(bills)} records</span></summary><p class="intro">{len(bills)} records from the supplied sponsored-bill list. This broader list is separate from the lead-sponsored totals below; sponsor roles have not been independently verified for each entry. Status labels are preserved from the supplied snapshot and may change.</p><p id="sponsored-scroll-help" class="source">Scroll within the list to browse all records. Open a bill summary for its full description.</p><div class="sponsored-bills-scroll" role="region" aria-label="{len(bills)} sponsored bills and resolutions" aria-describedby="sponsored-scroll-help" tabindex="0">'
  body+='\n'.join(f'<article class="sponsored-bill"><div class="sponsored-bill-heading"><h4>{esc(b["Bill"])}</h4><span>{esc(b["Progress"])}</span></div><h5>{esc(b["Bill Name"])}</h5><details><summary>Read bill summary</summary><p>{esc(b["Summary"])}</p></details></article>' for b in bills)
  body+='</div><p class="source">Source: supplied sponsored-bill snapshot, received October 2, 2026. Includes bills and resolutions; sponsor roles are not separated.</p></details>'
 detail=rec['legislation_detail'];passed={(x['year'],x['bill']) for x in detail['passed_chamber']};law={(x['year'],x['bill']) for x in detail['became_law']}
 body+=f'<details class="bill-records bill-foldout"><summary>Lead-sponsored records · 2025–2026 <span class="foldout-count">{len(detail["lead_sponsored"])} records</span></summary><div class="table-scroll"><table class="bill-table"><thead><tr><th scope="col">Bill</th><th scope="col">Year</th><th scope="col">Passed chamber</th><th scope="col">Became law</th></tr></thead><tbody>'
 body+=''.join(f'<tr><th scope="row">{esc(b["bill"])}</th><td>{b["year"]}</td><td>{"Yes" if (b["year"],b["bill"]) in passed else "Not recorded"}</td><td>{"Yes" if (b["year"],b["bill"]) in law else "Not recorded"}</td></tr>' for b in detail['lead_sponsored'])
 body+='</tbody></table></div><p class="source">Source: RIEP research using Rhode Island General Assembly bill-status records, August 30, 2026 snapshot.</p></details>'
 if payload:
  votes=payload['votes'];counts={v:sum(x['vote']==v for x in votes) for v in sorted({x['vote'] for x in votes})};counts_text=' and '.join(f'{n} {v}' for v,n in counts.items())
  body+=f'<details class="bill-records bill-foldout"><summary>Individual votes · June 10–11, 2026 <span class="foldout-count">{len(votes)} records</span></summary><p class="intro">{len(votes)} vote records from the supplied snapshot: {esc(counts_text)}. These records cover June 10–11, 2026; they are not a complete session voting history. Committee votes and floor votes are shown separately, including multiple votes on the same bill.</p><p id="vote-scroll-help" class="source">Scroll within the table to browse all votes. On smaller screens, scroll sideways to view the motion, date and vote.</p><div class="vote-records-scroll" role="region" aria-label="{esc(name)} vote records for June 10–11, 2026" aria-describedby="vote-scroll-help" tabindex="0"><table class="vote-records-table"><caption>{esc(name)} · {len(votes)} supplied vote records</caption><thead><tr><th scope="col">Bill</th><th scope="col">Description</th><th scope="col">Motion / committee</th><th scope="col">Date</th><th scope="col">{esc(name.split()[-1])}’s vote</th></tr></thead><tbody>'
  body+='\n'.join(f'<tr><th scope="row">{esc(v["bill"])}</th><td>{esc(v["description"])}</td><td>{esc(v["motion"])}</td><td><time datetime="{v['date'][-4:]}-{v['date'][:2]}-{v['date'][3:5]}">{esc(v["date"])}</time></td><td class="vote-position">{esc(v["vote"])}</td></tr>' for v in votes)
  body+='</tbody></table></div><p class="source">Source: supplied vote-record snapshot, received October 2, 2026. Records have not been independently verified. Additional dates are under construction.</p></details>'
 return section('bills','Bills &amp; votes',body+billtrack_sections(slug))
def billtrack_sections(slug):
 path=ROOT/'data'/f'{slug.replace("-","_")}_billtrack50_2026.json'
 if not path.exists():return ''
 data=json.loads(path.read_text());bills=data['sponsored_bills'];votes=data['votes']
 dates=sorted({v['date'] for v in votes});period='June 11, 2026' if len(dates)==1 else 'June 10–11, 2026'
 body=f'<details class="bill-records bill-foldout"><summary>Sponsored bills &amp; resolutions · 2026 <span class="foldout-count">{len(bills)} records</span></summary><p class="intro">The sponsored entries displayed by BillTrack50 include bills and resolutions. Lead sponsorship and cosponsorship are not separated in this list; it is distinct from the official-source lead-sponsored records above.</p><div class="sponsored-bills-scroll" role="region" aria-label="Sponsored bills and resolutions" tabindex="0">'
 body+=''.join(f'<article class="sponsored-bill"><div class="sponsored-bill-heading"><h4>{esc(b["bill"])}</h4><span>{esc(b["status"])}</span></div><h5>{esc(b["title"])}</h5>'+ (f'<details><summary>Read bill summary</summary><p>{esc(b["summary"])}</p></details>' if b.get('summary') else '')+'</article>' for b in bills)
 body+='</div><p class="source">Source: BillTrack50 public legislator table, captured October 4, 2026. Status labels reflect that snapshot.'+(' Full summaries supplied in the October 4 attachment; sponsored entries and votes were checked against the matching public-table extraction.' if data.get('attachment_verification') else '')+'</p></details>'
 body+=f'<details class="bill-records bill-foldout"><summary>Individual votes · {period} <span class="foldout-count">{len(votes)} records</span></summary><p class="intro">The 100 records displayed in BillTrack50’s public vote table. This is a limited snapshot, not a complete session voting history. Committee and floor motions remain separate; repeated bill numbers can represent separate votes.</p><div class="vote-records-scroll" role="region" aria-label="Individual vote records" tabindex="0"><table class="vote-records-table"><caption>Individual votes · {period}</caption><thead><tr><th scope="col">Bill</th><th scope="col">Description</th><th scope="col">Motion / committee</th><th scope="col">Date</th><th scope="col">Vote</th></tr></thead><tbody>'
 for v in votes:
  month,day,year=v['date'].split('/')
  body+=f'<tr><th scope="row">{esc(v["bill"])}</th><td>{esc(v["description"])}</td><td>{esc(v["motion"])}</td><td><time datetime="{year}-{month}-{day}">{esc(v["date"])}</time></td><td class="vote-position">{esc(v["vote"])}</td></tr>'
 return body+'</tbody></table></div><p class="source">Source: BillTrack50 public legislator table, captured October 4, 2026. Further dates are under construction.</p></details>'
def expectation_explainer(cel):
 return '<p class="score-context">The party rank compares this legislator with other members of the same party in the same chamber. CEL’s expectations label uses a separate benchmark that accounts for party status, seniority and committee leadership. “Meets Expectations” means a score between 50% and 150% of that benchmark; it does not mean an average party rank. <a href="'+esc(cel['glossary_url'])+'">How CEL defines expectations ↗</a></p>'
def current_index(rec):
 peers=[r for r in load('incumbent_records_2026')['records'] if r['chamber']=='senate'];keys=['prime_sponsored','passed_chamber','became_law'];totals=[sum(r['legislation'][k] for r in peers) for k in keys]
 assert len(peers)==38 and len({r['district_number'] for r in peers})==38
 calculate=lambda r:38/3*sum(r['legislation'][k]/t for k,t in zip(keys,totals));score=calculate(rec);rank=1+sum(calculate(r)>score for r in peers)
 roster=load('whos_running_2026')['chambers']['senate']
 parties={c['candidate_id']:c['party'] for district in roster.values() for c in district['candidates']}
 party=parties[rec['candidate_id']];party_peers=[r for r in peers if parties.get(r['candidate_id'])==party]
 party_rank=1+sum(calculate(r)>score for r in party_peers);party_label={'DEM':'Democrats','REP':'Republicans'}.get(party,party)
 average_label='Above Senate average' if score>1+1e-12 else 'Below Senate average' if score<1-1e-12 else 'At Senate average'
 tags=f'<p class="lawmaker-tags"><span>#{party_rank} of {len(party_peers)} Senate {esc(party_label)}</span><span>{average_label}</span></p>'
 context='<div class="score-context"><h4>Why RIEP publishes a current-session index</h4><p>CEL’s Legislative Effectiveness Score is our research benchmark. The CEL data presented here cover 2023–2024 and have not been extended to the 2025–2026 session. RIEP’s provisional index provides a current-session view of bill sponsorship and advancement while that historical score remains available for context.</p><p>RIEP uses three equally weighted stages and a Senate average of 1. It does not reproduce CEL’s five-stage method, bill-significance weights or expected-performance model. “Above” or “below Senate average” describes this index only; it is not a CEL expectations label.</p><a class="score-comparison-link" href="legislative-comparison.html">Compare RIEP and CEL scores for the same 2023–2024 session →</a></div>'
 counts=rec['legislation'];formula=' + '.join(f'{counts[k]} ÷ {t}' for k,t in zip(keys,totals));surname=rec['candidate_name'].split()[-1]
 return f'<section class="riep-progress" id="riep-legislative-index" aria-labelledby="riep-progress-title"><div class="lawmaker-head"><div><span class="eyebrow">Experimental RIEP calculation · 2025–2026</span><h3 id="riep-progress-title">Three-stage legislative progress index</h3></div><div class="lawmaker-score"><strong>{score:.2f}</strong><small>#{rank} of 38 Senate district records</small></div></div>{tags}{context}<p class="intro">Lead-sponsored bills, bills passed by the Senate, and bills that became law, compared with all 38 Senate district records. A score of 1 represents the comparison-set average.</p><div class="riep-progress-metrics">'+''.join(f'<div><strong>{counts[k]}</strong><span>{label}</span></div>' for k,label in zip(keys,['Lead-sponsored','Passed Senate','Became law']))+f'</div><details><summary>View calculation and methodology</summary><p>Each stage receives equal weight. Divide {esc(surname)}’s count at each stage by the corresponding Senate total, average the three shares, and multiply by 38. Rank uses unrounded scores; equal scores share a rank. Bills that become law contribute at each stage they reach. Cosponsored bills and resolutions are excluded.</p><p>38 ÷ 3 × ({formula}) = {score:.6f}.</p><p>Dataset updated: August 30, 2026. Counts reflect this dataset, not a live legislative feed.</p><p><strong>Prototype only.</strong> This is a separate RIEP progress index, not an update to the Center for Effective Lawmaking’s score or an overall assessment of a legislator. It does not include committee-action stages or bill-significance weights. It uses existing district records rather than every legislator who served during the term.</p></details><p class="source">Underlying bill records: <a href="https://status.rilegislature.gov/" target="_blank" rel="noopener">Official Rhode Island Bill Status/History ↗</a></p></section>'
def ratings(rec):
 name=rec['candidate_name'];rows=[r for r in load('outside_ratings_2026')['ratings'] if r['chamber']=='senate' and r['district_number']==rec['district_number']];cel=next((r for r in rows if r['organization']=='Center for Effective Lawmaking'),None)
 body='<p class="intro">Each organization uses its own methodology. RIEP does not combine these into an overall candidate score.</p>'
 if cel:
  stages=['introduced','committee_action','beyond_committee','passed_chamber','became_law'];labels=['Bills introduced','Committee action','Beyond committee','Passed chamber','Became law']
  body+=f'<div class="lawmaker"><div class="lawmaker-head"><div><span class="eyebrow">Legislative effectiveness · 2023–2024</span><h3>Center for Effective Lawmaking</h3></div><div class="lawmaker-score"><strong>{esc(cel["rating"])}</strong><small>Expected benchmark: {cel["benchmark"]}</small></div></div><p class="lawmaker-note">Historical score covering the 2023–2024 legislative session. It does not measure {esc(name)}’s 2025–2026 record.</p><p class="lawmaker-tags"><span>{esc(cel["expectation"])}</span><span>#{cel["party_rank"]} of {cel["party_total"]} {esc(cel["comparison_group"])}</span></p>{expectation_explainer(cel)}<div class="lawmaker-grid">'+''.join(f'<div><b>{cel["bills"][k]}</b><span>{label}</span></div>' for k,label in zip(stages,labels))+'</div><details><summary>View full legislative effectiveness details</summary><p>The score weights advancement by bill significance. The expected benchmark accounts for comparable legislators’ party status, seniority and committee leadership.</p><div class="table-scroll"><table class="lawmaker-table"><thead><tr><th>Category</th>'+''.join(f'<th>{l}</th>' for l in labels)+'</tr></thead><tbody>'+''.join('<tr><th>'+esc(c['label'])+'</th>'+''.join(f'<td>{c[k]}</td>' for k in stages)+'</tr>' for c in cel['bill_categories'])+'</tbody></table></div><h4>Historical scores</h4>'+''.join(f'<p>{esc(h["term"])} · {h["score"]:.2f} · Party rank {esc(h["rank"])}</p>' for h in cel['history'])+f'</details><p class="source">Produced by the Center for Effective Lawmaking at the University of Virginia and Vanderbilt University, not by RIEP. <a href="{esc(cel["source_url"])}">Source report ↗</a> · <a href="{esc(cel["methodology_url"])}">Methodology ↗</a> · <a href="{esc(cel["glossary_url"])}">Glossary ↗</a></p></div>'
 else:body+='<div class="lawmaker"><div class="lawmaker-head"><div><span class="eyebrow">Legislative effectiveness · 2023–2024</span><h3>Center for Effective Lawmaking</h3></div></div><p class="lawmaker-note">No 2023–2024 CEL score is available in the project dataset for this candidate.</p><p class="source"><a href="legislative-comparison.html">Explore the 2023–2024 comparison →</a></p></div>'
 body+=current_index(rec)
 for r in rows:
  if r['organization']=='Center for Effective Lawmaking':continue
  aclu=r['organization']=='ACLU of Rhode Island';title='ACLU of Rhode Island' if aclu else 'RI League of Cities and Towns'
  body+=f'<div class="rating-row"><div><strong>{title} · {r["year"]}</strong><small>{esc(r["measure"])}</small>'+('<button class="aclu-vote-trigger" type="button" id="aclu-votes-open" aria-haspopup="dialog" aria-controls="aclu-votes-dialog">View 11 individual votes</button>' if aclu else '')+f'</div><b>{esc(r["rating"])}</b></div>'
  if aclu:
   body+='<p class="aclu-explainer">The ACLU selected these votes to highlight civil-liberties issues. An aligned vote matches its stated position; an opposed vote does not. The selection does not cover every relevant bill or capture committee and floor leadership, so RIEP does not convert it into an overall grade.</p><dialog class="aclu-vote-dialog" id="aclu-votes-dialog" aria-labelledby="aclu-dialog-title"><div class="aclu-dialog-head"><div><h3 id="aclu-dialog-title">ACLU of Rhode Island · 2025 voting record</h3><p>Eleven Senate votes selected by the ACLU. The labels compare '+esc(name)+'’s vote with the ACLU’s position.</p></div><form method="dialog"><button class="aclu-dialog-close" type="submit" aria-label="Close voting record">×</button></form></div><div class="aclu-dialog-list">'
   status={'aligned':'✓ Aligned with ACLU position','opposed':'× Opposed ACLU position','absent':'A Absent / not voting'}
   body+=''.join(f'<div class="aclu-dialog-vote"><span class="aclu-dialog-num">{v["number"]}</span><span class="aclu-dialog-issue">{esc(v["issue"])}</span><span class="aclu-dialog-status {esc(v["status"])}">{status[v["status"]]}</span></div>' for v in r['votes'])+'</div></dialog>'
  body+=f'<p class="source">{esc(r["note"])} <a href="{esc(r["source_url"])}">Source report ↗</a></p>'
 return section('ratings','Outside ratings &amp; scorecards',body)
def ciccone_primary_rows():
 entries=[
  (2026,1930,'100%','Uncontested Democratic primary','https://electionresults.ri.gov/results/public/rhodeisland/elections/RI2026StatewidePrimary/ballot-items/01000000-553f-29ee-0e1f-08df0541a34a'),
  (2024,548,'100%','Uncontested Democratic primary','https://www.ri.gov/election/results/2024/statewide_primary/races/59.html'),
  (2022,1449,'67.7%','Contested Democratic primary','https://www.ri.gov/election/results/2022/statewide_primary/races/24.html'),
  (2020,973,'100%','Uncontested Democratic primary','https://www.ri.gov/election/results/2020/statewide_primary/races/309.html')]
 return [f'<div class="election"><a class="year election-link" href="{url}" aria-label="View {year} Democratic primary result">{year}</a><div><strong>Advanced · {votes:,} votes</strong><small>{label} · Official results</small></div><a class="result election-link" href="{url}" aria-label="View {year} primary result: {share} vote share">{share}</a></div>' for year,votes,share,label,url in entries]

def harmonize(slug):
 p=ROOT/'candidates'/f'{slug}.html';page=p.read_text();rec=next(r for r in load('incumbent_records_2026')['records'] if r['candidate_id'].endswith(slug));name=rec['candidate_name'];district=rec['district_number']
 page=replace_section(page,'bills',bill_sections(rec,slug));page=replace_section(page,'ratings',ratings(rec))
 roster=next(c for c in load('whos_running_2026')['chambers']['senate'][str(district)]['candidates'] if c['candidate_id']==rec['candidate_id'])
 community=roster['hometown']
 page=replace_section(page,'about',section('about','About this candidate',f'<p class="intro">{esc(name)}’s campaign positions and public records, with source and reporting-period details below.</p><div class="grid2"><div class="mini"><h3>At a glance</h3><p>{esc(name)} represents Senate District {district} in {esc(community)}. '+('Urso began serving in 2025.' if district==8 else 'This candidate is listed as the Democratic incumbent in the 2026 candidate roster.')+'</p></div><div class="mini"><h3>How to read this page</h3><p>Campaign positions are attributed to the campaign. Election returns, finance figures and outside scorecards are labeled by source and period.</p></div></div>'))
 page=replace_section(page,'sources',section('sources','Under construction','<p class="intro">This candidate profile is still under construction. Additional information will appear as it is verified.</p><div class="grid2"><div class="empty"><strong>Social media listening</strong>No social media listening or sentiment score is published on this page.</div><div class="empty"><strong>Additional records</strong>Earlier primary results and additional voting dates will be added after review.</div></div>'))
 # Match the existing primary timeline component and make both year and share links.
 rows=[]
 for race in load('primary_results_2026')['races']:
  if race['chamber']=='senate' and race['district']==district:
   for candidate in race['candidates']:
    if candidate['name']==name:
     url=f'/primary-results.html?chamber=senate&amp;district={district}&amp;party=DEM#racePanel'
     rows.append(f'<div class="election"><a class="year election-link" href="{url}" aria-label="View 2026 Democratic primary results for Senate District {district}">2026</a><div><strong>{candidate["votes"]:,} votes</strong><small>Democratic primary · Districtwide</small></div><a class="result election-link" href="{url}" aria-label="View the primary race behind {candidate["pct"]}% vote share">{candidate["pct"]}%</a></div>')
 if slug=='frank-a-ciccone': rows=ciccone_primary_rows()
 official_primary_path=ROOT/'data/candidate_profile_primary_returns_2026.json'
 official_primary=json.loads(official_primary_path.read_text()).get(slug) if official_primary_path.exists() else None
 if official_primary:
  entry=official_primary;url=esc(entry['source_url']);year=entry['year']
  rows=[f'<div class="election"><a class="year election-link" href="{url}" aria-label="View {year} Senate District {district} Democratic primary result">{year}</a><div><strong>Advanced · {entry["votes"]:,} votes</strong><small>Uncontested Democratic primary · Official results</small></div><a class="result election-link" href="{url}" aria-label="View {year} primary result: {entry["share"]} vote share">{entry["share"]}</a></div>']
 page=replace_section(page,'primaries',section('primaries','Democratic primary history',f'<p class="intro">Senate District {district} · Share of votes cast for named candidates. Select a year or vote share to open that specific primary race.</p><div class="timeline">'+(''.join(rows) or '<p>No primary returns are available in the current project dataset for this candidate. Additional primary history is under construction.</p>')+'</div><p class="source">2026 figures use RIEP’s unofficial September 10 snapshot. Earlier primary years are under construction. An uncontested 100% excludes undervotes.</p>'))
 if slug=='frank-a-ciccone' or official_primary:
  page=page.replace('2026 figures use RIEP’s unofficial September 10 snapshot. Earlier primary years are under construction. An uncontested 100% excludes undervotes.','Official Board of Elections returns for the years shown. An uncontested 100% is the share of votes for named candidates, excluding undervotes. Additional earlier years are under construction.')
 # Use Burke's finance grid, office-details list, and subhead styling.
 finance_start=page.index('<section class="card" id="finance">');finance_end=page.index('<section class="card" id="record">');page=page[:finance_start]+page[finance_start:finance_end].replace('class="record-grid"','class="metric-grid"')+page[finance_end:]
 page=page.replace('<h3>Session attendance</h3>','<h3 class="subheading">Session attendance</h3>')
 page=page.replace('<h2>Record in office · 2025–2026 General Assembly</h2>', '<h2>Record in office · 2025–2026 General Assembly</h2><p class="intro">Incumbent · Descriptive counts from RIEP’s official-source research. They are separate from the historical Lawmakers Project score below.</p>')
 page=page.replace('<aside class="side">','<aside class="side" aria-label="Candidate details and navigation">')
 page=re.sub(r'<p><strong>Leadership:</strong> (.*?)</p><p><strong>Committees:</strong> (.*?)</p>',r'<dl class="office-details"><div><dt>Leadership</dt><dd>\1</dd></div><div><dt>Committees</dt><dd>\2</dd></div></dl>',page)
 # Keep all endorsement links in the same dedicated component as Burke.
 research=next(r for r in load('candidate_research_2026_with_endorsements')['candidates'] if r['candidate_id']==rec['candidate_id']);endorsements=research['endorsements']
 if district in (7,8): endorsements=[e for e in endorsements if 'AFL-CIO' not in e['endorser']]+[{'endorser':'Rhode Island AFL-CIO','source_url':'https://rhodeislandaflcio.org/candidate-endorsement-applications-2026/'}]
 page=replace_section(page,'endorsements',section('endorsements','Endorsements','<p class="intro">Published endorsements from outside organizations. Select an organization to view its endorsement source.</p>'+''.join(f'<div class="endorsement-entry"><a class="endorsement-chip" href="{esc(e["source_url"])}" target="_blank" rel="noopener">{esc(e["endorser"])} ↗</a><p class="endorsement-period">2026 election · Senate District {district}</p></div>' for e in endorsements)+'<p class="source">Outside organizations’ endorsements, not RIEP endorsements. Sources may include organization lists and voter-guide records.</p>'))
 # Sidebar labels and contact formatting are shared with Burke.
 email='sen-urso@rilegislature.gov' if district==8 else 'sen-ciccone@rilegislature.gov' if district==7 else roster['email'];phone='(401) 276-5567' if district==8 else '(401) 276-5579' if district==7 else roster['phone']
 official_contacts={1:('sen-bissaillon@rilegislature.gov','(401) 276-5563'),2:('sen-quezada@rilegislature.gov','(401) 255-0345'),3:('sen-zurier@rilegislature.gov','(401) 644-0925')}
 if district in official_contacts: email,phone=official_contacts[district]
 contact=section('contact','Contact &amp; district','<dl class="details">'+''.join(f'<div><dt>{label}</dt><dd>{value}</dd></div>' for label,value in [('District',f'Senate District {district}'),('Community',esc(community)),('Phone',f'<a href="tel:+1{re.sub(r"[^0-9]","",phone)}">{phone}</a>'),('Legislative email' if district in (1,2,3,7,8) else 'Roster contact email',f'<a href="mailto:{email}">{email}</a>')])+'</dl>')
 page=re.sub(r'(<aside class="side"[^>]*>)<section class="card">.*?</section>',lambda m:m[1]+contact,page,count=1,flags=re.S)
 page=page.replace('</body>','<script src="candidate-profile.js"></script></body>')
 if district in official_contacts:
  surname=name.split()[-1].lower();bio=f'https://www.rilegislature.gov/senators/{surname}/Pages/Biography.aspx'
  page=page.replace('Portrait supplied by the project',f'Portrait: <a href="{bio}" target="_blank" rel="noopener">Rhode Island General Assembly ↗</a>').replace('width="402" height="536"','width="450" height="600"')
  if not endorsements:page=page.replace('Published endorsements from outside organizations. Select an organization to view its endorsement source.','No published endorsements are currently recorded for this candidate in RIEP’s research. Additional endorsements will be added after verification.')
 p.write_text(page)
