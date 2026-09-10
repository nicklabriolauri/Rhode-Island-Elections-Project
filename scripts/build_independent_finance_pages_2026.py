#!/usr/bin/env python3
import json,re,html
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STATUS=ROOT/'data/post_primary_status_2026.json'; RESULTS=ROOT/'data/primary_results_2026.json'; OUT=ROOT/'finance-candidates'; INDEX=ROOT/'data/independent_finance_index_2026.json'
def slugify(s): return re.sub(r'[^a-z0-9]+','-',str(s).lower()).strip('-')
def norm(s): return re.sub(r'[^a-z0-9]+',' ',str(s).lower()).strip()
def money(x): return f"${x:,.2f}"
SUPPLEMENT={
 'Brittany M Kubicek': {'through':'June 30, 2026','receipts':16771.76,'spending':12753.07,'cash':4018.69,'liabilities':0.0,'source':'Rhode Island Board of Elections CF-2 filings (Q1 + Q2 2026)'},
 'Jon D Brien': {'through':'June 30, 2026','receipts':15352.90,'spending':1196.49,'cash':25097.59,'liabilities':22689.98,'source':'Rhode Island Board of Elections CF-2 filings (Q1 + Q2 2026)'},
 'Jean P Barros': {'through':'March 31, 2026','receipts':0.0,'spending':400.0,'cash':51656.18,'liabilities':10204.68,'source':'Rhode Island Board of Elections CF-2 filing (Q1 2026)'},
}
def apply_recount_aware_statuses(status):
    if not RESULTS.exists(): return status
    results=json.loads(RESULTS.read_text()); races={}
    for r in results.get('races',[]):
        cs=[c for c in r.get('candidates',[]) if c.get('votes') is not None]
        if len(cs)<2: continue
        cs=sorted(cs,key=lambda c:float(c.get('votes') or 0),reverse=True); total=sum(float(c.get('votes') or 0) for c in cs); diff=float(cs[0].get('votes') or 0)-float(cs[1].get('votes') or 0)
        threshold=min(total*.02,200)
        key=(str(r.get('chamber','')).lower(),int(r.get('district') or r.get('district_number') or 0),str(r.get('party','')).upper())
        races[key]={'winner':norm(cs[0].get('name')),'recount_range':diff < threshold,'diff':diff,'threshold':threshold}
    for s in status.get('candidates',[]):
        key=(str(s.get('chamber','')).lower(),int(s.get('district') or 0),str(s.get('party','')).upper()); race=races.get(key)
        if not race: continue
        if race['recount_range']:
            s['election_status']='primary_pending'; s['primary_result']='pending'; s['unopposed_general']=False; s['status_label']='Primary Result Pending / Recount Range'; s['recount_range']=True
        else:
            won=norm(s.get('name'))==race['winner']; s['recount_range']=False; s['primary_result']='won' if won else 'lost'; s['election_status']='general_candidate' if won else 'lost_primary'; s['unopposed_general']=False if not won else s.get('unopposed_general',False); s['status_label']=f"{'Won' if won else 'Lost'} {s.get('party_label','').strip()} Primary"
    return status

def page(c,fin):
    name=html.escape(c['name']); chamber='House' if c['chamber']=='house' else 'Senate'; dist=c['district']; office='State Representative' if c['chamber']=='house' else 'State Senator'
    if fin:
        lead=f"{name}'s latest 2026 filing data reports {money(fin['receipts'])} in receipts and {money(fin['spending'])} in spending. The campaign closed the reported period with {money(fin['cash'])} in cash on hand."
        quick=f"Verified RIEP filing data through {fin['through']}."; stats=[('RAISED IN 2026',fin['receipts'],'mint'),('SPENT IN 2026',fin['spending'],'coral'),('CASH ON HAND',fin['cash'],'violet'),('LIABILITIES',fin['liabilities'],'amber')]
        cards=''.join(f'<div class="stat {tone}"><span>{lab}</span><b>{money(val)}</b></div>' for lab,val,tone in stats); source=f"<div class='plain'><b>Source</b><br>{html.escape(fin['source'])}. Figures are reproduced from filed reports supplied to RIEP.</div>"
    else:
        lead=f"RIEP has created a dedicated 2026 campaign-finance page for {name}. A current 2026 filing has not yet been added to the RIEP dataset."
        quick='This finance profile is being built. Use the official Board of Elections filing system for the authoritative record while RIEP adds and verifies filings.'; cards=''; source=''
    empty='' if fin else '<div class="empty"><b>2026 filing data not yet added</b><p>This page will populate when verified filing data is added.</p><a href="https://elections.ri.gov/campaign-finance/public-info" target="_blank" rel="noopener">Open official campaign-finance search</a></div>'
    return f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{name} | Campaign Finance | Rhode Island Elections Project</title><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700;800&family=Sora:wght@500;600;700;800&display=swap" rel="stylesheet"><style>
:root{{--ink:#112036;--soft:#5f7088;--line:#d8e3f0;--navy:#13264a;--mint:#15b79e;--coral:#ff6f61;--violet:#6d5efc;--amber:#f4b740}}*{{box-sizing:border-box}}body{{margin:0;font-family:'Instrument Sans',sans-serif;color:var(--ink);background:radial-gradient(circle at top left,rgba(55,197,255,.12),transparent 26%),radial-gradient(circle at top right,rgba(109,94,252,.1),transparent 24%),linear-gradient(180deg,#f5f9ff 0%,#edf3fb 100%)}}header{{padding:22px 24px 18px;color:#fff;background:linear-gradient(180deg,#0f1c39 0%,#162a52 100%)}}.head{{max-width:1220px;margin:auto}}.brand{{font-family:Sora,sans-serif;font-size:30px;font-weight:800;letter-spacing:-.05em}}nav{{display:flex;flex-wrap:wrap;gap:10px;margin-top:16px}}nav a{{color:#fff;text-decoration:none;border:1px solid rgba(255,255,255,.18);border-radius:999px;padding:9px 14px;font-size:13px;font-weight:800}}nav a.active{{background:linear-gradient(135deg,#8ef9e5,#a5f3fc,#e0f2fe);color:#08253c}}main{{max-width:1220px;margin:auto;padding:26px 24px 44px}}.hero{{display:grid;grid-template-columns:minmax(0,1.14fr) minmax(320px,.86fr);gap:18px}}.panel{{background:rgba(255,255,255,.96);border:1px solid var(--line);border-radius:28px;box-shadow:0 24px 48px rgba(17,32,54,.08)}}.story{{padding:30px;background:radial-gradient(circle at top right,rgba(55,197,255,.16),transparent 28%),linear-gradient(135deg,#fff,#f5faff)}}.eyebrow,.badge{{display:inline-flex;align-items:center;min-height:30px;padding:0 12px;border-radius:999px;border:1px solid rgba(111,125,146,.2);background:rgba(111,125,146,.12);color:#5b687b;font-size:11px;font-weight:900;letter-spacing:.14em;text-transform:uppercase}}h1{{margin:14px 0 0;font-family:Sora,sans-serif;font-size:54px;line-height:.95;letter-spacing:-.065em;color:var(--navy)}}p{{color:var(--soft);font-size:17px;line-height:1.62}}.plain{{margin-top:18px;padding:16px 18px;border-radius:20px;background:linear-gradient(135deg,rgba(21,183,158,.12),rgba(55,197,255,.12));border:1px solid rgba(55,197,255,.18);color:#24435f;line-height:1.55}}.stats{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px}}.stat{{position:relative;padding:18px;border:1px solid #dbe6f1;border-radius:24px;background:linear-gradient(180deg,#fff,#f6faff);overflow:hidden}}.stat:before{{content:'';position:absolute;inset:0 auto 0 0;width:5px}}.stat.mint:before{{background:var(--mint)}}.stat.coral:before{{background:var(--coral)}}.stat.violet:before{{background:var(--violet)}}.stat.amber:before{{background:var(--amber)}}.stat span{{font-size:11px;font-weight:900;letter-spacing:.14em;color:#738399}}.stat b{{display:block;margin-top:10px;font-family:Sora,sans-serif;font-size:34px;color:var(--navy)}}.side{{padding:24px;border-top:6px solid #6f7d92}}.side h2{{font-family:Sora,sans-serif;font-size:34px;line-height:.98;letter-spacing:-.055em;color:var(--navy)}}.btn,.empty a{{display:inline-block;margin-top:10px;padding:12px 18px;border-radius:999px;border:1px solid #c8d9e9;background:#fff;text-decoration:none;color:var(--navy);font-weight:800}}hr{{border:0;border-top:1px solid #dbe7f2;margin:30px 0}}.empty{{margin-top:18px;padding:22px;border:1px solid #dbe6f1;border-radius:22px;background:#fbfdff}}.empty b{{font-size:22px}}@media(max-width:850px){{.hero{{grid-template-columns:1fr}}h1{{font-size:40px}}}}
</style></head><body><header><div class="head"><div class="brand">Rhode Island Elections Project</div><nav><a href="/">Home</a><a href="/map.html">Map</a><a href="/running.html">Who's Running?</a><a href="/candidates.html">Meet the Candidates</a><a class="active" href="/finance.html">Campaign Finance</a><a href="/lookup.html">Find My Precinct</a><a href="/methodology.html">Methodology</a><a href="/about.html">About</a></nav></div></header><main><div class="hero"><section class="panel story"><span class="eyebrow">Independent</span><h1>Follow the money behind {name}.</h1><p>{lead}</p><div class="plain"><b>Quick read:</b> {quick}</div><div class="stats">{cards}</div>{empty}{source}</section><aside class="panel side"><span class="badge">Independent</span><h2>{name}</h2><p>{office}<br>{chamber} District {dist}</p><a class="btn" href="/running.html?chamber={c['chamber']}&district={dist}">Back to Who's Running?</a><hr><h3>Official Source</h3><p>Campaign-finance filings are administered by the Rhode Island Board of Elections.</p><a class="btn" href="https://elections.ri.gov/campaign-finance/public-info" target="_blank" rel="noopener">Board of Elections filings</a></aside></div></main></body></html>'''
def main():
    status=apply_recount_aware_statuses(json.loads(STATUS.read_text())); STATUS.write_text(json.dumps(status,indent=2)+'\n'); OUT.mkdir(exist_ok=True); idx=[]
    for c in status.get('candidates',[]):
        if c.get('election_status')!='general_candidate' or c.get('party') not in ('IND','OTH'): continue
        fn=f"{slugify(c['candidate_id'])}.html"; fin=SUPPLEMENT.get(c['name']); (OUT/fn).write_text(page(c,fin)); idx.append({'candidate_id':c['candidate_id'],'name':c['name'],'chamber':c['chamber'],'district':c['district'],'url':f'/finance-candidates/{fn}','has_2026_data':bool(fin)})
    INDEX.write_text(json.dumps({'generated_at':'2026-09-10','candidates':idx},indent=2)+'\n'); print('generated',len(idx),'independent finance pages')
if __name__=='__main__': main()
