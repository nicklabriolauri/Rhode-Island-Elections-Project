#!/usr/bin/env python3
"""Build the Cranston pilot from official GIS snapshots and the supplied PDF audit.

Usage: python scripts/build_cranston_map.py --source-dir /path/to/snapshots
Source snapshots: cranston-raw-{wards,precincts,roads,towns,water}.geojson,
cranston-city-1.txt (text extracted from supplied adopted citywide PDF), and
ri-general-latest.json (official state election feed).
"""
import argparse
import heapq
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/cranston'
CITY_MAPS = 'https://www.cranstonri.gov/departments/canvassing-department/voting-districts-and-district-maps/'
GIS = 'https://arcgisserver.cranstonri.org/arcgis/rest/services/Canvassing/FeatureServer/'
RESULTS = 'https://electionresults.ri.gov/results/public/RhodeIsland/elections/2026StatewideGeneralElection'
COLORS = ['#eab0b7', '#91c6db', '#ccd89f', '#b69ac8', '#f3c48d', '#f2e4a2']


def write(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'))+'\n')


def points(coords):
    if isinstance(coords[0], (float, int)):
        yield coords
    else:
        for part in coords:
            yield from points(part)


def bbox(geometry):
    ps = list(points(geometry['coordinates']))
    return [min(p[0] for p in ps), min(p[1] for p in ps), max(p[0] for p in ps), max(p[1] for p in ps)]


def round_coordinates(coords):
    if isinstance(coords[0], (float, int)):
        return [round(x, 6) for x in coords[:2]]
    return [round_coordinates(c) for c in coords]


def segment_distance(p, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    t = max(0, min(1, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy))) if dx or dy else 0
    return math.hypot(p[0]-a[0]-t*dx, p[1]-a[1]-t*dy)


def simplify_line(line, tolerance):
    if len(line) <= 2:
        return line
    index, distance = max(enumerate((segment_distance(p, line[0], line[-1]) for p in line[1:-1]), 1), key=lambda x:x[1])
    if distance <= tolerance:
        return [line[0], line[-1]]
    return simplify_line(line[:index+1], tolerance)[:-1]+simplify_line(line[index:], tolerance)


def simplify_geometry(geometry, tolerance):
    typ, coords = geometry['type'], geometry['coordinates']
    def ring(r):
        mid = len(r)//2
        result = simplify_line(r[:mid+1], tolerance)[:-1]+simplify_line(r[mid:], tolerance)
        return result if len(result) >= 4 else r
    if typ == 'Polygon':
        coords = [ring(r) for r in coords]
    elif typ == 'MultiPolygon':
        coords = [[ring(r) for r in polygon] for polygon in coords]
    elif typ == 'LineString':
        coords = simplify_line(coords, tolerance)
    elif typ == 'MultiLineString':
        coords = [simplify_line(line, tolerance) for line in coords]
    return {'type':typ, 'coordinates':round_coordinates(coords)}


def contains(geometry, point):
    def inside(r):
        x,y = point; hit = False
        for a,b in zip(r, r[1:]+r[:1]):
            if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
                hit = not hit
        return hit
    polygons = [geometry['coordinates']] if geometry['type']=='Polygon' else geometry['coordinates']
    return any(inside(p[0]) and not any(inside(r) for r in p[1:]) for p in polygons)


def label_point(geometry):
    """Find an interior label point with a small, deterministic distance-grid search."""
    box = bbox(geometry)
    rings = [geometry['coordinates']] if geometry['type']=='Polygon' else geometry['coordinates']
    edges = [(a,b) for p in rings for ring in p for a,b in zip(ring,ring[1:])]
    best, score = None, -1
    for i in range(1,25):
        for j in range(1,25):
            p = [box[0]+(box[2]-box[0])*i/25, box[1]+(box[3]-box[1])*j/25]
            if contains(geometry,p):
                distance = min(segment_distance(p,a,b) for a,b in edges)
                if distance > score:
                    best, score = p, distance
    if best is None:
        raise ValueError('No interior label point')
    return [round(v,6) for v in best]


def build(source):
    OUT.mkdir(parents=True, exist_ok=True)
    raw = {k:json.loads((source/f'cranston-raw-{k}.geojson').read_text()) for k in ['wards','precincts','roads','towns','water']}
    pdf_text = (source/'cranston-city-1.txt').read_text()
    pairs = re.findall(r'(\d)-(\d)\s*\((07\d{2})\)\s*Senate:\s*(\d+)\s*Rep:\s*(\d+)', pdf_text)
    if len(pairs)!=27 or len({p[2] for p in pairs})!=27:
        raise ValueError('Expected 27 distinct PDF precinct labels')
    audit = {p[2]:{'ward':int(p[0]),'local_label':f'{p[0]}-{p[1]}','senate':int(p[3]),'house':int(p[4])} for p in pairs}
    turnouts = {f['properties']['DISTRICT']:f['properties'] for f in json.loads((ROOT/'data/ri_turnout_2024_precinct.geojson').read_text())['features'] if f['properties'].get('TOWN')=='Cranston'}
    current, precincts = {}, []
    for f in raw['precincts']['features']:
        p = f['properties']; code = str(p['Precinct_CVRS']); ward = int(p['Ward'])
        fields = {'ward':ward,'local_label':p['WardDistrict'],'house':int(p['StateRepDistr']),'senate':int(p['StateSenateDistr'])}
        if audit.get(code)!=fields:
            raise ValueError(f'PDF/GIS assignment mismatch: {code}')
        t = turnouts[code]
        if (t['Ward'],t['StHouse'],t['StSenate'])!=(ward,fields['house'],fields['senate']):
            raise ValueError(f'2024 precinct assignment mismatch: {code}')
        properties = {'precinct':code, **fields, 'congress':int(p['CongrDistr']), 'polling_place':p['PollingPlace'], 'polling_address':p['PollingPlaceAddress'], 'voted_2024':t['VOTED'],'eligible_2024':t['ELIGIBLE'], 'label':label_point(f['geometry'])}
        # Retain full source geometry for address matching; only round to ~0.1m.
        precincts.append({'type':'Feature','properties':properties,'geometry':{'type':f['geometry']['type'],'coordinates':round_coordinates(f['geometry']['coordinates'])}})
        officeholders = {'council':{'name':p['CouncilWardName'],'party':p['CouncilWardParty'].strip('() '),'email':p['CouncilWardEmail']},'school':{'name':p['SchoolCmteeWardName'],'email':p['SchoolCmteeWardEmail']}}
        if ward in current and current[ward]!=officeholders:
            raise ValueError(f'Conflicting officeholders in Ward {ward}')
        current[ward] = officeholders
    if len(precincts)!=27 or set(current)!=set(range(1,7)):
        raise ValueError('Incomplete Cranston geography')
    precincts.sort(key=lambda f:f['properties']['precinct'])
    wards = []
    for f in raw['wards']['features']:
        p=f['properties']; ward=int(p['Ward']); subs=[x for x in precincts if x['properties']['ward']==ward]
        if p['PlanID']!='Plan_A3':raise ValueError('Unexpected ward plan')
        props={'ward':ward,'color':COLORS[ward-1],'label':label_point(f['geometry']),'precinct_count':len(subs),'precincts':[x['properties']['precinct'] for x in subs], 'house':sorted({x['properties']['house'] for x in subs}),'senate':sorted({x['properties']['senate'] for x in subs})}
        wards.append({'type':'Feature','properties':props,'geometry':{'type':f['geometry']['type'],'coordinates':round_coordinates(f['geometry']['coordinates'])}})
    wards.sort(key=lambda f:f['properties']['ward'])
    if [w['properties']['ward'] for w in wards]!=list(range(1,7)):
        raise ValueError('Missing or duplicate ward')
    for p in precincts:
        ward=next(w for w in wards if w['properties']['ward']==p['properties']['ward'])
        if not contains(ward['geometry'],p['properties']['label']):raise ValueError('Precinct label outside its ward')
    write('wards.geojson',{'type':'FeatureCollection','features':wards})
    write('precincts.geojson',{'type':'FeatureCollection','features':precincts})
    towns = [{'type':'Feature','properties':{'name':f['properties']['NAME'].title(),'label':label_point(f['geometry'])},'geometry':simplify_geometry(f['geometry'],.00008)} for f in raw['towns']['features']]
    # Context is deliberately faint. Source municipalities predate the election plan.
    write('context.geojson',{'type':'FeatureCollection','features':towns})
    roads=[]
    for f in raw['roads']['features']:
        name=(f['properties'].get('NAME') or '').strip()
        if not name or name in ('DRIVEWAY','PARKING LOT'):continue
        roads.append({'type':'Feature','properties':{'name':name.title(),'in_city':f['properties']['IN_CITY']=='Y'},'geometry':simplify_geometry(f['geometry'],.000015)})
    write('roads.geojson',{'type':'FeatureCollection','features':roads})
    waters=[]
    for f in raw['water']['features']:
        b=bbox(f['geometry'])
        if b[2]<-71.66 or b[0]>-71.35 or b[3]<41.68 or b[1]>41.83:continue
        if (b[2]-b[0])*(b[3]-b[1])<.0000002:continue
        waters.append({'type':'Feature','properties':{},'geometry':simplify_geometry(f['geometry'],.000025)})
    write('water.geojson',{'type':'FeatureCollection','features':waters})
    source_results=json.loads((source/'ri-general-latest.json').read_text());election=source_results['election'];races=[]
    for item in source_results['ballotItems']:
        name=item['name'][0]['text']
        if not name.startswith('Cranston:') or item['contestType']!='Candidate':continue
        office='school' if 'School Committee' in name else 'council'
        match=re.search(r'Ward (\d+)',name); ward=int(match[1]) if match else None
        seats=int(re.search(r'\d+', item['voteFor'][0]['text'])[0]);total=item['voteTotal'];candidates=[]
        for option in item['summaryResults']['ballotOptions']:
            cname=re.sub(r'\s*\([^()]+\)$','',option['name'][0]['text']);votes=option['voteCount']
            candidates.append({'name':cname,'party':((option.get('party') or {}).get('abbreviation') or '').upper(),'votes':votes,'share':round(votes/total*100,6) if total else None,'is_write_in':bool(option.get('isWriteIn')),'source_is_winner':option.get('isWinner')})
        candidates.sort(key=lambda c:-c['votes'])
        if sum(c['votes'] for c in candidates)!=total:raise ValueError('Vote arithmetic mismatch')
        races.append({'office':office,'ward':ward,'name':name.split(': ',1)[1],'seats':seats,'total_votes':total,'candidates':candidates,'source_url':RESULTS+'/ballot-items/'+item['id']})
    if len(races)!=14 or {(r['office'],r['ward']) for r in races}!={(o,w) for o in ['council','school'] for w in [None,1,2,3,4,5,6]}:raise ValueError('Expected all 14 local contests')
    first=raw['precincts']['features'][0]['properties']
    config={'municipality':'Cranston','slug':'cranston','reviewed_on':'2026-11-19','boundary_plan':'Ward Plan A3 / Precinct Plan A3a','ward_adopted_on':'2022-03-30','precinct_adopted_on':'2022-04-12','pdf_validation':{'precincts_checked':27,'mismatches':0,'source_documents':['2022 Adopted Precincts 36x60.pdf','2022 Adopted Precincts Map Series 36x60.pdf'],'assignments':audit},'current_officeholders':current,'current_council_term_ends':'2027-01-04','citywide_officeholders':{'mayor':{'name':first['MayorName'],'party':first['MayorParty'].strip('() ')},'council':[first['Citywide1Name'],first['Citywide2Name'],first['Citywide3Name']],'school':[first['SchoolCmteeCitywideName']]},'results':{'election_date':'2026-11-03','is_official':election.get('isOfficialResults') is True,'as_of':election['asOf'],'races':races},'sources':{'maps':CITY_MAPS,'wards':GIS+'4','precincts':GIS+'3','roads':'https://services5.arcgis.com/bmiwyveTUuaT56jB/arcgis/rest/services/Roads/FeatureServer/18','context':'https://services2.arcgis.com/S8zZg9pg23JUEexQ/ArcGIS/rest/services/Municipalities_1989/FeatureServer/0','council':'https://www.cranstonri.gov/about/city-council/','school':'https://www.cranstonri.gov/government/school-committee-directory/','election':RESULTS,'state_lookup':'https://vote.sos.ri.gov/Home/PollingPlaces'}}
    write('overview.json',config)
    print(f'Built 6 wards, 27 PDF-checked precincts, {len(roads)} road segments, {len(waters)} water features, and 14 local contests.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-dir',type=Path,required=True)
    build(parser.parse_args().source_dir)
