#!/usr/bin/env python3
"""RIEP journal-based attendance builder for the 2025-2026 RI General Assembly.

Attendance means presence at a legislative session as recorded in the official
House/Senate Journal. Floor-vote 'Not Voting' is NOT treated as absence.

Requires: requests, pypdf
Input:  data/incumbent_records_2026.json
Output: data/incumbent_records_2026.json
        data/attendance_sessions_2025_2026.json
        data/attendance_audit_2025_2026.json
"""
from __future__ import annotations
import datetime as dt, io, json, re, time, unicodedata
from pathlib import Path
import requests
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'
RECORDS=DATA/'incumbent_records_2026.json'
SESSIONS_OUT=DATA/'attendance_sessions_2025_2026.json'
AUDIT_OUT=DATA/'attendance_audit_2025_2026.json'
HTTP=requests.Session(); HTTP.headers.update({'User-Agent':'RhodeIslandElectionsProject/1.0 (+https://www.rhodeislandelectionsproject.org/)'})
HOUSE='https://www.rilegislature.gov/journals/housejournals'
SENATE='https://www.rilegislature.gov/journals/senatejournals'
WINDOWS={2025:(dt.date(2025,1,1),dt.date(2025,7,31)),2026:(dt.date(2026,1,1),dt.date(2026,7,31))}

def norm(s):
    s=unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower().replace("o'",'o')
    s=re.sub(r'\b(the honorable|honorable|speaker|madam president|president|representatives?|senators?)\b',' ',s)
    s=re.sub(r'\b(jr|sr|ii|iii|iv)\.?\b',' ',s); return ' '.join(re.sub(r'[^a-z0-9]+',' ',s).split())
def surname(s):
    p=norm(s).split(); return p[-1] if p else ''
def dates(a,b):
    while a<=b: yield a; a+=dt.timedelta(days=1)
def urls(chamber,d):
    y=d.year; ds=d.strftime('%m-%d-%Y'); label='House' if chamber=='house' else 'Senate'; base=HOUSE if chamber=='house' else SENATE
    names=[f'{ds}.pdf',f'HJ%20{ds}.pdf'] if chamber=='house' else [f'SJ%20{ds}.pdf',f'{ds}.pdf']
    return [f'{base}/{y}%20{label}%20Journals/{n}' for n in names]
def fetch(chamber,d):
    for u in urls(chamber,d):
        try:r=HTTP.get(u,timeout=25)
        except requests.RequestException:continue
        if r.status_code==200 and (r.content.startswith(b'%PDF') or 'pdf' in (r.headers.get('content-type') or '').lower()):return u,r.content
    return None
def text(pdf):
    rd=PdfReader(io.BytesIO(pdf)); return '\n'.join((p.extract_text() or '') for p in rd.pages[:8])
def totals(t):
    m=re.search(r'(\d+)\s+(?:members|Senators?)\s+present\s+and\s+(\d+)\s+(?:members?|Senators?)\s+absent',t,re.I|re.S)
    if not m:m=re.search(r'quorum\s+is\s+declared\s+present\s+with\s+(\d+).*?present\s+and\s+(\d+).*?absent',t,re.I|re.S)
    return (int(m.group(1)),int(m.group(2))) if m else (None,None)
def section(t,label,nexts):
    t=t.replace('\u2013','-').replace('\u2014','-'); nxt='|'.join(re.escape(x) for x in nexts)
    m=re.search(rf'\b{label}\s*-\s*\d+\s*:\s*(.*?)(?=\b(?:{nxt})\s*-|\n\s*(?:INVOCATION|PLEDGE|APPROVAL|COMMUNICATIONS)\b)',t,re.I|re.S)
    return m.group(1).strip() if m else ''
def names(sec):
    s=re.sub(r'\s+',' ',sec); s=re.sub(r'\b(?:The Honorable )?(?:Speaker|President)\s+[A-Za-z.\' -]+?\s+and\s+(?:Representatives|Senators)\s+','',s,flags=re.I)
    s=re.sub(r'^(?:Representatives|Senators)\s+','',s,flags=re.I); s=re.sub(r',?\s+and\s+',', ',s)
    return [x.strip(' .;') for x in s.split(',') if surname(x)]
def presider(t,ch):
    p=(r'PRESENT\s*-\s*\d+\s*:\s*The Honorable Speaker\s+([A-Za-z.\' -]+?)\s+and\s+Representatives' if ch=='house' else r'PRESENT\s*-\s*\d+\s*:\s*The Honorable President\s+([A-Za-z.\' -]+?)\s*,?\s+Senators')
    m=re.search(p,t,re.I|re.S); return re.sub(r'\s+',' ',m.group(1)).strip() if m else None
def late(t):
    out=[]
    for p in [r'(?:Representative|Senator)\s+([A-Za-z.\' -]+?)\s+(?:is|was)\s+(?:now\s+)?present',r'(?:Representative|Senator)\s+([A-Za-z.\' -]+?)\s+(?:arrives|arrived)\s+(?:in|at)\s+the\s+(?:House|Senate|Chamber)',r'(?:Representative|Senator)\s+([A-Za-z.\' -]+?)\s+reports?\s+(?:his|her|their)\s+presence']:
        out += [re.sub(r'\s+',' ',m.group(1)).strip(' ,.;') for m in re.finditer(p,t,re.I)]
    return list(dict.fromkeys(out))
def parse(ch,d,u,t):
    dp,da=totals(t); P=names(section(t,'PRESENT',('ABSENT',))); A=names(section(t,'ABSENT',('INVOCATION','COMMUNICATIONS','PLEDGE','APPROVAL')))
    pr=presider(t,ch)
    if pr and surname(pr) not in {surname(x) for x in P}:P.insert(0,pr)
    L=late(t)
    # Validate initial roll before late-arrival corrections.
    p0={surname(x) for x in P}; a0={surname(x) for x in A}; declared=(dp+da) if dp is not None and da is not None else None
    initial_valid=declared is not None and len(p0)+len(a0)==declared and len(p0)==dp and len(a0)==da
    for x in L:
        sx=surname(x); A=[a for a in A if surname(a)!=sx]
        if sx not in {surname(a) for a in P}:P.append(x)
    return {'date':d.isoformat(),'chamber':ch,'source_url':u,'declared_present':dp,'declared_absent':da,'present':sorted({surname(x) for x in P}),'absent':sorted({surname(x) for x in A}),'late_arrivals':sorted({surname(x) for x in L}),'validated':initial_valid}
def collect():
    ok=[]; bad=[]
    for y,(a,b) in WINDOWS.items():
      for ch in ('house','senate'):
        for d in dates(a,b):
            f=fetch(ch,d)
            if not f:continue
            u,pdf=f
            try:s=parse(ch,d,u,text(pdf))
            except Exception as e:bad.append({'date':d.isoformat(),'chamber':ch,'source_url':u,'error':repr(e)}); continue
            (ok if s['validated'] else bad).append(s if s['validated'] else {'date':d.isoformat(),'chamber':ch,'source_url':u,'error':'roll-call reconciliation failed'})
            time.sleep(.03)
    return ok,bad
def merge(payload,sessions):
    by={ch:sorted([s for s in sessions if s['chamber']==ch],key=lambda x:x['date']) for ch in ('house','senate')}
    for r in payload['records']:
        start=dt.date.fromisoformat(r.get('service_start','2025-01-01')); ln=surname(r['candidate_name']); chamber_sessions=[s for s in by[r['chamber']] if dt.date.fromisoformat(s['date'])>=start]
        eligible=[s for s in chamber_sessions if ln in s['present'] or ln in s['absent']]; unmatched=[s['date'] for s in chamber_sessions if ln not in s['present'] and ln not in s['absent']]
        P=[s for s in eligible if ln in s['present']]; A=[s for s in eligible if ln in s['absent']]; n=len(eligible)
        status='verified_from_official_journals' if n and not unmatched else ('partial_review_required' if n else 'not_available')
        r['attendance']={'period':'2025–2026 General Assembly','definition':'Presence at a legislative session as recorded in the official House/Senate Journal.','sessions_eligible':n or None,'sessions_present':len(P) if n else None,'sessions_absent':len(A) if n else None,'attendance_rate_pct':round(100*len(P)/n,1) if n else None,'absent_dates':[s['date'] for s in A],'source_urls_for_absences':[s['source_url'] for s in A],'unmatched_validated_session_dates':unmatched,'status':status,'note':"Session attendance only. A floor-vote 'Not Voting' entry is not counted as an absence."}
        r.setdefault('verification',{})['attendance']=status

def main():
    payload=json.loads(RECORDS.read_text(encoding='utf-8')); sessions,bad=collect()
    if not sessions:raise SystemExit('No validated journals found; public data not modified.')
    merge(payload,sessions)
    SESSIONS_OUT.write_text(json.dumps({'updated_at':dt.date.today().isoformat(),'sessions':sessions},indent=2),encoding='utf-8')
    review=[{'candidate_name':r['candidate_name'],'chamber':r['chamber'],'district_number':r['district_number'],'status':r['attendance']['status'],'unmatched_dates':r['attendance']['unmatched_validated_session_dates']} for r in payload['records'] if r['attendance']['status']!='verified_from_official_journals']
    AUDIT_OUT.write_text(json.dumps({'updated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'validated_session_count':len(sessions),'house_sessions':sum(s['chamber']=='house' for s in sessions),'senate_sessions':sum(s['chamber']=='senate' for s in sessions),'excluded_or_failed_journals':bad,'records_requiring_review':review},indent=2),encoding='utf-8')
    if review:
        out=DATA/'incumbent_records_2026_WITH_ATTENDANCE_REVIEW.json'; out.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8'); print('Review required:',out); raise SystemExit(2)
    RECORDS.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8'); print('Updated',RECORDS)
if __name__=='__main__':main()
