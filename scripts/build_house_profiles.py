"""Build the published Providence-area House profiles from existing, dated RIEP records."""
import json, re
from urllib.parse import quote
from pathlib import Path
import build_candidate_pages as base
from candidate_profile_components import section, replace_section, ratings, bill_sections, current_index
ROOT=Path(__file__).resolve().parents[1]
CONFIGS=[('Edith H Ajello','edith-h-ajello',1,'ajello','edith_ajello', '(401) 222-2296'),('Christopher R Blazejewski','christopher-r-blazejewski',2,'blazejewski','christopher_blazejewski','(401) 222-2466'),('Nathan W Biah','nathan-w-biah',3,'biah','nathan_biah','(401) 222-1224'),('Rebecca M Kislak','rebecca-m-kislak',4,'Kislak','rebecca_kislak','(401) 222-1591')]
CONFIGS += [('Raymond A Hull','raymond-a-hull',6,'Hull','raymond_hull','(401) 222-1723'),('John Joseph Lombardi','john-joseph-lombardi',8,'lombardi','john_lombardi','(401) 222-1721'),('Enrique George Sanchez','enrique-george-sanchez',9,'Sanchez','enrique_sanchez','(401) 222-1162'),('Scott A Slater','scott-a-slater',10,'slater','scott_slater','(401) 222-1591')]

CONFIGS += [('Anthony J DeSimone','anthony-j-desimone',5,'desimone','anthony_desimone','(401) 222-2447')]
CONFIGS += [('Grace Diaz','grace-diaz',11,'diaz','grace_diaz','(401) 222-2258'),('Ramon Perez','ramon-perez',13,'perez','ramon_perez','(401) 222-1725'),('Charlene M Lima','charlene-m-lima',14,'Lima','charlene_lima','(401) 222-2447')]
CONFIGS += [('Brandon Potter','brandon-potter',16,'potter','brandon_potter','(401) 222-2447'),('Jacquelyn Baginski','jacquelyn-baginski',17,'baginski','jacquelyn_baginski','(401) 222-4263'),('Arthur Handy','arthur-handy',18,'Handy','arthur_handy','(401) 222-1725')]

CONFIGS += [('Christopher G Paplauskas','christopher-g-paplauskas',15,'Paplauskas','christopher_paplauskas','(401) 222-2259')]

CONFIGS += [('Joseph McNamara','joseph-mcnamara',19,'McNamara','joseph_mcnamara','(401) 222-2296')]
CONFIGS += [('David A Bennett','david-a-bennett',20,'Bennett','david_bennett','(401) 222-2369'),('Marie A Hopkins','marie-a-hopkins',21,'Hopkins','marie_hopkins','(401) 222-2259')]

CONFIGS += [('Evan Patrick Shanley','evan-patrick-shanley',24,'Shanley','evan_shanley','(401) 222-1224'),('Thomas E Noret','thomas-e-noret',25,'Noret','thomas_noret','(401) 222-4435'),('Earl A Read III','earl-a-read-iii',26,'Read','earl_read','(401) 222-2296')]

CONFIGS += [('George A Nardone','george-a-nardone',28,'Nardone','george_nardone','(401) 222-2259'),('Sherry L Roberts','sherry-l-roberts',29,'Roberts','sherry_roberts','(401) 222-2259'),('Justine Caldwell','justine-caldwell',30,'caldwell','justine_caldwell','(401) 222-4263')]

CONFIGS += [('Carol Hagan McEntee','carol-hagan-mcentee',33,'McEntee','carol_hagan_mcentee','(401) 222-4435'),('Teresa A Tanzi','teresa-a-tanzi',34,'Tanzi','teresa_tanzi','(401) 222-1722')]

CONFIGS += [('Tina L Spears', 'tina-l-spears', 36, 'spears', 'tina_spears', '(401) 222-1162'), ('Samuel Angelo Azzinaro', 'samuel-angelo-azzinaro', 37, 'azzinaro', 'sam_azzinaro', '(401) 222-1882'), ('Brian Patrick Kennedy', 'brian-patrick-kennedy', 38, 'kennedy', 'brian_patrick_kennedy', '(401) 222-2369'), ('Megan L Cotter', 'megan-l-cotter', 39, 'cotter', 'megan_cotter', '(401) 222-1591'), ('Michael Chippendale', 'michael-chippendale', 40, 'chippendale', 'michael_chippendale', '(401) 222-2259')]

CONFIGS += [('Richard R Fascia','richard-r-fascia',42,'Fascia','richard_fascia','(401) 222-2259'),('Deborah A Fellela','deborah-a-fellela',43,'Fellela','deborah_fellela','(401) 222-1723')]

CONFIGS += [('Gregory Costantino','gregory-costantino',44,'Costantino','gregory_costantino','(401) 222-1721'),('Mia A Ackerman','mia-a-ackerman',45,'Ackerman','mia_ackerman','(401) 222-1723'),('Mary Ann Shallcross Smith','mary-ann-shallcross-smith',46,'shallcross%20smith','mary_ann_shallcross_smith','(401) 222-1721'),('David J Place','david-j-place',47,'Place','david_place','(401) 222-2259'),('Brian C Newberry','brian-c-newberry',48,'Newberry','brian_newberry','(401) 222-2259')]

CONFIGS += [('Jon D Brien','jon-d-brien',49,'brien','jon_brien','(401) 222-1591'),('Stephen Casey','stephen-casey',50,'Casey','stephen_casey','(401) 222-8028'),('Robert D Phillips','robert-d-phillips',51,'Phillips','robert_phillips','(401) 222-1721'),('Alex D Marszalkowski','alex-d-marszalkowski',52,'Marszalkowski','alex_marszalkowski','(401) 222-1722')]

CONFIGS += [('Paul M Santucci', 'paul-m-santucci', 53, 'Santucci', 'paul_santucci', '(401) 222-2259'), ("William W O'Brien", 'william-w-o-brien', 54, 'OBrien', 'william_obrien', '(401) 222-1882'), ('Arthur J Corvese', 'arthur-j-corvese', 55, 'Corvese', 'arthur_corvese', '(401) 222-1591'), ('Joshua J Giraldo', 'joshua-j-giraldo', 56, 'Giraldo', 'joshua_giraldo', '(401) 222-2447')]

CONFIGS += [('Brandon T Voas','brandon-t-voas',57,'voas','brandon_voas','(401) 222-1224'),('Cherie L Cruz','cherie-l-cruz',58,'cruz','cherie_cruz','(401) 222-2447')]

CONFIGS += [('Jennifer A Stewart', 'jennifer-a-stewart', 59, 'stewart', 'jennifer_stewart', '(401) 222-1721'), ('Karen Alzate', 'karen-alzate', 60, 'Alzate', 'karen_alzate', '(401) 222-1882'), ('Leonela Felix', 'leonela-felix', 61, 'felix', 'leonela_felix', '(401) 222-2447'), ('Mary Duffy Messier', 'mary-duffy-messier', 62, 'messier', 'mary_messier', '(401) 222-1725')]

CONFIGS += [('Katherine Sheena Kazarian', 'katherine-sheena-kazarian', 63, 'Kazarian', 'katherine_kazarian', '(401) 222-2466'), ('Jenni A Furtado', 'jenni-a-furtado', 64, 'Furtado', 'jenni_furtado', '(401) 222-2296'), ('Matthew Dawson', 'matthew-dawson', 65, 'Dawson', 'matthew_dawson', '(401) 222-1725')]

CONFIGS += [('Jennifer Smith Boylan', 'jennifer-smith-boylan', 66, 'Boylan', 'jennifer_boylan', '(401) 222-4263'), ('June S Speakman', 'june-s-speakman', 68, 'Speakman', 'june_speakman', '(401) 222-2369'), ('Susan Ann Donovan', 'susan-ann-donovan', 69, 'Donovan', 'susan_donovan', '(401) 222-8028'), ('John G Edwards', 'john-g-edwards', 70, 'Edwards', 'john_edwards', '(401) 222-8028')]

CONFIGS += [('Michelle E McGaw', 'michelle-e-mcgaw', 71, 'mcgaw', 'michelle_mcgaw', '(401) 222-2447'), ('Terri-Denise Cortvriend', 'terri-denise-cortvriend', 72, 'cortvriend', 'terri_cortvriend', '(401) 222-1723'), ('Marvin Abney', 'marvin-abney', 73, 'abney', 'marvin_abney', '(401) 222-8028'), ('Alex Finkelman', 'alex-finkelman', 74, 'finkelman', 'alex_finkelman', '(401) 222-1725'), ('Lauren H Carson', 'lauren-h-carson', 75, 'carson', 'lauren_carson', '(401) 222-1162')]

def build(slugs=None):
 # Use the complete 75-member calculation dataset for the House index.
 base.current_index=current_index
 fogarty=(ROOT/'candidates/kathleen-a-fogarty.html').read_text()
 widget=re.search(r'<section class="card voting-pilot" id="voting-patterns">.*?</section>',fogarty,re.S).group()
 portraits=json.loads((ROOT/'data/candidate_portrait_sources_2026.json').read_text())
 records=base.load('incumbent_records_2026')['records']
 primary=base.load('primary_results_2026')['races']
 registry={}
 for name,slug,district,surname,image,phone in CONFIGS:
  if slugs is not None and slug not in slugs:continue
  bio=f'https://www.rilegislature.gov/representatives/{surname}/Pages/Biography.aspx'
  community={6:'Providence, North Providence',13:'Providence, Johnston',14:'Cranston, Providence',15:'Cranston',16:'Cranston',17:'Cranston',18:'Cranston',19:'Warwick, Cranston',20:'Warwick, Cranston',21:'Warwick',24:'Warwick, East Greenwich',25:'Coventry, West Warwick',26:'Coventry, West Warwick, Warwick',28:'Coventry',29:'Coventry, West Greenwich',30:'East Greenwich, West Greenwich',33:'Narragansett, South Kingstown',34:'Narragansett, South Kingstown',36:'Charlestown, New Shoreham, South Kingstown, Westerly',37:'Westerly',38:'Hopkinton, Westerly',39:'Exeter, Hopkinton, Richmond',40:'Coventry, Foster, Glocester',42:'Johnston, Cranston',43:'Johnston',44:'Johnston, Lincoln, Smithfield',45:'Cumberland, Lincoln',46:'Lincoln, Pawtucket',47:'Burrillville, Glocester',48:'Burrillville, North Smithfield',49:'Woonsocket, North Smithfield',50:'Woonsocket',51:'Woonsocket, Cumberland',52:'Cumberland',53:'Smithfield, Glocester',54:'North Providence',55:'North Providence',56:'Central Falls',57:'Central Falls, Cumberland',58:'Pawtucket',59:'Pawtucket',60:'Pawtucket, Central Falls',61:'Pawtucket',62:'Pawtucket',63:'East Providence, Pawtucket',64:'East Providence, Pawtucket',65:'East Providence',66:'Barrington, East Providence',68:'Bristol, Warren',69:'Bristol, Portsmouth',70:'Portsmouth, Tiverton',71:'Little Compton, Portsmouth, Tiverton',72:'Middletown, Portsmouth',73:'Middletown, Newport',74:'Jamestown, Middletown',75:'Newport'}.get(district,'Providence')
  email=f'rep-{surname.lower()}@rilegislature.gov' if district!=46 else 'rep-shallcross-smith@rilegislature.gov'
  base.build(name,slug,district,community,email,phone,'house')
  path=ROOT/'candidates'/f'{slug}.html';page=path.read_text()
  rec=next(r for r in records if r['chamber']=='house' and r['district_number']==district)
  registry[rec['candidate_id']]=slug
  candidate=next(c for c in base.load('whos_running_2026')['chambers']['house'][str(district)]['candidates'] if c['candidate_id']==rec['candidate_id'])
  party_code=candidate['party'];party=candidate['party_label']
  page=replace_section(page,'bills',bill_sections(rec,slug))
  page=replace_section(page,'ratings',ratings(rec))
  if slug=='jon-d-brien':
   page=re.sub(r'<span>#[0-9]+ of [0-9]+ House Democrats</span>','',page,count=1)
   page=page.replace('The party rank compares this legislator with other members of the same party in the same chamber. ', 'Brien is an Independent; the historical dataset’s Democratic comparison rank is omitted here. ')
  page=replace_section(page,'about',section('about','About this candidate',f'<p class="intro">{base.esc(name)} represents House District {district} · {base.esc(community)}.</p><div class="grid2"><div class="mini"><h3>At a glance</h3><p>{base.esc(party)} incumbent in the 2026 candidate roster.</p></div><div class="mini"><h3>How to read this page</h3><p>Campaign positions, election returns, campaign finance and outside scorecards are labeled by source and period.</p></div></div><p class="source">'+base.link(bio,'Official General Assembly biography ↗')+'</p>'))
  if district==64:
   page=page.replace('Democratic incumbent in the 2026 candidate roster.','Democratic incumbent in the 2026 candidate roster. First elected in November 2024; House service began in 2025.')
   page=page.replace('No 2023–2024 CEL score is available in the project dataset for this candidate.','A 2023–2024 CEL score does not apply to Furtado’s House service, which began in 2025. Her current-session RIEP index is shown below.')
  if district==53:
   page=page.replace('Republican incumbent in the 2026 candidate roster.','Republican incumbent in the 2026 candidate roster. First elected to the House in November 2024; first legislative session: 2025–2026.')
   page=page.replace('No 2023–2024 CEL score is available in the project dataset for this candidate.','A 2023–2024 CEL score does not apply to Santucci’s House service, which began in 2025. His current-session RIEP index is shown below.')
  contact=section('contact','Contact &amp; district','<dl class="details">'+''.join(f'<div><dt>{k}</dt><dd>{v}</dd></div>' for k,v in [('District',f'House District {district}'),('Community',base.esc(community)),('Phone',base.link('tel:+1'+re.sub('[^0-9]','',phone),phone)),('Legislative email',base.link('mailto:'+email,email))])+'</dl><p class="source">'+base.link(bio,'Official General Assembly contact details ↗')+'</p>')
  page=re.sub(r'(<aside class="side"[^>]*>)<section class="card">.*?</section>',lambda m:m[1]+contact,page,count=1,flags=re.S)
  rows=[]
  official=base.load('candidate_profile_primary_returns_2026').get(slug,[])
  if isinstance(official,dict):official=[official]
  for result in official:
   url=result['source_url'];label=('Uncontested ' if result.get('uncontested') else '')+result['party']+' primary · Official results'
   rows.append(f'<div class="election"><a class="year election-link" href="{base.esc(url)}">{result["year"]}</a><div><strong>{result["votes"]:,} votes</strong><small>{base.esc(label)}</small></div><a class="result election-link" href="{base.esc(url)}">{base.esc(result["share"])}</a></div>')
  for race in ([] if official else primary):
   if race['chamber']!='house' or int(race['district'])!=district or race['party_code']!=party_code:continue
   for c in race['candidates']:
    if c['name']!=name:continue
    url=f'/races/house-{district}-'+('democratic' if party_code=='DEM' else 'republican')+'.html'
    rows.append(f'<div class="election"><a class="year election-link" href="{url}">2026</a><div><strong>{c["votes"]:,} votes</strong><small>{base.esc(party)} primary · Unofficial September 10 snapshot</small></div><a class="result election-link" href="{url}">{c["pct"]}%</a></div>')
  body=f'<p class="intro">House District {district} · Share of votes cast for named candidates.</p><div class="timeline">'+(''.join(rows) or '<p>Primary vote totals are under construction. No vote total is assigned from a different race.</p>')+'</div><p class="source">'+('2026 figures use RIEP’s unofficial September 10 snapshot. Earlier primary years are under construction. ' if rows else '')+base.link('https://electionresults.ri.gov/results/public/rhodeisland/elections/RI2026StatewidePrimary','Official 2026 Board of Elections results ↗')+'</p>'
  if official:body=f'<p class="intro">House District {district} · Share of votes cast for named candidates.</p><div class="timeline">'+''.join(rows)+'</div><p class="source">'+ ' · '.join(base.link(r['source_url'],r['source_label']+' ↗') for r in official)+'. Official 2026 results updated September 15, 2026. Earlier primary years are under construction.</p>'
  if party_code=='IND':body='<p class="intro">Independent general-election candidate; a 2026 party-primary vote total is not assigned. Earlier party-primary history is under construction.</p>'
  page=replace_section(page,'primaries',section('primaries','Primary history' if party_code=='IND' else party+' primary history',body))
  research=next(r for r in base.load('candidate_research_2026_with_endorsements')['candidates'] if r['candidate_id']==rec['candidate_id'])
  endorsements=research['endorsements']
  page=replace_section(page,'endorsements',section('endorsements','Endorsements',('<p class="intro">Published endorsements from outside organizations. Select an organization to view its endorsement source.</p>' if endorsements else '<p class="intro">No published endorsements are currently recorded for this candidate in RIEP’s research. Additional endorsements will be added after verification.</p>')+''.join(f'<div class="endorsement-entry"><a class="endorsement-chip" href="{base.esc(e["source_url"])}" target="_blank" rel="noopener">{base.esc(e["endorser"])} ↗</a><p class="endorsement-period">2026 election · House District {district}</p></div>' for e in endorsements)+'<p class="source">Outside organizations’ endorsements, not RIEP endorsements. Sources may include organization lists and voter-guide records.</p>'))
  selected=widget.replace('Kathleen A Fogarty',name).replace('Kathleen%20A%20Fogarty',quote(name))
  page=page.replace('<section class="card" id="bills">',selected+'<section class="card" id="bills">',1)
  page=page.replace('href="voting-patterns/pilot.css','href="house-voting-patterns/pilot.css')
  page=page.replace('</body>','<script src="candidate-profile.js"></script><script src="house-voting-patterns/pilot.js?v=20261006-house"></script></body>')
  finance_snapshot=re.search(r'<section class="card" id="finance">.*?</section>',page,re.S).group()
  page=page.replace('Rhode Island Senator','Rhode Island Representative').replace('chamber=senate','chamber=house').replace('October 4, 2026','October 6, 2026').replace('October 5, 2026','October 6, 2026')
  page=page.replace(f'/running.html?chamber=house&amp;district={district}&amp;election=general',f'/races/house-{district}.html')
  page=re.sub(r'<p class="photo-note">.*?</p>','<p class="photo-note">Portrait: '+base.link(bio,'Rhode Island General Assembly ↗')+'</p>',page)
  from PIL import Image
  photo=ROOT/'candidates'/f'{slug}.png'
  if not photo.exists():photo=ROOT/'candidates'/f'{slug}.jpg'
  w,h=Image.open(photo).size if photo.exists() else (0,0)
  page=re.sub(r'(class="portrait"[^>]*?)width="[0-9]+" height="[0-9]+"',lambda m:m[1]+f'width="{w}" height="{h}"',page)
  page=page.replace('<aside class="side">','<aside class="side" aria-label="Candidate details and navigation">').replace('<h3>Session attendance</h3>','<h3 class="subheading">Session attendance</h3>')
  start=page.index('<section class="card" id="finance">');end=page.index('<section class="card" id="record">');page=page[:start]+page[start:end].replace('class="record-grid"','class="metric-grid"')+page[end:]
  page=re.sub(r'<p><strong>Leadership:</strong> (.*?)</p><p><strong>Committees:</strong> (.*?)</p>',r'<dl class="office-details"><div><dt>Leadership</dt><dd>\1</dd></div><div><dt>Committees</dt><dd>\2</dd></div></dl>',page)
  if district==2:page=page.replace('<dd></dd>','<dd>No committee assignments listed in the recorded roster.</dd>')
  assert 'chamber=senate' not in page and 'Senate District' not in page
  if district in (15,19,20,21,24,25,26,28,29,30,33,34,36,37,38,39,40,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,68,69,70,71,72,73,74,75):page=page.replace(f'href="/races/house-{district}.html"',f'href="/running.html?chamber=house&amp;district={district}&amp;election=general"')
  if district in range(44,76):page=page.replace('October 6, 2026','October 7, 2026')
  page=replace_section(page,'finance',finance_snapshot.replace('class="record-grid"','class="metric-grid"'))
  path.write_text(page)
  entry={'slug':slug,'portrait_url':('https://www.rilegislature.gov/representatives/Pictures/McEntee.jpg' if district==33 else f'https://www.rilegislature.gov/LegislationPictures/{image}.jpg'),'biography_url':bio,'retrieved_at':'2026-10-07','credit':'Rhode Island General Assembly','width':w,'height':h}
  if photo.exists():entry['file_name']=photo.name
  if photo.exists():portraits=[r for r in portraits if r['slug']!=slug]+[entry]
 (ROOT/'data/candidate_portrait_sources_2026.json').write_text(json.dumps(portraits,indent=2)+'\n')
 for filename in ['ballot.html','running.html']:
  path=ROOT/filename;page=path.read_text()
  def extend(m):
   entries=json.loads(m[1]);entries.update(registry)
   return 'const candidateProfile = ('+json.dumps(entries,separators=(',',':'))+')[candidate.candidate_id]'
  page,n=re.subn(r'const candidateProfile = \((\{.*?\})\)\[candidate.candidate_id\]',extend,page);assert n==1
  path.write_text(page)
 path=ROOT/'index.html';page=path.read_text();marker='      if(candidate?.chamber !== "senate") return "";'
 all_registry=json.loads(re.search(r'const candidateProfile = \((\{.*?\})\)\[candidate.candidate_id\]',(ROOT/'ballot.html').read_text())[1])
 profiles={}
 for d,race in base.load('whos_running_2026')['chambers']['house'].items():
  profiles[d]=[[re.findall(r'[a-z0-9]+',c['name'].split()[-1].lower())[-1],all_registry[c['candidate_id']]] for c in race['candidates'] if c['candidate_id'] in all_registry]
 house='      if(candidate?.chamber === "house") {\n        const profiles = '+json.dumps(profiles,separators=(',',':'))+';\n        const profile = (profiles[Number(candidate.district_number)] || []).find(p=>normalizeSearchText(candidate.name || "").split(" ").includes(p[0]));\n        return profile ? `candidates/${profile[1]}.html` : "";\n      }\n'
 pattern=r'      if\(candidate\?\.chamber === "house"\) \{\n.*?\n      \}\n'
 if re.search(pattern,page,re.S):page=re.sub(pattern,lambda m:house,page,count=1,flags=re.S)
 else:page=page.replace(marker,house+marker,1)
 path.write_text(page)
if __name__=='__main__':build()
