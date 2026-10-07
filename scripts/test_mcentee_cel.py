"""Ensure the CEL name alias resolves McEntee and preserves her finance update."""
import json,re,sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_cel_ratings_2026 as c
root=Path(__file__).resolve().parents[1]
assert c.normalized_name('McEntee, Hagan')==c.normalized_name('Carol Hagan McEntee')
assert c.normalized_name('Hagan McEntee')==('carol','mcentee')
assert c.normalized_name('McEntee, Michael')!=c.normalized_name('Carol Hagan McEntee')
data=json.loads((root/'data/outside_ratings_2026.json').read_text())
rows=[r for r in data['ratings'] if r['organization']==c.ORGANIZATION and r['chamber']=='house' and r['district_number']==33]
assert len(rows)==1
r=rows[0];assert r['candidate_name']=='Carol Hagan McEntee' and r['cel_id']==17597
assert r['rating']=='1.98' and r['party_rank']==6 and r['party_total']==66 and r['benchmark']==1.401
assert r['expectation']=='Meets Expectations'
assert r['bills']==dict(introduced=44,committee_action=44,beyond_committee=20,passed_chamber=20,became_law=16)
assert len(r['history'])==5 and r['history'][1]['score']==2.52
page=(root/'candidates/carol-hagan-mcentee.html').read_text()
assert '<strong>1.98</strong>' in page and '#6 of 66 House Democrats' in page
assert 'No 2023–2024 CEL score is available' not in page
before=subprocess.check_output(['git','show','04575b86954bd4878a332d9b8b3a96f7e914b72b:candidates/carol-hagan-mcentee.html'],cwd=root,text=True)
section=lambda s:re.search(r'<section class="card" id="finance">.*?</section>',s,re.S).group()
assert section(page)==section(before)
prior=json.loads(subprocess.check_output(['git','show','04575b86954bd4878a332d9b8b3a96f7e914b72b:data/outside_ratings_2026.json'],cwd=root,text=True))
assert data['ratings'][:-1]==prior['ratings']
assert 'riep-legislative-index' in page and 'data-voting-widget' in page
print('PASS: verified McEntee CEL name alias, score, rank, bill stages and five-session history; finance and other scorecards unchanged')
