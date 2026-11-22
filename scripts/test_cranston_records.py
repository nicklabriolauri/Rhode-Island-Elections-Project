"""Run before publishing. Checks identities, deduplication, source integrity and known examples."""
from pathlib import Path
import json,collections
R=Path(__file__).resolve().parents[1]
d=json.loads((R/'data/cranston/records-2026/records.json').read_text())
ids={m['id'] for m in d['members']};assert len(ids)==9
assert not ids&{'sara-jane-haupt','avery-therese-mangahas','steven-a-stycos'}
for table in ['meetings','motions','attendance','sources']:
 keys=[x['id'] for x in d[table]];assert len(keys)==len(set(keys)),table
for m in d['motions']:
 assert set(m['votes'])<=ids
 if m['votes']:
  assert sum(v=='Yes' for v in m['votes'].values())==m['yes'],m['id']
  assert sum(v=='No' for v in m['votes'].values())==m['no'],m['id']
  assert m['review_status']!='Needs review'
 if m['review_status']=='Needs review':assert not m['votes'],m['id']
 assert m['source_id'] in {s['id'] for s in d['sources']}
for mid,rows in __import__('itertools').groupby(sorted(d['attendance'],key=lambda a:a['meeting_id']),key=lambda a:a['meeting_id']):
 rows=list(rows);assert len(rows)==9 and {x['member_id'] for x in rows}==ids
 assert all(x['status'] in ['Present','Absent','Late arrival','Not recorded'] for x in rows)
# Same July/August/September minutes were filed twice. Count the session once.
for dt in ['2026-07-20','2026-08-17','2026-09-22']:assert sum(m['date']==dt for m in d['meetings'])==1,dt
r=next(r for r in d['resolutions'] if r['number']=='2026-2');assert len(r['motion_ids'])==1
m=next(m for m in d['motions'] if m['id']==r['motion_ids'][0]);assert (m['yes'],m['no'],m['source_page'])==(8,0,2)
assert 'Councilman Traficante' in m['action'] and 'Resolution' in m['action']
assert 'bridget-r-graziano' not in m['votes']
a=next(a for a in d['attendance'] if a['date']=='2026-01-20' and a['member_id']=='bridget-r-graziano');assert a['status']=='Absent'
# Joint March 4 minutes explicitly note Haroian arriving at 7:11, not present at opening.
a=next(a for a in d['attendance'] if a['date']=='2026-03-04' and a['member_id']=='kristen-e-haroian');assert a['status']=='Late arrival'
a=next(a for a in d['attendance'] if a['date']=='2026-03-04' and a['member_id']=='christopher-e-buonanno');assert a['status']=='Not recorded'
assert any(m['review_status']=='Aggregate only' and not m['votes'] and m['result']=='Unanimous' for m in d['motions'])
assert len(d['resolutions'])==22 and any(r['number']=='2026-12A' for r in d['resolutions'])
assert not any(r['number']=='2026-15' for r in d['resolutions'])
assert all(r.get('document_status')=='downloaded' and r.get('original_path','').endswith('.pdf') for r in d['resolutions'])
assert all(r.get('source_url','').startswith('https://') for r in d['resolutions'])
assert any(m['date']=='2026-11-16' and m['minutes_status']=='No minutes on file' for m in d['meeting_inventory'])
for p in ['sara-jane-haupt','avery-therese-mangahas','steven-a-stycos']:
 html=(R/'candidates'/(p+'.html')).read_text();section=html.split('id="votes"')[1].split('</section>')[0]
 assert 'No 2026 attendance rate or votes' in section and 'recorded absences' not in section
print('Cranston record checks passed:',len(d['meetings']),'meetings,',len(d['resolutions']),'resolutions,',sum(len(m['votes']) for m in d['motions']),'named votes')
