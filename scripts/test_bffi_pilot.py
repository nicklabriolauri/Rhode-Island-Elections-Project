"""Check attribution, one-candidate scope, regeneration and accessible markup."""
from html.parser import HTMLParser
from candidate_profile_components import ROOT,load,bffi_card,bffi_styles,ratings
from build_bffi_pilot import build

records=load('incumbent_records_2026')['records']
target=next(r for r in records if r['candidate_id']=='senate-32-dem-primary-pamela-j-lauria')
payload=load('bffi_pilot_2026')
assert len(payload['ratings'])==1
assert payload['ratings'][0]['rating']=='For'
assert payload['retrieved_at']=='2026-10-06'
card=bffi_card(target)
for phrase in ['Bodily Freedom Forever Index','The Womxn Project','2026 general election','For','reproductive rights','gender-affirming care','LGBTQ+ rights','two-question survey','public statements','voting records','N/A','Mixed','not an RIEP score or endorsement','dated snapshot']:
 assert phrase in card,phrase
assert '100%' not in card and 'Expected benchmark' not in card
assert payload['ratings'][0]['source_url'] in card
assert payload['methodology_url'] in card
for rec in records:
 if rec['candidate_id']!=target['candidate_id']:assert bffi_card(rec)==''
page_path=ROOT/'candidates/pamela-j-lauria.html'
before=page_path.read_text();build();assert page_path.read_text()==before,'repeat builds must be stable'
assert before.count('id="bffi-scorecard"')==1
assert before.count('href="bffi-scorecard.css?v=20261006"')==1
assert bffi_styles(before,target)==before
assert 'id="bffi-scorecard"' in ratings(target),'profile regeneration retains pilot'
for phrase in ['Center for Effective Lawmaking','id="riep-legislative-index"','id="aclu-votes-dialog"','RI League of Cities and Towns','data-voting-widget']:
 assert phrase in before,phrase
class Tags(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.fragments=[]
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if attrs.get('id'):self.ids.append(attrs['id'])
  if attrs.get('href','').startswith('#'):self.fragments.append(attrs['href'][1:])
tags=Tags();tags.feed(before)
assert len(tags.ids)==len(set(tags.ids))
assert all(fragment in tags.ids for fragment in tags.fragments)
for path in (ROOT/'candidates').glob('*.html'):
 if path!=page_path:assert 'id="bffi-scorecard"' not in path.read_text(),path
print('PASS: Lauria-only BFFI pilot, category meaning, sources, stable regeneration, existing scorecards and HTML IDs')
