"""Attach the shared Senate voting-pattern widget to all modeled senators' profiles.
Use the Burke section as the shared explanation; retain candidate-specific highlights.
Re-running replaces the feature section rather than duplicating it.
"""
import html,json,re,urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CANDIDATES=ROOT/'candidates'
data=json.loads((CANDIDATES/'voting-patterns/positions.json').read_text())
burke=(CANDIDATES/'john-burke.html').read_text()
pattern=r'<section\b[^>]*\bid="voting-patterns"[^>]*>.*?</section>'
template=re.search(pattern,burke,re.S).group(0)
css='<link rel="stylesheet" href="voting-patterns/pilot.css?v=20261006">'
js='<script src="voting-patterns/pilot.js?v=20261006-labels" defer></script>'
profiles=[]
for member in data['positions']:
 name=member['name'];slug=re.sub('[^a-z0-9]+','-',name.lower()).strip('-');p=CANDIDATES/(slug+'.html')
 assert p.exists(),f'Missing senator profile: {name}'
 s=p.read_text();assert f'Rhode Island Senate · District {member["district"]}' in s, f'District mismatch: {name}'
 section=template.replace('John Burke',html.escape(name,quote=True)).replace('John%20Burke',urllib.parse.quote(name,safe=''))
 if re.search(pattern,s,re.S):s=re.sub(pattern,lambda _:section,s,count=1,flags=re.S)
 else:
  assert '<section class="card" id="bills">' in s,name
  s=s.replace('<section class="card" id="bills">',section+'<section class="card" id="bills">',1)
 if 'href="#voting-patterns"' not in s:s=s.replace('<a href="#bills">','<a href="#voting-patterns">Voting patterns</a><a href="#bills">',1)
 if 'href="voting-patterns/pilot.css' not in s:s=s.replace('</head>',css+'</head>',1)
 if 'src="voting-patterns/pilot.js' not in s:s=s.replace('</body>',js+'</body>',1)
 assert s.count('id="voting-patterns"')==1 and s.count('data-voting-widget')==1,name
 if s!=p.read_text():p.write_text(s)
 profiles.append(dict(path=str(p.relative_to(ROOT)),name=name,district=member['district']))
assert len(profiles)==38
print(json.dumps(profiles))
