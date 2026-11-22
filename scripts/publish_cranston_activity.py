"""Publish frozen provisional activity scores after rebuilding the reviewed snapshot."""
from pathlib import Path
from html import escape as e
import json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
PROFILE_IDS=['avery-therese-mangahas','sara-jane-haupt','andy-m-andujar','frank-j-ritz-jr','michael-a-traficante','daniel-robert-wall','emilia-vaziri','steven-a-stycos','kristen-e-haroian']
def profile_card(slug,data):
 m=next((m for m in data['members'] if m['id']==slug),None)
 if not m:
  body='<p class="intro"><strong>2026 activity score: Not applicable.</strong></p><p>This individual is not part of the nine-member 2026 council cohort. No score or rank is assigned, and no predecessor’s activity is transferred to this profile. The incoming term starts January 4, 2027.</p>'
  if slug=='steven-a-stycos':body+='<p>Earlier council service is outside this 2026 snapshot.</p>'
 else:
  tied=sum(x['rank']==m['rank'] for x in data['members'])>1
  body='<p class="intro">2026 service: <strong>'+e(m['office_2026'])+'</strong>'+(' · '+e(m['leadership']) if m['leadership'] else '')+'.</p>'
  difference=m['index']-100
  comparison=f"{abs(difference):.1f}%"
  direction='above' if difference>=0 else 'below'
  peers=[x['name'] for x in data['members'] if x['rank']==m['rank'] and x['id']!=slug]
  rank_label=('Tied #' if tied else '#')+str(m['rank'])+' of 9'
  body+='<div class="activity-score-grid"><div class="activity-rank"><b>'+rank_label+'</b><span>Documented sponsorship activity</span><span class="activity-comparison">'+comparison+' '+direction+' the council average in activity points</span></div><div><b>'+str(m['points'])+'</b><span>Activity points from named sponsorships</span></div></div>'
  if m['rank']==1:
   body+='<p class="activity-rank-note"><strong>Tied #1 in documented sponsorship activity</strong>'+(' with '+e(' and '.join(peers)) if peers else '')+' among the nine 2026 council members in this partial record. This is an activity ranking, not a finding of overall effectiveness.</p>'
  body+='<div class="activity-explainer"><h3>What does this score mean?</h3><p>'+e(m['name'])+' has <strong>'+str(m['points'])+' activity points</strong>. The nine-member council average is <strong>'+f'{data["mean_points"]:.1f}'+' points</strong>. That puts this score <strong>'+comparison+' '+direction+' average</strong> under the same scoring rules.</p><details><summary>How the '+f'{m["index"]:.1f}'+' index is calculated</summary><p>We set the council average to 100 so scores are easier to compare. A score of 150 means 50% more activity points than average; 100 means average; 50 means half the average.</p><p><strong>'+str(m['points'])+' ÷ '+f'{data["mean_points"]:.6f}'+'… × 100 = '+f'{m["index"]:.1f}'+'</strong> (rounded; the calculation uses the unrounded average).</p><p>The index compares weighted sponsorship points. It does not mean '+f'{m["index"]:.1f}'+'% effective, and it does not measure the quality or impact of policies.</p></details></div>'
  body+='<div class="table-scroll"><table class="bill-table"><caption>Sponsorship breakdown · full credit for each named sponsor</caption><thead><tr><th scope="col">Measure tier</th><th scope="col">Sponsorships</th><th scope="col">Points each</th><th scope="col">Points</th></tr></thead><tbody>'
  for key,label,weight in [('symbolic','Symbolic and advocacy',1),('administrative','Property / administrative approvals',2),('substantive','Local policy, fiscal measures and ordinances',5)]:
   t=m['tiers'][key];body+=f'<tr><th scope="row">{label}</th><td>{t["count"]}</td><td>{weight}</td><td>{t["points"]}</td></tr>'
  body+='</tbody></table></div><p>'+str(m['additional_cosponsorships'])+' additional explicit cosponsorships are recorded separately and add no points. A jointly sponsored symbolic resolution earns each named sponsor <strong>1 full point</strong>.</p>'
  body+='<details><summary>Activity by primary topic</summary><ul>'+''.join('<li>'+e(t['topic'])+': <strong>'+str(t['points'])+' points</strong></li>' for t in m['topics'])+'</ul><p class="source">Secondary topic tags support filtering but do not add points.</p></details><p><a class="button primary" href="/cranston-activity-index-test.html?member='+e(slug)+'#audit">Inspect measures, topic tags and source minutes</a></p>'
 body+='<p class="activity-caveat"><strong>Provisional · partial extracted records.</strong> This measures documented sponsorship activity, not overall effectiveness, policy quality or constituent service. Attribution gaps can affect members differently. Index = 100 × points ÷ the nine-member mean; it is not a percentage. Leadership roles are context, with no numerical adjustment.</p><p class="source">Reviewed November 22, 2026 · '+str(data['meeting_count'])+' available full-council meeting records · <a href="/cranston-activity.html">Full ranking and methodology</a> · <a href="/data/cranston/activity-index-ranking-2026.csv" download>Download ranking (CSV)</a></p>'
 return '<section class="card" id="activity-index"><h2>Legislative Activity Index · 2026 pilot</h2>'+body+'</section>'
def render_profile_activity(text,slug):
 snapshot=ROOT/'data/cranston/activity-index-scores-2026.json'
 if not snapshot.exists():return text
 data=json.loads(snapshot.read_text())
 text=re.sub(r'<section class="card" id="activity-index">.*?</section>\s*','',text,flags=re.S)
 anchor='<section class="card" id="sponsorship">'
 if anchor not in text:raise ValueError('Missing sponsorship section '+slug)
 text=text.replace(anchor,profile_card(slug,data)+'\n'+anchor,1)
 if 'href="#activity-index"' not in text:text=text.replace('<p class="source municipal-record-links">','<p class="source municipal-record-links"><a href="#activity-index">Activity index</a>',1)
 return re.sub(r'municipal-profile.css\?v=[^"\s]+','municipal-profile.css?v=20261122-combined-scores',text)
def ranking_page(data):
 rows=[]
 for m in data['members']:
  href=m['profile_url'] or '/cranston-sponsorship.html?member='+m['id']+'#measures'
  tied=sum(x['rank']==m['rank'] for x in data['members'])>1
  cells=[('Joint ' if tied else '')+str(m['rank']),'<a href="'+e(href)+'">'+e(m['name'])+'</a>',e(m['office_2026'])+('<small>'+e(m['leadership'])+'</small>' if m['leadership'] else ''),str(m['tiers']['symbolic']['count']),str(m['tiers']['administrative']['count']),str(m['tiers']['substantive']['count']),str(m['points']),f'{m["index"]:.1f}']
  rows.append('<tr id="'+e(m['id'])+'">'+''.join(('<th scope="row">' if i==1 else '<td>')+c+('</th>' if i==1 else '</td>') for i,c in enumerate(cells))+'</tr>')
 template=(ROOT/'templates/cranston-activity.html').read_text()
 return template.replace('<!-- RANKING_ROWS -->',''.join(rows)).replace('<!-- MEAN -->',f'{data["mean_points"]:.3f}').replace('<!-- COVERAGE -->',str(data['meeting_count'])+' available meeting records · '+str(data['measure_count'])+' identified measures').replace('<!-- VERSION -->',e(data['version']))
def publish():
 subprocess.run(['node',str(ROOT/'scripts/export_cranston_activity.mjs')],check=True)
 data=json.loads((ROOT/'data/cranston/activity-index-scores-2026.json').read_text())
 for slug in PROFILE_IDS:
  path=ROOT/'candidates'/(slug+'.html');path.write_text(render_profile_activity(path.read_text(),slug))
 (ROOT/'cranston-activity.html').write_text(ranking_page(data))
 path=ROOT/'cranston-sponsorship.html';text=path.read_text()
 if 'href="/cranston-activity.html"' not in text:text=text.replace('<section class="panel">','<p><a href="/cranston-activity.html">See the provisional 1–2–5 activity ranking and methodology</a></p><section class="panel">',1)
 path.write_text(text)
if __name__=='__main__':publish()


