"""Render the reviewed/extracted public-record view on the nine municipal profiles."""
from pathlib import Path
import json,re
from html import escape as e
ROOT=Path(__file__).resolve().parents[1]
def publish():
 d=json.loads((ROOT/'data/cranston/records-2026/records.json').read_text());current={m['id']:m for m in d['members']}
 registry=json.loads((ROOT/'data/local_representatives.json').read_text())
 for person in registry['profiles']:
  slug=person['slug'];path=ROOT/'candidates'/(slug+'.html')
  if not path.exists():continue
  if person.get('municipality') not in [None,'Cranston']:continue
  # Only the nine Cranston profiles are eligible, never other profiles in the directory.
  if slug not in ['avery-therese-mangahas','sara-jane-haupt','andy-m-andujar','frank-j-ritz-jr','michael-a-traficante','daniel-robert-wall','emilia-vaziri','steven-a-stycos','kristen-e-haroian']:continue
  if slug in current:
   a=[a for a in d['attendance'] if a['member_id']==slug];p=sum(x['status']=='Present' for x in a);late=sum(x['status']=='Late arrival' for x in a);absent=sum(x['status']=='Absent' for x in a);u=sum(x['status']=='Not recorded' for x in a)
   votes=[m for m in d['motions'] if slug in m['votes']]
   body=f'<p>2026 service: <strong>{e(current[slug]["office_2026"])}</strong>. This history follows the individual across terms and offices.</p><h3>Meeting attendance</h3><p><strong>{p} present at opening roll call</strong> · {late} documented late arrivals · {absent} recorded absences · {u} unresolved opening records.</p><p class="source">Coverage: {len(d["meetings"])} available full council meeting records. Missing minutes are excluded. Opening roll call does not establish attendance throughout a meeting. Committee attendance is separate.</p><h3>Recorded votes</h3><p>{len(votes)} individual votes from named roll calls. Aggregate-only and inconsistent roll calls are not assigned to this member.</p>'
   rows=[]
   for m in votes[:10]:
    src=m['source_url']+(('#page='+str(m['source_page'])) if m['source_page'] else '')
    rows.append(f'<tr><td>{e(m["date"])}</td><td>{e(m["title"])}<details><summary>Read the motion</summary><p>{e(m["action"])}</p></details></td><td><strong>{e(m["votes"][slug])}</strong></td><td><a href="{e(src)}">Minutes'+(f', p. {m["source_page"]}' if m['source_page'] else '')+f'</a><br>{e(m.get("minutes_status",""))}</td></tr>')
   body+='<div class="table-scroll"><table class="bill-table"><thead><tr><th scope="col">Date</th><th scope="col">Measure / motion</th><th scope="col">Vote</th><th scope="col">Source</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
   body+=f'<p><a class="button primary" href="/cranston-records.html?member={slug}#votes">See the complete voting history</a></p>'
  else:
   body='<p>This member is not serving on the 2026 Cranston City Council. The incoming term begins January 4, 2027. No 2026 attendance rate or votes are assigned to this profile.</p>'
   if slug=='steven-a-stycos':body+='<p>Stycos has earlier council service. Those earlier terms are outside this 2026 import.</p>'
  body+='<p class="source"><a href="/cranston-records.html">2026 resolution archive, attendance and coverage</a>. Named lists are checked against printed tallies. Draft minutes remain labeled, and unresolved source conflicts stay in the review queue.</p>'
  section='<section class="card" id="votes"><h2>Council votes and attendance</h2>'+body+'</section>'
  s=path.read_text();s,n=re.subn(r'<section class="card" id="votes">.*?</section>',lambda _:section,s,count=1,flags=re.S);assert n==1,path
  path.write_text(s)
 print('Updated nine Cranston profile sections')
if __name__=='__main__':publish()
