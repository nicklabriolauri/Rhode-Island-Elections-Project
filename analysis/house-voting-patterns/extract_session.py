"""Extract binary floor roll calls from the official 2025-2026 House journals."""
import csv,json,re,collections
from pathlib import Path
ROOT=Path(__file__).parent
roster=json.loads((ROOT/'representatives.json').read_text());manifest=json.loads((ROOT/'manifest.json').read_text())
def vote_list(raw):
 # A name list ends at its sentence-ending period. Some journals omit a blank line before the next motion.
 end=re.search(r'\.(?=[ \t]*(?:\n|$))',raw)
 return raw[:end.end()] if end else raw
def in_office(r,date):return r["served_start"]<=date and (r["served_end"] is None or date<=r["served_end"])
def normalize_name(raw):
 raw=raw.lower().replace("’", "'")
 raw=re.sub(r"\b(the honorable|honorable|speaker|representatives?|and)\b", " ",raw)
 return re.sub(r"[^a-z]", "", raw)
def names(raw):
 raw=vote_list(raw)
 raw=re.sub(r'\s+and\s+Representatives\s+', ', ', raw, flags=re.I)
 # Exact comma-delimited surnames prevent O'Brien from matching Brien.
 raw=re.sub(r"Shallcross\s*,\s*Smith", "Shallcross Smith",raw,flags=re.I)
 parts=[normalize_name(part) for part in re.sub(r"\s+", " ",raw).split(',')]
 lookup={r['surname']:r['name'] for r in roster}
 unknown=set(parts)-set(lookup)-{''}
 assert not unknown, f"Unrecognized names: {unknown}: {raw}"
 return {lookup[n] for n in parts if n}
def csvwrite(name,rows):
 with (ROOT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
rolls=[];votes=[];audit=[];other=[]
pattern=r'YEAS\s*[–—-]\s*(\d+)\s*:\s*(.*?)NAYS\s*[–—-]\s*(\d+)[ \t]*:?[ \t]*'
for j in manifest:
 text=(ROOT/j['text']).read_text()
 clean=re.sub(r'H\.J\.\s*--[^\n]*\n','\n',text)
 rawcount=len(re.findall(r'YEAS\s*[–—-]',clean));matches=list(re.finditer(pattern,clean,re.S))
 missed=rawcount-len(matches)
 if missed:
  audit.append({'date':j['date'],'issue':'unparsed_yea_blocks','count':missed})
 end=0;active=''
 for seq,m in enumerate(matches,1):
  raw_no=vote_list(clean[m.end():]) if int(m[3]) else ''
  yes=names(m[2]);no=names(raw_no) if int(m[3]) else set();context=clean[end:m.start()];end=m.end()+len(raw_no)
  heads=list(re.finditer(r'(?m)^\s*\d+\.\s+202[56]-([HS])\s+(\d+)([^\n]*)',context))
  bills=[h[1]+h[2]+' '+h[3].strip() for h in heads]
  if bills:active=bills[-1].strip()
  tail=context[-1400:].lower()
  consent='consent calendar' in tail and ('following measures' in tail or 'roll call' in tail)
  if consent:kind='Consent calendar';bill='; '.join(bills);active=''
  elif 'motion to amend' in tail[-550:] or 'motion to amend' in tail[-850:] and 'read and passed' not in tail[-400:]:kind='Amendment';bill=active
  elif 'advice and consent' in tail[-650:]:kind='Appointment';bill=''
  elif 'read and passed' in tail[-650:] or 'passage' in tail[-400:]:kind='Passage';bill=active
  else:kind='Other floor motion';bill=active
  rid=f"HOU-{j['date'].replace('-','')}-{seq:03d}"
  outofservice=[r['name'] for r in roster if r['name'] in yes|no and not in_office(r,j['date'])]
  valid=len(yes)==int(m[1]) and len(no)==int(m[3]) and not yes&no and not outofservice
  issues=[]
  if len(yes)!=int(m[1]) or len(no)!=int(m[3]):issues.append('Published totals do not reconcile with named votes')
  if yes&no:issues.append('Name appears in both Yea and Nay lists')
  if outofservice:issues.append('Named vote outside service window')
  roll={'rollcall_id':rid,'date':j['date'],'year':j['year'],'journal_page':clean[:m.start()].count('\f')+1,
   'source_url':j['url'],'motion_class':kind,'bill_label':bill,'declared_yeas':int(m[1]),'declared_nays':int(m[3]),
   'listed_yeas':len(yes),'listed_nays':len(no),'valid':valid,'issues':'; '.join(issues),
   'minority_share':min(len(yes),len(no))/len(yes|no) if yes|no else 0,
   'raw_yeas':vote_list(m[2]).strip(),'raw_nays':raw_no.strip() if int(m[3]) else '', 'context':context[-2000:].strip()}
  rolls.append(roll)
  if not valid:audit.append({'date':j['date'],'rollcall_id':rid,'journal_page':roll['journal_page'],'issues':issues,'printed':[int(m[1]),int(m[3])],'listed':[len(yes),len(no)],'overlap':sorted(yes&no),'outside_service':outofservice})
  for r in roster:
   inservice=in_office(r,j['date'])
   status='Conflicting Yea/Nay' if r['name'] in yes&no else 'Yea' if r['name'] in yes else 'Nay' if r['name'] in no else 'Not listed in Yea/Nay' if inservice else 'Not in office'
   votes.append({'rollcall_id':rid,'date':j['date'],'legislator':r['name'],'district':r['district'],'party':r['party'],'status':status,'vote_code':1 if status=='Yea' else 0 if status=='Nay' else '', 'valid_rollcall':valid})
 # Nonbinary officer-election ballots are documented separately, not coerced into Yea/Nay.
 for m in re.finditer(r'(?m)^\s*(SHEKARCHI|CHIPPENDALE|BLAZEJEWSKI)\s*[-–—]\s*(\d+)\s*:',clean):
  other.append({'date':j['date'],'journal_page':clean[:m.start()].count('\f')+1,'source_url':j['url'],'reason':'Named candidate ballot, not a binary Yea/Nay vote','context':clean[max(0,m.start()-650):m.start()+1000].strip()})
(ROOT/'audit.json').write_text(json.dumps(audit,indent=2))
assert not any(x.get('issue')=='unparsed_yea_blocks' for x in audit),'Unparsed Yea blocks; inspect audit before modeling'
csvwrite('rollcalls.csv',rolls);csvwrite('votes_long.csv',votes)
if other:csvwrite('nonbinary_ballots.csv',other)
lookup={(r['legislator'],r['rollcall_id']):r['vote_code'] for r in votes}
for fname,rs in [('votes_matrix.csv',rolls),('model_matrix.csv',[r for r in rolls if r['valid']])]:
 with (ROOT/fname).open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['legislator']+[r['rollcall_id'] for r in rs])
  for r in roster:w.writerow([r['name']]+[lookup[r['name'],x['rollcall_id']] for x in rs])
(ROOT/'audit.json').write_text(json.dumps(audit,indent=2))
summary={'journals':len(manifest),'years':dict(collections.Counter(j['year'] for j in manifest)),
 'people_in_historical_roster':len(roster),'current_representatives':sum(r['current'] for r in roster),'binary_rollcalls':len(rolls),
 'validated_rollcalls':sum(r['valid'] for r in rolls),'quarantined_rollcalls':sum(not r['valid'] for r in rolls),
 'validated_divided_rollcalls':sum(r['valid'] and r['minority_share']>=.025 for r in rolls),'nonbinary_ballots':len(other)}
(ROOT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
