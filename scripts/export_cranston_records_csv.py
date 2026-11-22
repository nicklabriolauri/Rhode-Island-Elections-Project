"""Portable flat-table export for Excel, R, Python or another municipality's template.
Run after build_cranston_records.py. Standard Python only; preserves stable keys.
Intern review notes must be joined back by Record ID, never by row position.
"""
import json,csv
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'data/cranston/records-2026';d=json.loads((D/'records.json').read_text());out=D/'csv';out.mkdir(exist_ok=True)
for name in ['members','resolutions','meetings','attendance','motions','sources','meeting_inventory','review_queue']:
 rows=d[name]
 if not rows:continue
 keys=list(dict.fromkeys(k for row in rows for k in row))
 with (out/(name+'.csv')).open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
  for row in rows:
   # Protect spreadsheet imports from treating source wording as a formula.
   values={k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else ("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) for k,v in row.items()};w.writerow(values)
with (out/'votes.csv').open('w',newline='',encoding='utf-8-sig') as f:
 keys=['vote_id','motion_id','date','member_id','vote','source_url','source_page'];w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
 for m in d['motions']:
  for member,vote in m['votes'].items():w.writerow(dict(vote_id=m['id']+'-'+member,motion_id=m['id'],date=m['date'],member_id=member,vote=vote,source_url=m['source_url'],source_page=m['source_page']))
print('Exported keyed CSV tables to',out)
