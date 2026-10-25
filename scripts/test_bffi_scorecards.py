"""Check identity matching, missing/conflicting labels, coverage and repeat builds."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from bffi_scorecards import ROOT,payload,card,styles,CATEGORIES,esc
from build_bffi_scorecards import build,registry
from candidate_profile_components import bffi_card,bffi_styles

def test():
 data=payload();rows=data['candidates'];by_id={r['candidate_id']:r for r in rows};assert len(rows)==len(by_id)
 profiles=registry();assert len(profiles)==135
 for r in rows:
  labels={s['rating'] for s in r['sources']}
  assert all(s['chamber']==r['chamber'] and s['district_number']==r['district_number'] for s in r['sources'])
  assert labels<=CATEGORIES
  if r['status']=='rated':assert labels=={r['rating']}
  elif r['status']=='conflicting_source_entries':assert len(labels)>1 and r['rating'] is None
  else:assert r['status']=='not_listed' and not labels and r['rating'] is None
 class IDs(HTMLParser):
  def __init__(self):super().__init__();self.ids=[]
  def handle_starttag(self,t,a):
   d=dict(a)
   if d.get('id'):self.ids.append(d['id'])
 for cid,slug in profiles.items():
  r=by_id[cid];page=(ROOT/'candidates'/f'{slug}.html').read_text();markup=card(r)
  assert markup in page,slug
  assert page.count('id="bffi-scorecard"')==1
  assert page.count('id="bffi-title"')==1
  assert 'href="#bffi-scorecard"' in page
  assert 'bffi-scorecard.css?v=20261025-all' in page
  assert esc(r['candidate_name']) in markup
  assert bffi_card(r)==markup and bffi_styles(page,r)==page
  assert 'not an RIEP score or endorsement' in markup
  assert data['methodology_url'] in markup
  for source in r['sources']:assert source['source_url'] in markup and source['source_image_url'] in markup
  if r['status']=='conflicting_source_entries':
   assert 'Conflicting entries' in markup
   for source in r['sources']:assert f"{source['municipality']}: {source['rating']}" in markup
  if r['status']=='not_listed':assert 'Not listed' in markup and 'not an N/A or Against rating' in markup
  parser=IDs();parser.feed(page);assert len(parser.ids)==len(set(parser.ids)),slug
 # Different candidates in one district must retain their distinct labels.
 assert by_id['house-39-dem-primary-megan-l-cotter']['rating']=='For'
 assert by_id['house-39-rep-primary-jasmin-roy']['rating']=='Against'
 assert by_id['house-15-dem-primary-colleen-m-crudele']['rating']=='N/A'
 assert by_id['house-15-ind-general-allan-w-fung']['rating'] is None
 assert card({'candidate_id':'unknown','chamber':'house','district_number':39})==''
 assert not build(),'repeat builds must not modify profiles'
 css=(ROOT/'candidates/bffi-scorecard.css').read_text()
 for cls in ['bffi-against','bffi-mixed','bffi-na','bffi-unlisted']:assert cls in css
 counts=Counter((by_id[c]['status'],by_id[c]['rating']) for c in profiles)
 print('PASS: 135 profiles, candidate identity, source conflicts, missing entries, categories, attribution, unique IDs and idempotent regeneration.',dict(counts))
if __name__=='__main__':test()
