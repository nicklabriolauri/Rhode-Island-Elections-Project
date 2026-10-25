"""Apply BFFI cards to every published profile without rebuilding other records."""
import json,re
from pathlib import Path
from bffi_scorecards import card,styles,payload,ROOT

def registry():
 return json.loads(re.search(r'const candidateProfile = \((\{.*?\})\)\[candidate.candidate_id\]',(ROOT/'ballot.html').read_text())[1])

def apply(page,rec):
 from candidate_profile_components import replace_section
 if 'id="bffi-scorecard"' in page:page=replace_section(page,'bffi-scorecard','')
 # Keep the card inside the scorecards section, where incumbent generators expect it.
 marker=re.search(r'<section\b[^>]*id="ratings"[^>]*>',page)
 if not marker:
  marker=re.search(r'<section\b[^>]*id="finance"[^>]*>',page)
  assert marker,rec['candidate_id']
  return styles(page[:marker.start()]+card(rec)+page[marker.start():],rec)
 depth=0;end=None
 for tag in re.finditer(r'</?section\b[^>]*>',page[marker.start():]):
  depth+=-1 if tag.group().startswith('</') else 1
  if depth==0:end=marker.start()+tag.start();break
 assert end is not None
 page=page[:end]+card(rec)+page[end:]
 return styles(page,rec)

def build():
 by_id={r['candidate_id']:r for r in payload()['candidates']};changed=[]
 for cid,slug in registry().items():
  assert cid in by_id,cid
  p=ROOT/'candidates'/f'{slug}.html';old=p.read_text();new=apply(old,by_id[cid])
  if new!=old:p.write_text(new);changed.append(slug)
 return changed
if __name__=='__main__':print('Updated BFFI scorecards:',len(build()))
