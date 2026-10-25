"""Render attributed BFFI labels by candidate identity, never by district alone."""
import html,json,re
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CATEGORIES={'For','Against','Mixed','N/A'}
def esc(value):return html.escape(str(value),quote=True)
def payload():return json.loads((ROOT/'data/bffi_ratings_2026.json').read_text())
def card(rec):
 data=payload();matches=[r for r in data['candidates'] if r['candidate_id']==rec['candidate_id']]
 if not matches:return ''
 assert len(matches)==1
 r=matches[0]
 assert r['chamber']==rec['chamber'] and r['district_number']==int(rec['district_number'])
 rating=r['rating'];assert rating in CATEGORIES or rating is None
 conflict=r['status']=='conflicting_source_entries'
 label='Conflicting entries' if conflict else rating or 'Not listed';category={'For':'for','Against':'against','Mixed':'mixed','N/A':'na',None:'unlisted'}[rating]
 meaning={'For':'The Womxn Project places this candidate in its category for support of reproductive rights, gender-affirming care and LGBTQ+ rights.',
 'Against':'The Womxn Project places this candidate in its category for opposition to policies supporting reproductive and LGBTQ+ rights.',
 'Mixed':'The Womxn Project reports conflicting information that the candidate has not clarified through its survey.',
 'N/A':'The Womxn Project reports that it could not obtain the information needed for a rating. N/A indicates missing information; it is not an Against rating.',
 None:'No entry for this candidate was found in the published municipal BFFI tables checked for this snapshot. This is not an N/A or Against rating assigned by The Womxn Project.'}[rating]
 if conflict:meaning='The Womxn Project’s municipal tables publish different labels for this candidate. RIEP displays each entry below and has not selected one as definitive.'
 sources=r['sources'];links=' · '.join(f'<a href="{esc(s["source_url"])}">{esc(s["municipality"])} candidate listing ↗</a>' for s in sources)
 if not links:links=f'<a href="{esc(data["results_url"])}">Published BFFI candidate listings ↗</a>'
 stamp=date.fromisoformat(data['retrieved_at']).strftime('%B %d, %Y').replace(' 0',' ')
 evidence=''
 if sources:
  evidence='<p>Published rating tables: '+' · '.join(f'<a href="{esc(s["source_image_url"])}">{esc(s["municipality"])} table ↗</a>' for s in sources)+'</p>'
 if conflict:
  evidence='<ul class="bffi-source-list">'+''.join(f'<li><strong>{esc(x["municipality"])}: {esc(x["rating"])}</strong> · <a href="{esc(x["source_url"])}">Published listing ↗</a> · <a href="{esc(x["source_image_url"])}">Rating table ↗</a></li>' for x in sources)+'</ul>'
 return f'''<section class="bffi-card bffi-{category}" id="bffi-scorecard" aria-labelledby="bffi-title" data-bffi-rating="{esc(label)}"><div class="bffi-head"><div><p class="eyebrow">The Womxn Project · {esc(data['edition'])}</p><h3 id="bffi-title">{esc(data['index_name'])}</h3><p class="bffi-subtitle">Reproductive rights and LGBTQ+ rights · BFFI</p></div><span class="bffi-badge" aria-label="The Womxn Project rating: {esc(label)}">{esc(label)}</span></div><p><strong>{esc(r['candidate_name'])}: {esc(label)}.</strong> {meaning}</p>{evidence if conflict else ''}<details><summary>What the rating means &amp; how it is assigned</summary><p>The index reflects The Womxn Project’s assessment of candidate positions on reproductive rights and LGBTQ+ rights. Its staff and volunteers send a two-question survey, review public statements and social media, examine relevant voting records, and contact candidates about their findings. The tables do not specify whether an individual label is based on a survey response, public-source research or both.</p><dl class="bffi-key"><dt>For</dt><dd>Support for reproductive rights, gender-affirming care and LGBTQ+ rights under the organization’s definition.</dd><dt>Against</dt><dd>The organization finds opposition to policies supporting reproductive and LGBTQ+ rights.</dd><dt>Mixed</dt><dd>Conflicting information that the candidate has not clarified through the survey.</dd><dt>N/A</dt><dd>The organization could not obtain the information needed for a rating.</dd></dl><p>This is an outside categorical assessment, not an RIEP score or endorsement. RIEP does not combine it with legislative effectiveness or other scorecards, and does not infer a rating from party or incumbency.</p>{evidence if not conflict else ''}</details><p class="source">{links} · <a href="{esc(data['methodology_url'])}">BFFI methodology ↗</a> · Checked {stamp}. This is a dated snapshot of the published tables.</p></section>'''

def styles(page,rec):
 if not card(rec):return page
 page=re.sub(r'href="bffi-scorecard.css(?:\?[^\"]*)?"','href="bffi-scorecard.css?v=20261025-all"',page)
 if 'href="bffi-scorecard.css' not in page:page=page.replace('</head>','<link rel="stylesheet" href="bffi-scorecard.css?v=20261025-all">\n</head>')
 if 'href="#bffi-scorecard"' not in page:page=page.replace('</nav>','<a href="#bffi-scorecard">Womxn Project rating</a></nav>',1)
 return page
