#!/usr/bin/env python3
import json, html, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RUN=json.loads((ROOT/'data/whos_running_2026.json').read_text())
PRECINCT_RUN=json.loads((ROOT/'data/whos_running_2026_precincts.json').read_text())
RES=json.loads((ROOT/'data/primary_results_2026.json').read_text())
OUT=ROOT/'races'; OUT.mkdir(exist_ok=True)

def normparty(p):
    p=str(p or '').lower()
    return 'democratic' if p.startswith('dem') else 'republican' if p.startswith('rep') else re.sub(r'[^a-z]+','-',p).strip('-') or 'primary'
def partyclass(p): return 'dem' if normparty(p)=='democratic' else 'rep' if normparty(p)=='republican' else 'oth'
def esc(x): return html.escape(str(x if x is not None else ''))
def page(r):
    chamber=str(r['chamber']).lower(); d=int(r['district']); party=normparty(r.get('party')); label='State House' if chamber=='house' else 'State Senate'
    title=f'{label} District {d} {party.title()} Primary | 2026 Rhode Island Election | RIEP'
    candidates=sorted(r.get('candidates',[]),key=lambda c:float(c.get('votes') or 0),reverse=True)
    total=sum(float(c.get('votes') or 0) for c in candidates)
    rows=''
    fresh_records=RUN.get('chambers',{}).get(chamber,{}).get(str(d),{})
    snap_records=PRECINCT_RUN.get('chambers',{}).get(chamber,{}).get(str(d),{})
    primary_records=list(fresh_records.get('primary_candidates') or fresh_records.get('candidates') or []) + list(snap_records.get('candidates') or [])
    def nname(value): return re.sub(r'[^a-z0-9]+',' ',str(value or '').lower()).strip()
    byname={}
    for record in primary_records:
        key=nname(record.get('name'))
        if key not in byname or (not byname[key].get('home_precinct_code') and record.get('home_precinct_code')):
            byname[key]=record
    map_candidates=[]
    candidate_meta={}
    for c in candidates:
        rc=byname.get(nname(c.get('name')),{})
        candidate_meta[nname(c.get('name'))]=rc
        code=rc.get('home_precinct_code')
        if code:
            map_candidates.append({'name':c.get('name',''),'code':str(code),'precinct':rc.get('home_precinct_name',''),'hometown':rc.get('hometown','')})
    map_candidates_json=json.dumps(map_candidates).replace('</','<\\/')
    top_votes=float(candidates[0].get('votes') or 0) if candidates else 0
    second_votes=float(candidates[1].get('votes') or 0) if len(candidates)>1 else 0
    margin_votes=max(0,top_votes-second_votes)
    margin_pct=((margin_votes/total)*100) if total else 0
    threshold=min(total*.02,200) if total else 0
    called=bool(len(candidates)>1 and margin_votes>=threshold and top_votes>second_votes)
    status_label='CALLED' if called else 'RECOUNT RANGE'
    for i,c in enumerate(candidates):
        v=float(c.get('votes') or 0); pct=c.get('pct')
        if pct is None and total: pct=v/total*100
        meta=candidate_meta.get(nname(c.get('name')),{})
        precinct=meta.get('home_precinct_code')
        hometown=meta.get('hometown')
        winner=(i==0 and called)
        cls='candidate winner' if winner else 'candidate'
        badge='<span class="winner-badge">WINNER</span>' if winner else ''
        meta_bits=[f"{int(v):,} votes"]
        if precinct: meta_bits.append(f"Home precinct {esc(precinct)}")
        if hometown: meta_bits.append(esc(hometown))
        detail=' · '.join(meta_bits)
        rows+=f'''<article class="{cls}"><div><div class="candidate-name-line"><h2>{esc(c.get('name'))}</h2>{badge}</div><p>{detail}</p></div><strong>{float(pct):.1f}%</strong></article>''' if pct is not None else f'''<article class="{cls}"><div><div class="candidate-name-line"><h2>{esc(c.get('name'))}</h2>{badge}</div><p>Vote total pending</p></div></article>'''
    race_summary=f"{status_label} · {int(total):,} votes cast · margin {int(margin_votes):,} votes ({margin_pct:.1f} pts)" if total else status_label
    return f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="Stable RIEP page for the 2026 {party.title()} primary in Rhode Island {label} District {d}, with district map, candidates, and election results.">
<meta name="robots" content="index,follow"><link rel="canonical" href="https://www.rhodeislandelectionsproject.org/races/{chamber}-{d}-{party}.html">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>:root{{--navy:#111c3d;--navy2:#172554;--text:#0f172a;--muted:#64748b;--line:#e2e8f0;--bg:#f8fafc}}*{{box-sizing:border-box}}body{{margin:0;font-family:Arial,Helvetica,sans-serif;color:var(--text);background:var(--bg)}}header{{background:linear-gradient(135deg,#0f172a,#172554);color:#fff;padding:18px 24px}}.nav{{max-width:1200px;margin:auto;display:flex;justify-content:space-between;gap:18px;flex-wrap:wrap}}a{{color:inherit;text-decoration:none}}nav a{{margin-left:14px;font-weight:700;font-size:14px}}.hero{{background:linear-gradient(135deg,#0f172a,#172554);color:#fff;padding:48px 24px 58px}}.wrap{{max-width:1200px;margin:auto}}.eyebrow{{font-size:11px;font-weight:900;letter-spacing:.13em;text-transform:uppercase;color:#bfdbfe}}h1{{font-size:clamp(38px,6vw,68px);line-height:1;margin:10px 0 12px;letter-spacing:-.045em}}.hero p{{color:#dbeafe;font-size:18px}}main{{max-width:1200px;margin:-28px auto 50px;padding:0 18px}}.grid{{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(320px,.65fr);gap:18px}}.panel{{background:#fff;border:1px solid var(--line);border-radius:22px;box-shadow:0 16px 40px rgba(15,23,42,.08);padding:22px}}#raceMap{{height:520px;border-radius:16px;background:#e2e8f0}}.candidate{{display:flex;justify-content:space-between;gap:15px;align-items:center;border-top:1px solid var(--line);padding:18px 16px;margin:0 -4px}}.candidate:first-child{{border-top:0}}.candidate h2{{font-size:20px;margin:0}}.candidate p{{margin:6px 0 0;color:var(--muted);line-height:1.45}}.candidate strong{{font-size:24px}}.candidate.winner{{background:linear-gradient(135deg,#172554,#1e3a8a);color:#fff;border-radius:16px;border-top:0;margin:10px -4px;padding:18px 16px;box-shadow:0 10px 26px rgba(23,37,84,.18)}}.candidate.winner h2,.candidate.winner strong{{color:#fff}}.candidate.winner p{{color:#dbeafe}}.candidate-name-line{{display:flex;align-items:center;gap:9px;flex-wrap:wrap}}.winner-badge{{display:inline-flex;padding:4px 7px;border-radius:999px;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.32);font-size:10px;font-weight:900;letter-spacing:.08em}}.race-summary{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:0 0 12px;padding:12px 14px;border-radius:14px;background:#f1f5f9;color:#475569;font-size:13px;font-weight:800}}.party{{display:inline-flex;padding:6px 9px;border-radius:999px;font-size:11px;font-weight:900;text-transform:uppercase}}.party.dem{{background:#dbeafe;color:#1d4ed8}}.party.rep{{background:#fee2e2;color:#b91c1c}}.note{{color:var(--muted);line-height:1.55}}.map-key{{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}}.map-key span{{display:inline-flex;align-items:center;gap:7px;padding:7px 10px;border:1px solid #cbd5e1;border-radius:999px;color:#475569;font-size:13px;font-weight:700}}.map-dot{{width:10px;height:10px;border-radius:50%;background:#fff;border:2px solid #0f766e}}@media(max-width:860px){{.grid{{grid-template-columns:1fr}}#raceMap{{height:420px}}}}</style></head>
<body data-chamber="{chamber}" data-district="{d}"><header><div class="nav"><strong><a href="/">Rhode Island Elections Project</a></strong><nav><a href="/primary-results.html">Primary Results</a><a href="/running.html">Who's Running?</a><a href="/map.html">Maps & Data</a></nav></div></header>
<section class="hero"><div class="wrap"><div class="eyebrow">2026 Rhode Island primary election</div><h1>{label} District {d}</h1><p><span class="party {partyclass(party)}">{party.title()} Primary</span></p></div></section>
<main><div class="grid"><section class="panel"><h2>District map</h2><div id="raceMap"></div><div id="mapKey" class="map-key"></div><p class="note" id="mapNote">District boundary for this primary race.</p></section><section class="panel"><h2>Primary results</h2><div class="race-summary">{esc(race_summary)}</div>{rows}<p class="note"><strong>Unofficial results.</strong> Source: Rhode Island Board of Elections. Candidate home precincts come from Rhode Island Department of State filing data and are shown without residential addresses.</p></section></div></main>
<script>const chamber=document.body.dataset.chamber,d=Number(document.body.dataset.district),url=chamber==='house'?'/data/house_new.geojson':'/data/senate_new.geojson',homePrecincts={map_candidates_json};const map=L.map('raceMap',{{scrollWheelZoom:false}});L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:18,opacity:.28,attribution:'&copy; OpenStreetMap contributors'}}).addTo(map);const precinctCode=f=>String((f.properties||{{}}).DISTRICT||(f.properties||{{}}).PRECINCTS||(f.properties||{{}}).PRECINCT||(f.properties||{{}}).PRECINCT_ID||'').trim();Promise.all([fetch(url).then(r=>r.json()),fetch('/data/ri_turnout_2024_precinct.geojson').then(r=>r.json()).catch(()=>({{features:[]}}))]).then(([g,pg])=>{{const f=g.features.find(f=>{{const p=f.properties||{{}},raw=p.district_number??p.DIST_NUM??p.SLDUST??p.DISTRICT??p.District??p.NAME??p.NAMELSAD,m=String(raw??'').match(/\\d+/);return m&&Number(m[0])===d}});if(f){{const l=L.geoJSON(f,{{style:{{color:'#172554',weight:4,fillColor:'#dbeafe',fillOpacity:.42}}}}).addTo(map);map.fitBounds(l.getBounds(),{{padding:[18,18]}})}}else map.setView([41.68,-71.52],9);const wanted=new Map();homePrecincts.forEach(c=>{{if(!wanted.has(c.code))wanted.set(c.code,[]);wanted.get(c.code).push(c)}});const mapped=new Set();(pg.features||[]).forEach(p=>{{const code=precinctCode(p),cs=wanted.get(code);if(!cs||!cs.length)return;const lyr=L.geoJSON(p,{{style:{{color:'#0f766e',weight:2,fillColor:'#99f6e4',fillOpacity:.36}}}}).addTo(map),center=lyr.getBounds().getCenter();cs.forEach(c=>mapped.add(c.name));const popup=cs.map(c=>'<strong>'+c.name+'</strong>').join('<br>')+'<br>Public filing home precinct: '+code+'<br><small>Exact residential addresses are not displayed.</small>';L.circleMarker(center,{{radius:7,color:'#0f766e',weight:2,fillColor:'#fff',fillOpacity:1}}).addTo(map).bindPopup(popup)}});if(homePrecincts.length){{document.getElementById('mapNote').textContent='Map shows the legislative district boundary and every candidate’s public filing home precinct. Candidates sharing a precinct are grouped on one marker. Exact residential addresses are intentionally not displayed.';document.getElementById('mapKey').innerHTML=homePrecincts.map(c=>'<span><i class="map-dot"></i>'+c.name+' · precinct '+c.code+'</span>').join('')}}}});</script></body></html>'''

n=0
for r in RES.get('races',[]):
    if r.get('contested') is False: continue
    fn=f"{str(r['chamber']).lower()}-{int(r['district'])}-{normparty(r.get('party'))}.html"
    (OUT/fn).write_text(page(r)); n+=1
print('generated',n,'primary race pages')
