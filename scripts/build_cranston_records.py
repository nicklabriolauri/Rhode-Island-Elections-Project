"""Build auditable council records from collected public sources.
Only explicit named votes whose counts reconcile are assigned to members.
Review overrides are separate from raw sources and keyed by stable record IDs.
"""
from pathlib import Path
import json,re,hashlib,datetime,bisect,difflib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data/cranston/records-2026'
clean=lambda s:' '.join(s.split())
MEMBERS=[('bridget-r-graziano','Bridget R. Graziano','Graziano','Ward 1'),('andy-m-andujar','Andy M. Andujar','Andujar','Ward 3'),('frank-j-ritz-jr','Frank J. Ritz Jr.','Ritz','Ward 4'),('michael-a-traficante','Michael A. Traficante','Traficante','Ward 5'),('emilia-vaziri','Emilia Vaziri','Vaziri','Citywide'),('richard-d-campopiano','Richard D. Campopiano','Campopiano','Citywide'),('christopher-e-buonanno','Christopher E. Buonanno','Buonanno','Citywide'),('kristen-e-haroian','Kristen E. Haroian','Haroian','Ward 2'),('daniel-robert-wall','Daniel Robert Wall','Wall','Ward 6')]
def names(s):
 s=re.sub(r'\bVazri\b','Vaziri',s,flags=re.I)
 return [m[0] for m in MEMBERS if re.search(r'\b'+m[2]+r'\b',s,re.I)]
def date_of(s):
 m=re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})[, .]+\s*(2026)',s,re.I)
 return datetime.datetime.strptime(' '.join(m.groups()),'%B %d %Y').date().isoformat() if m else None
def key(s):return hashlib.sha256(s.encode()).hexdigest()[:12]
def build():
 src=json.loads((OUT/'sources.json').read_text());state_dates={d.get('expected_date') for d in src['documents'] if d.get('expected_date')};meetings=[];motions=[];attendance=[];review=[];docs=[];seen=set()
 for d in src['documents']:
  if d.get('sha256') in seen:continue
  if d.get('sha256'):seen.add(d['sha256'])
  docs.append({k:v for k,v in d.items() if k not in ['pages','links']})
  if d['category']!='minutes' or not d.get('pages'):continue
  raw='\n\f\n'.join(p['text'] for p in d['pages']);digest=key(re.sub(r'[^a-z0-9]','',raw.lower()))
  if digest in seen:continue
  seen.add(digest)
  text=re.sub(r'\s',' ',raw).replace('\x02',' ')
  for match in re.finditer(r'City Council Minutes[^\n]*Page \d+|U/[^\n]+',raw):text=text[:match.start()]+' '*(match.end()-match.start())+text[match.end():]
  # Date must come from the meeting heading, never a prior meeting's approval date.
  dt=date_of(text[:4500]);
  if 'clerkshq.com' in d['url'] and dt in state_dates:continue
  mid='cranston-'+(dt or 'unknown')+'-'+key(d['url'])
  page=lambda pos: raw[:pos].count('\f')+1 if len(d['pages'])>1 or d['url'].lower().endswith('.pdf') else None
  mt={'id':mid,'date':dt,'body':'City Council','type':'Special' if not re.search(r'REGULAR\s+MEETING',text[:1600],re.I) else 'Regular','source_id':d['id'],'source_url':d['url'],'original_path':d.get('local_path'),'attendance_status':'not extracted','minutes_status':d.get('minutes_status','ClerkBase approved archive')}
  if not dt:
   review.append({'id':mid,'type':'Meeting date','reason':'No 2026 date in meeting heading','source_url':d['url']});continue
  # The roster printed in the letterhead may be outdated. Only use opening roll call.
  roll=re.search(r'ROLL\s+CALL\s*:?\s*(.*?)(?:PLEDGE\s+OF|PUBLIC\s+COMMENT|III\s*\.)',text,re.I)
  if roll:
   body=roll[1];body=re.split(r'Also\s+Present\s*:',body,flags=re.I)[0]
   split=re.split(r'\bAbsent\s*:',body,flags=re.I);present=names(split[0]);absent=names(split[1]) if len(split)>1 else []
   late=names(' '.join(re.findall(r'[^.]*\barrived\b[^.]*',body,flags=re.I)))
   present=[x for x in present if x not in late]
   overlap=set(present)&set(absent)
   if present and not overlap:
    mt['attendance_status']='opening roll call extracted'
    for m in MEMBERS:
     status='Late arrival' if m[0] in late else 'Present' if m[0] in present else 'Absent' if m[0] in absent else 'Not recorded'
     attendance.append({'id':mid+'-'+m[0],'meeting_id':mid,'date':dt,'member_id':m[0],'status':status,'source_id':d['id'],'source_url':d['url'],'source_page':page(roll.start()),'source_excerpt':clean(roll[0]),'review_status':'Source extracted' if status!='Not recorded' else 'Needs review','reviewer':'','review_date':''})
    if len(present)+len(absent)+len(late)!=9:review.append({'id':mid+'-attendance','type':'Attendance','reason':'Opening roll call does not resolve all nine members','source_url':d['url']})
   else:review.append({'id':mid+'-attendance','type':'Attendance','reason':'Ambiguous opening roll call','source_url':d['url']})
  else:review.append({'id':mid+'-attendance','type':'Attendance','reason':'Opening roll call not found','source_url':d['url']})
  meetings.append(mt)
  starts=[m.start() for m in re.finditer(r'(?:(?:On|Upon)\s+motion\b|(?:A\s+)?MOTION\s+(?:was\s+)?(?:duly\s+)?made\b)',text,re.I)]
  groups=[]
  pat=r'(?:The\s+)?following\s+(?:being\s+recorded\s+as\s+voting|voted|voting)\s*[“"\']\s*(aye|nay|yes|no|abstain(?:ed)?)\s*[”"\']\s*:?'
  for g in re.finditer(pat,text,re.I):
   tail=text[g.end():g.end()+1100];tailraw=raw[g.end():g.end()+1100]
   end=re.search(r'\s[-–]\s*(\d{1,2})(?:\s*\.|\s|$)',tail)
   wall=re.search(r'\bWall\b(?:\s*[-–]\s*\d+)?[. ]*',tail)
   reported=int(end[1]) if end else None
   if end:stop=end.end()
   elif wall:stop=wall.end()
   else:
    boundary=re.search(r'\n\s*\n',tailraw.lstrip(' '));offset=len(tailraw)-len(tailraw.lstrip(' '))
    stop=boundary.start()+offset if boundary else len(tail)
   chunk=tail[:stop];ids=names(chunk)
   idx=bisect.bisect_right(starts,g.start())-1;start=starts[idx] if idx>=0 else max(0,g.start()-800)
   groups.append({'start':start,'pos':g.start(),'end':g.end()+stop,'choice':'Yes' if g[1].lower() in ['aye','yes'] else 'No' if g[1].lower() in ['nay','no'] else 'Abstain','ids':ids,'reported':reported if reported is not None else len(ids),'chunk':chunk})
  for g in re.finditer(r'Roll\s+call\s+(aye|nay)\s*[-–:]?',text,re.I):
   tail=text[g.end():g.end()+1100];end=re.search(r';\s*(?:Absent|Abstain|Recus)|[.]\s*(?:Result|[IVX]+[.])',tail,re.I)
   if not end:continue
   chunk=tail[:end.start()];ids=names(chunk);idx=bisect.bisect_right(starts,g.start())-1
   if idx<0:continue
   groups.append({'start':starts[idx],'pos':g.start(),'end':g.end()+end.start(),'choice':'Yes' if g[1].lower()=='aye' else 'No','ids':ids,'reported':len(ids),'chunk':chunk})
  clusters={}
  for g in groups:clusters.setdefault(g['start'],[]).append(g)
  for start,gs in clusters.items():
   gs=list({(g['choice'],tuple(g['ids']),g['reported']):g for g in gs}.values())
   stop=max(g['end'] for g in gs);block=text[start:stop];votes={};issues=[]
   for g in gs:
    if len(g['ids'])!=g['reported']:issues.append('Named '+g['choice']+' list does not reconcile to its printed count')
    for member in g['ids']:
     if member in votes:issues.append('Member repeated across vote lists')
     votes[member]=g['choice']
   tallies=list(re.finditer(r'(?:vote\s+of|Result:)\s*(\d+)\s*[-–]\s*(\d+)',block,re.I));yes=sum(v=='Yes' for v in votes.values());no=sum(v=='No' for v in votes.values())
   if tallies:
    tally=tallies[-1]
    if (yes,no)!=(int(tally[1]),int(tally[2])):issues.append('Named yes/no votes do not match printed overall tally')
   # Explicit named lists can establish votes even when the minutes omit an aggregate tally.
   # Keep the motion and immediately preceding agenda context. Never infer support from sponsorship.
   before=raw[max(0,start-2200):start]
   markers=list(re.finditer(r'(?:^|\n)\s*[•·]?\s*(?:RESOLUTION|Resolution|ORDINANCE|Ordinance|APPROVAL|APPOINTMENT|RE-APPOINTMENT|ADOPTION|\d{1,2}-\d{2}-\d{2}[A-Za-z]?)\b',before))
   context=before[markers[-1].start():] if markers else ''
   context=re.split(r'\n\s*\n',context.strip())[0] if context else ''
   if re.search(r'(?:On|Upon)\s+motion|MOTION\s+made',context,re.I):context=''
   title=clean(context).strip(' :;.-') or 'Council motion'
   sentence=re.split(r'(?<=\.)\s+(?:Motion|The following|Roll call|Under Discussion)',block,maxsplit=1,flags=re.I)[0]
   action=clean(sentence)
   if re.search(r'new business.*as a block',action,re.I):title='Refer new business as a block'
   elif re.search(r'minutes.*as a block',action,re.I):title='Approve prior meeting minutes as a block'
   elif re.search(r'resolutions.*as a block',action,re.I):title='Consider resolutions as a block'
   if len(action)>1500:action=action[:1500]+'…'
   motionid=mid+'-motion-'+key(clean(block)+str(start))
   rec={'id':motionid,'meeting_id':mid,'date':dt,'title':title,'action':action,'kind':'resolution' if re.search(r'\bresolution\b',title+' '+action,re.I) else 'other','result':'Failed' if re.search(r'motion\s+(?:failed|lost)',block,re.I) else 'Passed' if re.search(r'(?:motion\s+passed|was\s+adopted|resolution\s+was\s+adopted)',block,re.I) else 'Recorded vote','yes':yes,'no':no,'abstain':sum(v=='Abstain' for v in votes.values()),'votes':votes if not issues else {},'extracted_votes':votes,'source_id':d['id'],'source_url':d['url'],'source_page':page(gs[0]['pos']),'source_excerpt':clean(block),'review_status':'Needs review' if issues else 'Source extracted','reviewer':'','review_date':'','reported_tally':(tallies[-1][1]+'–'+tallies[-1][2]) if tallies else None,'tally_basis':'Printed tally' if tallies else 'Counted from named lists','resolution_ids':[],'minutes_status':d.get('minutes_status','ClerkBase approved archive')}
   motions.append(rec)
   if issues:review.append({'id':motionid,'type':'Roll call','reason':'; '.join(sorted(set(issues))),'source_url':d['url'],'source_excerpt':clean(block)})
  # Preserve aggregate outcomes even when the minutes do not name individual voters.
  aggregate_seen=set()
  for m in re.finditer(r'Motion\s+(?:passed|failed)[^.]{0,130}\.|(?:Resolution|Ordinance)\s+was\s+adopted[^.]{0,100}\.|All\s+Ayes\b',text,re.I):
   if any(s<=m.start()<=max(g['end'] for g in gs) for s,gs in clusters.items()):continue
   idx=bisect.bisect_right(starts,m.start())-1;start=starts[idx] if idx>=0 else max(0,m.start()-500)
   if start in aggregate_seen:continue
   aggregate_seen.add(start)
   block=clean(text[start:m.end()]);tally=re.search(r'(?:vote\s+of|Result:)\s*(\d+)\s*[-–]\s*(\d+)',block,re.I)
   unanimous=bool(re.search(r'unanim|All\s+Ayes',block,re.I))
   before=raw[max(0,start-2200):start];markers=list(re.finditer(r'(?:^|\n)\s*[•·]?\s*(?:RESOLUTION|Resolution|ORDINANCE|Ordinance|APPROVAL|APPOINTMENT|RE-APPOINTMENT|ADOPTION|\d{1,2}-\d{2}-\d{2}[A-Za-z]?)\b',before))
   context=before[markers[-1].start():].strip() if markers else ''
   context=re.split(r'\n\s*\n',context)[0]
   if re.search(r'(?:On|Upon)\s+motion|MOTION\s+made',context,re.I):context=''
   motionid=mid+'-aggregate-'+key(block+str(start))
   rec={'id':motionid,'meeting_id':mid,'date':dt,'title':clean(context) or 'Council motion','action':block[:1500],'kind':'resolution' if re.search(r'\bresolution\b',context+' '+block,re.I) else 'other','result':'Unanimous' if unanimous else 'Failed' if re.search(r'failed',m[0],re.I) else 'Passed','yes':int(tally[1]) if tally else None,'no':int(tally[2]) if tally else None,'abstain':None,'votes':{},'extracted_votes':{},'source_id':d['id'],'source_url':d['url'],'source_page':page(m.start()),'source_excerpt':block,'review_status':'Aggregate only','reviewer':'','review_date':'','resolution_ids':[],'tally_basis':'Printed aggregate' if tally else 'Unanimous; individual names not listed' if unanimous else 'No individual list extracted','minutes_status':d.get('minutes_status','ClerkBase approved archive')}
   motions.append(rec)
   if not unanimous:review.append({'id':motionid,'type':'Unassigned motion result','reason':'No reconciled named roll call was extracted; do not assign individual votes','source_url':d['url'],'source_page':page(m.start()),'source_excerpt':block})
 # Resolution inventory is extracted directly from the numbered table, not generated from a sequence.
 resolutions=src.get('resolutions',[])
 for res in resolutions:
  value=re.sub(r'([A-Za-z]{3})[.]',r'\1',res['adopted_date_text']);res['adopted_date']=datetime.datetime.strptime(value,'%b %d, %Y').date().isoformat()
  candidates=[m for m in motions if m['date']==res.get('adopted_date') and m['kind']=='resolution']
  def score(m):
   a=set(re.findall(r'[a-z]{3,}',res['title'].lower()))-{'the','and','city','cranston','resolution','council','of','as','by'}
   b=set(re.findall(r'[a-z]{3,}',(m['title']+' '+m['action']).lower()))
   return len(a&b)/len(a) if a else 0
  ranked=sorted([(score(m),m) for m in candidates],key=lambda x:x[0],reverse=True)
  matches=[m for n,m in ranked if n>=.72 and (n==ranked[0][0])]
  # A unique strong title/date match links records. Ambiguous matches stay in review.
  if len(matches)==1:
   res['motion_ids']=[matches[0]['id']];matches[0]['resolution_ids'].append(res['number']);res['match_status']='Title and date matched'
  else:
   res['motion_ids']=[];res['match_status']='Needs review'
   review.append({'id':'resolution-'+res['number'],'type':'Resolution match','reason':'No unique title/date match to a recorded motion','source_url':res['source_url']})
 # Exact same meeting bytes are deduplicated above; preserve distinct special meetings on the same day.
 overrides_path=OUT/'review-overrides.json'
 if overrides_path.exists():
  overrides=json.loads(overrides_path.read_text())
  for m in motions:
   if m['id'] in overrides.get('motions',{}):m.update(overrides['motions'][m['id']])
 records={'year':2026,'retrieved_at':src['retrieved_at'],'scope':'Full City Council, opening roll call and explicitly named motion votes. Committee meetings are separate and not included.','members':[{'id':x[0],'name':x[1],'surname':x[2],'office_2026':x[3]} for x in MEMBERS],'sources':docs,'meetings':sorted(meetings,key=lambda x:(x['date'],x['id'])),'attendance':attendance,'motions':sorted(motions,key=lambda x:(x['date'],x['id']),reverse=True),'resolutions':resolutions,'review_queue':review,'meeting_inventory':src.get('meeting_inventory',[]),'collection_errors':src.get('index_errors',[])}
 (OUT/'records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2));print(json.dumps({'meetings':len(meetings),'attendance':len(attendance),'motions':len(motions),'assigned_motions':sum(bool(m['votes']) for m in motions),'resolutions':len(resolutions),'review_items':len(review)}))
 return records
if __name__=='__main__':build()
