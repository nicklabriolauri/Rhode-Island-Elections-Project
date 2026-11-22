"""Build a frozen experimental activity-index snapshot. Standard library only.

Run explicitly after reviewing the input snapshot; not tied to automatic imports.
"""
from pathlib import Path
from html import escape
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'data/cranston/sponsorship-2026.json'
OUT=ROOT/'data/cranston/activity-index-pilot-2026.json'

def build():
    raw=INPUT.read_bytes();source=json.loads(raw)
    special={'ordinance-12-26-02S':'fiscal','ordinance-12-25-06S':'fiscal','ordinance-12-25-03':'approval'}
    data={'version':'0.1-test','year':2026,'reviewed':'2026-11-22','source_sha256':hashlib.sha256(raw).hexdigest(),'source_url':'/data/cranston/sponsorship-2026.json','meeting_count':source['meeting_count'],'motion_count':source['motion_count'],'coverage':'Partial extracted records; attribution gaps vary by member. This is a frozen test snapshot, not a validated performance score.','members':source['members'],'proposals':[]}
    for p in source['proposals']:
        if p['category']=='ordinance':function=special.get(p['id'],'local_rule')
        elif p['category'] in ['recognition','symbolic']:function=p['category']
        elif p['category']=='position':function='advocacy'
        else:raise ValueError('Unreviewed category '+p['category'])
        x={**p,'function':function,'classification_note':'Provisional function classification from the identified title and recorded actions; not a legal ruling or a finding of final adoption.'}
        if function=='fiscal':x['classification_note']+=' School-building revolving fund or municipal rescue-service budget measure.'
        if function=='approval':x['classification_note']+=' City-owned property sale approval, separated from general policy initiation.'
        if p['id']=='ordinance-09-22-02':x['classification_note']+=' School-related background-check proposal is treated as a proposed local rule; no claim about legal validity or enactment.'
        data['proposals'].append(x)
    OUT.write_text(json.dumps(data,indent=2)+'\n')
    template=(ROOT/'templates/cranston-activity-index-test.html').read_text()
    # JSON is data, never executable markup. Escape less-than to prevent script termination.
    page=template.replace('<!-- PILOT_DATA -->',json.dumps(data).replace('<','\\u003c'))
    (ROOT/'cranston-activity-index-test.html').write_text(page)
    print(f'Built {data["version"]}: {len(data["members"])} members, {len(data["proposals"])} identified measures')

if __name__=='__main__':build()
