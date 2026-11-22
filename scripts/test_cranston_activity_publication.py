"""Check public/profile consistency, incoming exclusions and repeatable rendering."""
import json,re,sys
from pathlib import Path
from html.parser import HTMLParser
from publish_cranston_activity import ROOT,PROFILE_IDS,render_profile_activity
class IDs(HTMLParser):
 def __init__(self):super().__init__();self.ids=[]
 def handle_starttag(self,tag,attrs):
  self.ids += [v for k,v in attrs if k=='id']
d=json.loads((ROOT/'data/cranston/activity-index-scores-2026.json').read_text())
assert d['configuration']['joint']=='full' and d['configuration']['cosponsor']==0
expected={'daniel-robert-wall':29,'frank-j-ritz-jr':29,'michael-a-traficante':28,'christopher-e-buonanno':19,'andy-m-andujar':16,'bridget-r-graziano':16,'kristen-e-haroian':16,'emilia-vaziri':10,'richard-d-campopiano':7}
assert {m['id']:m['points'] for m in d['members']}==expected
assert sum(m['points'] for m in d['members'])==170
for m in d['members']:
 assert sum(x['points'] for x in m['tiers'].values())==m['points']
 assert sum(x['points'] for x in m['topics'])==m['points']
for slug in PROFILE_IDS:
 text=(ROOT/'candidates'/(slug+'.html')).read_text()
 assert text.count('id="activity-index"')==1
 assert render_profile_activity(text,slug)==text
 ids=IDs();ids.feed(text);assert len(ids.ids)==len(set(ids.ids)),slug
 card=re.search(r'<section class="card" id="activity-index">.*?</section>',text,re.S)[0]
 if slug in expected:
  m=next(m for m in d['members'] if m['id']==slug)
  assert f'<b>{m["points"]}</b>' in card
  assert f'How the {m["index"]:.1f} index is calculated' in card
  assert f'{abs(m["index"]-100):.1f}%' in card
 else:assert 'Not applicable' in card and 'activity-score-grid' not in card
 assert text.count('<nav class="tabs"')==1
# Test the existing sponsorship renderer also retains exactly one activity card.
from cranston_sponsorship import render_profile
source=json.loads((ROOT/'data/cranston/sponsorship-2026.json').read_text())
for slug in PROFILE_IDS:
 text=(ROOT/'candidates'/(slug+'.html')).read_text()
 rebuilt=render_profile(text,slug,source)
 assert rebuilt.count('id="activity-index"')==1
page=(ROOT/'cranston-activity.html').read_text()
assert page.count('<tr id=')==9 and '<!-- RANKING_ROWS -->' not in page
assert 'noindex,nofollow' in (ROOT/'cranston-activity-index-test.html').read_text()
print('Profile scores, no predecessor transfer, unique IDs, rebuild persistence and public ranking checks passed')


wall=(ROOT/'candidates/daniel-robert-wall.html').read_text()
assert 'alt="Daniel Robert Wall" width="526" height="554"' in wall
assert 'Tied #1 in documented sponsorship activity' in wall and 'with Frank J. Ritz Jr.' in wall
assert '53.5%' in wall and '18.9 points' in wall
assert (ROOT/'candidates/daniel-robert-wall.png').read_bytes()[:8]==b'\x89PNG\r\n\x1a\n'
assert 'most effective legislator' not in wall.lower()
print('Portrait, explicit first-place tie and plain-language score explanation passed')
