"""Build a compact mobile guide from the site's authoritative datasets."""
import json,re,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def norm(s):return re.sub('[^a-z0-9]','',s.lower())
def main():
 load=lambda f:json.loads((ROOT/'data'/f).read_text())
 roster=load('whos_running_2026.json');finance=load('candidate_finance_2026.json')['profiles'];priorities=load('candidate_profiles_2026.json')['profiles'];research=load('candidate_research_2026_with_endorsements.json')['candidates'];ratings=load('race_ratings_2026.json')['races']
 rows=[];seen=set()
 for chamber,districts in roster['chambers'].items():
  for district,race in districts.items():
   for c in race.get('candidates',[])+race.get('general_candidates',[]):
    active=c.get('election_status')=='general_candidate' or c.get('on_election_ballot') and c.get('election_status') not in ('lost_primary','withdrawn','removed')
    key=(chamber,str(district),norm(c['name']))
    if not active or key in seen:continue
    seen.add(key)
    match=lambda p:p.get('chamber')==chamber and str(p.get('district_number'))==str(district) and norm(p.get('candidate_name',''))==norm(c['name'])
    f=next((p for p in finance if match(p)),None);p=next((p for p in priorities if match(p)),None);r=next((p for p in research if match(p)),None)
    slug=f['slug'] if f else re.sub('[^a-z0-9]+','-',c['name'].lower()).strip('-')
    path=ROOT/'candidates'/f'{slug}.html';profile='/candidates/'+path.name if path.exists() else None
    photo=next(('/candidates/'+slug+ext for ext in ['.png','.jpg','.jpeg'] if (ROOT/'candidates'/(slug+ext)).exists()),None)
    raw=(p or {}).get('priorities') or (r or {}).get('priorities') or []
    snaps=[]
    if f:
     for s in [f]+list(reversed(f.get('archived_reporting_periods',[]))):
      label=s.get('reporting_period_label') or s.get('report_label','Reporting period')
      snaps.append({k:s.get(k) for k in ['report_label','reporting_period_label','money_raised','money_spent','ending_cash','finance_audit_note']}|{'pdf':s.get('latest_filing_href')})
    rows.append(dict(id=c['candidate_id'],slug=slug,name=c['name'],party=c.get('party','OTH'),chamber=chamber,district=int(district),hometown=c.get('hometown',''),status=c.get('status_label',''),profile=profile,photo=photo,priorities=raw,finance=snaps,finance_url='/finance.html?slug='+slug if f else None))
 data=dict(updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),cycle=2026,candidates=rows,ratings=[{k:r.get(k) for k in ['chamber','district','rating','projected_flip','included']} for r in ratings])
 (ROOT/'data/mobile_guide_2026.json').write_text(json.dumps(data,separators=(',',':'))+'\n')
 print(len(rows),'general-election candidates;', (ROOT/'data/mobile_guide_2026.json').stat().st_size,'bytes')
if __name__=='__main__':main()
