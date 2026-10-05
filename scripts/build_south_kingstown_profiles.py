"""Render the South Kingstown batch in the shared candidate layout, offline."""
import json,re
from pathlib import Path
from build_candidate_pages import build,esc,link
from candidate_profile_components import harmonize,section,replace_section
root=Path(__file__).resolve().parents[1]
configs=[('Virginia Susan Sosnowski','virginia-susan-sosnowski',37,'South Kingstown','sen-sosnowski@rilegislature.gov','(401) 783-7704','senate'),('Kathleen A Fogarty','kathleen-a-fogarty',35,'South Kingstown','rep-fogarty@rilegislature.gov','(401) 222-1162','house')]
for a in configs:
 build(*a);harmonize(a[1]);p=root/'candidates'/(a[1]+'.html');s=p.read_text();label='House' if a[6]=='house' else 'Senate';portrait=next(r for r in json.loads((root/'data/candidate_portrait_sources_2026.json').read_text()) if r['slug']==a[1])
 s=replace_section(s,'about',section('about','About this candidate',f'<p class="intro">{esc(a[0])} represents {label} District {a[2]} · {a[3]}.</p><div class="grid2"><div class="mini"><h3>At a glance</h3><p>Democratic incumbent in the 2026 candidate roster.</p></div><div class="mini"><h3>How to read this page</h3><p>Campaign positions, election returns, campaign finance and outside scorecards are labeled by source and period.</p></div></div><p class="source">'+link(portrait['biography_url'],'Official General Assembly biography ↗')+'</p>'))
 s=replace_section(s,'contact',section('contact','Contact &amp; district','<dl class="details">'+''.join(f'<div><dt>{k}</dt><dd>{v}</dd></div>' for k,v in [('District',f'{label} District {a[2]}'),('Community',a[3]),('Phone',link('tel:+1'+re.sub('[^0-9]','',a[5]),a[5])),('Legislative email',link('mailto:'+a[4],a[4]))])+'</dl>'))
 s=re.sub(r'<p class="photo-note">.*?</p>', '<p class="photo-note">Portrait: '+link(portrait['biography_url'],'Rhode Island General Assembly ↗')+'</p>',s)
 s=re.sub(r'(class="portrait"[^>]*?)width="[0-9]+" height="[0-9]+"',lambda m:m[1]+f'width="{portrait["width"]}" height="{portrait["height"]}"',s)
 s=s.replace('October 4, 2026','October 5, 2026')
 if a[6]=='house':s=s.replace('Senate District','House District').replace('chamber=senate','chamber=house').replace('senators/fogarty','representatives/fogarty')
 p.write_text(s)

for a in configs:
 p=root/'candidates'/(a[1]+'.html');page=p.read_text();page=replace_section(page,'primaries',section('primaries','Democratic primary history','<p class="intro">Primary returns are under construction. No primary vote total is assigned from a different race.</p><p class="source"><a href="https://electionresults.ri.gov/results/public/rhodeisland/elections/RI2026StatewidePrimary">Official 2026 Board of Elections results ↗</a></p>'))
 page=page.replace('Rhode Island Senator Kathleen','Rhode Island Representative Kathleen')
 p.write_text(page)
from build_challenger_pages import build_challenger
build_challenger('jennifer-p-nerbonne')
