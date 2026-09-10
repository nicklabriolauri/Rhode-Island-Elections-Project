#!/usr/bin/env python3
import json,re,html
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STATUS=ROOT/'data/post_primary_status_2026.json'
RESULTS=ROOT/'data/primary_results_2026.json'
OUT=ROOT/'finance-candidates'
INDEX=ROOT/'data/independent_finance_index_2026.json'

def slugify(s): return re.sub(r'[^a-z0-9]+','-',str(s).lower()).strip('-')
def norm(s): return re.sub(r'[^a-z0-9]+',' ',str(s).lower()).strip()
def money(x): return f"${x:,.2f}"

# Verified from RI BOE CF-2 reports supplied to RIEP on 2026-09-10.
SUPPLEMENT={
 'Brittany M Kubicek': {'through':'June 30, 2026','receipts':16771.76,'spending':12753.07,'cash':4018.69,'liabilities':0.0,'source':'Rhode Island Board of Elections CF-2 filings (Q1 + Q2 2026)'},
 'Jon D Brien': {'through':'June 30, 2026','receipts':15352.90,'spending':1196.49,'cash':25097.59,'liabilities':22689.98,'source':'Rhode Island Board of Elections CF-2 filings (Q1 + Q2 2026)'},
 'Jean P Barros': {'through':'March 31, 2026','receipts':0.0,'spending':400.0,'cash':51656.18,'liabilities':10204.68,'source':'Rhode Island Board of Elections CF-2 filing (Q1 2026)'},
}

def apply_recount_aware_statuses(status):
    if not RESULTS.exists(): return status
    results=json.loads(RESULTS.read_text())
    # Rhode Island law allows a candidate trailing by 5% or less to petition for a recount procedure.
    # Keep those races pending; mark clear races when margin exceeds 5 percentage points.
    bykey={}
    for r in results.get('races',[]):
        chamber=str(r.get('chamber','')).lower(); district=int(r.get('district') or r.get('district_number') or 0)
        party=str(r.get('party','')).upper()
        cs=[c for c in r.get('candidates',[]) if c.get('votes') is not None]
        if len(cs)<2: continue
        cs=sorted(cs,key=lambda c:(c.get('votes') or 0),reverse=True)
        top,second=cs[0],cs[1]
        p1=float(top.get('pct') or 0); p2=float(second.get('pct') or 0)
        bykey[(chamber,district,party)]={'winner':norm(top.get('name')),'margin_pct':p1-p2}
    for s in status.get('candidates',[]):
        key=(str(s.get('chamber','')).lower(),int(s.get('district') or 0),str(s.get('party','')).upper())
        race=bykey.get(key)
        if not race: continue
        if race['margin_pct'] <= 5.0:
            s['election_status']='primary_pending'; s['primary_result']='pending'; s['unopposed_general']=False
            s['status_label']='Primary Result Pending / Recount Window'
        else:
            if norm(s.get('name'))==race['winner']:
                s['election_status']='general_candidate'; s['primary_result']='won'
                s['status_label']=f"Won {s.get('party_label','').strip()} Primary".replace('Democratic Primary','Democratic Primary').replace('Republican Primary','Republican Primary')
            else:
                s['election_status']='lost_primary'; s['primary_result']='lost'; s['unopposed_general']=False
                s['status_label']=f"Lost {s.get('party_label','').strip()} Primary"
    return status

def page(c,fin):
    name=html.escape(c['name']); chamber='House' if c['chamber']=='house' else 'Senate'; dist=c['district']
    office='State Representative' if c['chamber']=='house' else 'State Senator'
    party='Independent' if c.get('party') in ('IND','OTH') else html.escape(c.get('party_label','Other'))
    if fin:
        lead=f"The latest 2026 filing data added to RIEP reports {money(fin['receipts'])} in receipts and {money(fin['spending'])} in spending. The campaign reported {money(fin['cash'])} in cash on hand through {fin['through']}."
        quick=f"RIEP currently has verified 2026 campaign-finance data through {fin['through']}."
        metrics=f'''<div class="metrics"><div><span>RAISED IN 2026</span><b>{money(fin['receipts'])}</b></div><div><span>SPENT IN 2026</span><b>{money(fin['spending'])}</b></div><div><span>CASH ON HAND</span><b>{money(fin['cash'])}</b></div><div><span>LIABILITIES</span><b>{money(fin['liabilities'])}</b></div></div>'''
        source=f"<p class='source'>Source: {html.escape(fin['source'])}. Figures are reproduced from candidate filings supplied to RIEP.</p>"
    else:
        lead="RIEP has created this campaign-finance profile so every 2026 general-election candidate has a dedicated finance page. No current 2026 filing has yet been added to the RIEP dataset for this candidate."
        quick="No current 2026 filing has yet been added to RIEP. This page will populate as verified filings are obtained and checked."
        metrics='<div class="empty"><b>2026 filing data not yet added</b><p>Use the official Rhode Island Board of Elections public filing system for the authoritative record while this profile is being completed.</p><a href="https://elections.ri.gov/campaign-finance/public-info" target="_blank" rel="noopener">Open official campaign-finance search</a></div>'
        source=""
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{name} | Campaign Finance | Rhode Island Elections Project</title><meta name="description" content="2026 campaign finance profile for {name}, {chamber} District {dist}, Rhode Island."><style>
body{{margin:0;font-family:Arial,sans-serif;background:#eef8ff;color:#10224d}}header{{background:#122957;color:#fff;padding:22px 5vw}}nav a{{color:#fff;text-decoration:none;margin-right:20px;font-weight:700}}main{{max-width:1320px;margin:32px auto;padding:0 24px;display:grid;grid-template-columns:1.15fr .85fr;gap:26px}}.panel{{background:#fff;border:1px solid #cfe1f2;border-radius:28px;padding:36px;box-shadow:0 16px 45px rgba(23,63,115,.08)}}h1{{font-size:56px;line-height:1.02;margin:0 0 20px;letter-spacing:-.045em}}h2{{font-size:38px;margin:5px 0 14px}}p{{font-size:18px;line-height:1.55;color:#536784}}.badge{{display:inline-block;padding:8px 15px;border-radius:999px;background:#f1f3f5;border:1px solid #cfd5dc;color:#505a67;font-weight:800;text-transform:uppercase;font-size:13px}}.notice{{margin:26px 0;padding:22px;border-radius:20px;background:#e8f8ff;border:1px solid #9eddf5}}.metrics{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:24px}}.metrics div,.empty{{border:1px solid #cfe1f2;border-radius:20px;padding:22px;background:#fbfdff}}.metrics span{{display:block;font-size:12px;font-weight:800;color:#6b7e99;letter-spacing:.08em}}.metrics b{{display:block;font-size:28px;margin-top:8px}}.empty b{{font-size:24px}}a.btn,.empty a{{display:inline-block;padding:12px 18px;border-radius:999px;border:1px solid #bcd2e8;text-decoration:none;color:#10224d;font-weight:800;background:#fff}}.source{{font-size:13px}}@media(max-width:850px){{main{{grid-template-columns:1fr}}h1{{font-size:40px}}}}
</style></head><body><header><nav><a href="/">Home</a><a href="/running.html">Who's Running?</a><a href="/finance.html">Campaign Finance</a><a href="/methodology.html">Methodology</a></nav></header><main><section class="panel"><span class="badge">{party}</span><h1>Follow the money behind {name}.</h1><p>{lead}</p><div class="notice"><b>CAMPAIGN FINANCE PROFILE</b><p>{quick}</p></div>{metrics}{source}</section><aside class="panel"><span class="badge">{party}</span><h2>{name}</h2><p>{office}<br>{chamber} District {dist}</p><a class="btn" href="/running.html?chamber={c['chamber']}&district={dist}">Back to Who's Running?</a><hr style="border:0;border-top:1px solid #dbe7f2;margin:30px 0"><h3>Official source</h3><p>Campaign-finance filings are administered by the Rhode Island Board of Elections.</p><a class="btn" href="https://elections.ri.gov/campaign-finance/public-info" target="_blank" rel="noopener">Board of Elections filings</a></aside></main></body></html>'''

def main():
    status=json.loads(STATUS.read_text())
    status=apply_recount_aware_statuses(status)
    STATUS.write_text(json.dumps(status,indent=2)+'\n')
    OUT.mkdir(exist_ok=True)
    idx=[]
    for c in status.get('candidates',[]):
        if c.get('election_status')!='general_candidate' or c.get('party') not in ('IND','OTH'): continue
        slug=slugify(c['candidate_id'])
        fn=f'{slug}.html'; fin=SUPPLEMENT.get(c['name'])
        (OUT/fn).write_text(page(c,fin))
        idx.append({'candidate_id':c['candidate_id'],'name':c['name'],'chamber':c['chamber'],'district':c['district'],'url':f'/finance-candidates/{fn}','has_2026_data':bool(fin)})
    INDEX.write_text(json.dumps({'generated_at':'2026-09-10','candidates':idx},indent=2)+'\n')
    print('generated',len(idx),'independent finance pages')
if __name__=='__main__': main()
