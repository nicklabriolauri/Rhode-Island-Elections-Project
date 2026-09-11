#!/usr/bin/env python3
import json,re
from pathlib import Path
from datetime import date
ROOT=Path(__file__).resolve().parents[1]
BASE='https://www.rhodeislandelectionsproject.org'
run=json.loads((ROOT/'data/whos_running_2026.json').read_text())
res=json.loads((ROOT/'data/primary_results_2026.json').read_text())
urls=['/','/primary-results.html','/running.html','/ballot.html','/finance.html','/endorsements.html','/lookup.html','/map.html','/methodology.html','/about.html','/support.html']
for chamber in ('house','senate'):
    for district in run.get('chambers',{}).get(chamber,{}):
        urls.append(f'/races/{chamber}-{district}.html')
def party_slug(p):
    p=str(p or '').lower()
    if p.startswith('dem'): return 'democratic'
    if p.startswith('rep'): return 'republican'
    return re.sub(r'[^a-z]+','-',p).strip('-') or 'primary'
for race in res.get('races',[]):
    if race.get('contested') is False: continue
    urls.append(f"/races/{str(race.get('chamber','')).lower()}-{int(race.get('district'))}-{party_slug(race.get('party'))}.html")
seen=[]
for u in urls:
    if u not in seen: seen.append(u)
lastmod=date.today().isoformat()
lines=['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for u in seen:
    lines += ['  <url>',f'    <loc>{BASE}{u}</loc>',f'    <lastmod>{lastmod}</lastmod>','  </url>']
lines.append('</urlset>')
(ROOT/'sitemap.xml').write_text('\n'.join(lines)+'\n')
print(f'wrote {len(seen)} sitemap URLs')
