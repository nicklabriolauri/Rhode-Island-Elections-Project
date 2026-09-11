#!/usr/bin/env python3
import json,re
from pathlib import Path
from datetime import date
ROOT=Path(__file__).resolve().parents[1]
FILES=[ROOT/'data/candidate_research_2026.json',ROOT/'data/candidate_research_2026_with_endorsements.json']

def norm(s): return re.sub(r'[^a-z0-9]+',' ',str(s or '').lower()).strip()

def add_end(c,org,url):
    ends=c.setdefault('endorsements',[])
    if not any(norm(e.get('name') or e.get('organization'))==norm(org) for e in ends):
        ends.append({'organization':org,'source_url':url,'source_type':'endorser_official_source','date_checked':'2026-09-11'})

CLEAN='https://cleanwater.org/be-clean-water-voter-2026-rhode-island-endorsements'
NASW='https://naswri.socialworkers.org/Advocacy/PACE'
RIDSA='https://ridsa.org/endorsements'
PVD_STREETS='https://pvdstreets.org/vote/'
RECLAIM='https://www.reclaimri.org/canvass'
BRITT='https://brittanyforri.com/'
clean = {
('senate',12):'Valarie Lawson',('senate',3):'Samuel D Zurier',('senate',5):'Samuel W Bell',('senate',8):'Lori Urso',('senate',11):'Linda Ujifusa',('senate',13):'Dawn Euer',('senate',15):'Meghan Kallman',('senate',16):'Jonathon Acosta',('senate',17):'Nelly Burdette',('senate',18):'Robert Britto',('senate',19):'Ryan Pearson',('senate',24):'Melissa Murray',('senate',28):'Lammis Vargas',('senate',31):'Matthew LaMountain',('senate',32):'Pam Lauria',('senate',34):'Samantha Wilcox',('senate',35):'Bridget Valverde',('senate',36):'Alana DiMario',('senate',38):'Victoria Gu',
('house',1):'Edith Ajello',('house',2):'Christopher Blazejewski',('house',4):'Rebecca Kislak',('house',8):'John Lombardi',('house',9):'Enrique Sanchez',('house',11):'Grace Diaz',('house',12):'Arlette Hidalgo',('house',18):'Arthur Handy',('house',19):'Joseph McNamara',('house',22):'Zakary Pereira',('house',23):'William Muto',('house',31):'Matthew McCoy',('house',32):'Robert Craven',('house',33):'Carol McEntee',('house',34):'Teresa Tanzi',('house',35):'Kathleen Fogarty',('house',36):'Tina Spears',('house',53):'Suzy Alba',('house',57):'Brandon Voas',('house',64):'Jenni Furtado',('house',65):'Matthew Dawson',('house',66):'Jennifer Boylan',('house',67):'Nicole Jellinek',('house',68):'June Speakman',('house',69):'Susan Donovan',('house',70):'John Edwards',('house',71):'Michelle McGaw',('house',75):'Lauren Carson'}
nasw={('senate',36):'Alana DiMario',('senate',13):'Dawn Euer',('senate',15):'Meghan Kallman',('senate',17):'Nelly Burdette',('house',1):'Edith Ajello',('house',4):'Rebecca Kislak',('house',18):'Arthur Handy',('house',67):'Nicole Jellinek'}
pvd_streets={
('house',1):'Edith Ajello',('house',4):'Rebecca Kislak',('house',7):'Amy Santiago',('house',18):'Arthur Handy',('house',34):'Teresa Tanzi',('house',35):'Kathleen Fogarty',('house',59):'Jennifer Stewart',('house',61):'Leonela Felix',('house',66):'Jennifer Boylan',('house',67):'Nicole Jellinek',('house',68):'June Speakman',
('senate',8):'Gena Felix',('senate',15):'Meghan Kallman',('senate',16):'Jonathon Acosta',('senate',28):'Lammis Vargas',('senate',36):'Alana DiMario'}
reclaim={
('house',1):'Edith Ajello',('house',7):'Amy Santiago',('house',39):'Megan Cotter',('house',49):'Veronicka Vega',('house',59):'Jennifer Stewart',('house',61):'Leonela Felix',
('senate',8):'Gena Felix',('senate',15):'Meghan Kallman',('senate',17):'Nelly Burdette'}

for path in FILES:
    p=json.loads(path.read_text())
    changed=0
    for c in p.get('candidates',[]):
        chamber=str(c.get('chamber','')).lower(); dist=int(c.get('district_number') or 0); name=norm(c.get('candidate_name'))
        target=clean.get((chamber,dist))
        if target and all(x in name for x in norm(target).split()): add_end(c,'Clean Water Action',CLEAN); changed+=1
        target=nasw.get((chamber,dist))
        if target and all(x in name for x in norm(target).split()): add_end(c,'NASW-RI PACE',NASW); changed+=1
        target=pvd_streets.get((chamber,dist))
        if target and all(x in name for x in norm(target).split()): add_end(c,'Providence Streets Coalition',PVD_STREETS); changed+=1
        target=reclaim.get((chamber,dist))
        if target and all(x in name for x in norm(target).split()): add_end(c,'Reclaim RI',RECLAIM); changed+=1
        if chamber=='house' and dist==5 and 'brittany' in name and 'kubicek' in name:
            c['campaign_website']=BRITT; c['website_status']='verified_official_campaign_site'; c['website_checked']='2026-09-10'; c['website_audit_note']='Official 2026 campaign website verified.'
            c['priorities']=[
              {'title':'Housing','summary':'Calls for a statewide rent freeze and expansion of affordable, publicly owned housing.','source_label':'Official campaign website','source_url':BRITT},
              {'title':'Healthcare','summary':'Supports healthcare for Rhode Islanders that is free at the point of service.','source_label':'Official campaign website','source_url':BRITT},
              {'title':'Power in the workplace','summary':'Supports a $30 minimum wage, freedom to unionize, and the right to strike.','source_label':'Official campaign website','source_url':BRITT},
              {'title':'Energy and infrastructure','summary':'Supports public ownership of Rhode Island Energy and full funding for RIPTA and public transportation.','source_label':'Official campaign website','source_url':BRITT}]
            add_end(c,'Rhode Island Democratic Socialists of America',RIDSA); changed+=1
    p['generated_at']='2026-09-11'
    path.write_text(json.dumps(p,indent=2,ensure_ascii=False)+'\n')
    print(path.name,changed)
