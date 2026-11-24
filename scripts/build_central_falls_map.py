#!/usr/bin/env python3
"""Build Central Falls map data from RIGIS GeoJSON, state ballots and the 2026 results feed.

Run with --source-dir containing gis.json, results.json and ballot-0401.pdf
through ballot-0407.pdf. Requires ogr2ogr and pdftotext.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

from build_cranston_map import bbox, label_point

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/central-falls'
GIS = 'https://services2.arcgis.com/S8zZg9pg23JUEexQ/ArcGIS/rest/services/BND_Voting_Precincts_2022/FeatureServer/0'
BALLOTS = 'https://risos-legacy-files-public.s3.amazonaws.com/documents/elections/ballots/2026/11/03/'
RESULTS = 'https://electionresults.ri.gov/results/public/RhodeIsland/elections/2026StatewideGeneralElection'
ROSTER = 'https://central-falls-ri.publick.org/officials/'
COLORS = ['#eab0b7', '#91c6db', '#ccd89f', '#b69ac8', '#f3c48d']


def save(name, payload):
    (OUTPUT / name).write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n')


def build(source):
    raw = json.loads((source / 'gis.json').read_text())
    turnouts = json.loads((ROOT / 'data/ri_turnout_2024_precinct.geojson').read_text())
    turnout = {f['properties']['DISTRICT']: f['properties'] for f in turnouts['features']}
    precincts = []
    for feature in raw['features']:
        p, geometry = feature['properties'], feature['geometry']
        code = p['DISTRICT']
        ballot = subprocess.check_output(['pdftotext', '-f', '1', '-l', '1', '-layout',
                                          source / ('ballot-' + code + '.pdf'), '-'], text=True)
        expected = (p['Ward'], p['StHouse'], p['StSenate'], p['Congress'])
        actual = tuple(int(re.search(label + r' (\d+)', ballot)[1]) for label in
                       ['Central Falls Ward', 'Representative District', 'Senate District', 'Congressional District'])
        assert p['TOWN'] == 'Central Falls' and actual == expected, (code, expected, actual)
        precincts.append({'type': 'Feature', 'geometry': geometry, 'properties': {
            'precinct': code, 'local_label': code, 'ward': p['Ward'], 'house': p['StHouse'],
            'senate': p['StSenate'], 'congress': p['Congress'], 'label': label_point(geometry),
            'voted_2024': turnout[code]['VOTED'], 'eligible_2024': turnout[code]['ELIGIBLE'],
            'ballot_url': BALLOTS + code + '.pdf'
        }})
    assert {p['properties']['precinct'] for p in precincts} == {f'040{i}' for i in range(1, 8)}
    # Dissolve only the precincts belonging to the same ward.
    dissolved = json.loads(subprocess.check_output([
        'ogr2ogr', '-f', 'GeoJSON', '/vsistdout/', source / 'gis.json', '-dialect', 'SQLite',
        '-sql', 'SELECT Ward, ST_Union(geometry) AS geometry FROM gis GROUP BY Ward ORDER BY Ward'
    ]))
    assert {f['properties']['Ward'] for f in dissolved['features']} == set(range(1, 6))
    for f in dissolved['features']:
        ward = f['properties']['Ward']
        ps = [p['properties'] for p in precincts if p['properties']['ward'] == ward]
        f['properties'] = {'ward': ward, 'color': COLORS[ward - 1], 'precinct_count': len(ps),
                           'label': label_point(f['geometry']), 'house': sorted({p['house'] for p in ps}),
                           'senate': sorted({p['senate'] for p in ps})}
    results = json.loads((source / 'results.json').read_text())
    races = []
    for item in results['ballotItems']:
        name = item['name'][0]['text']
        if not name.startswith('Central Falls: Non-Partisan City Council') or item['contestType'] != 'Candidate':
            continue
        match = re.search(r'Ward (\d+)', name)
        seats = int(re.search(r'\d+', item['voteFor'][0]['text'])[0])
        total = item['voteTotal']
        candidates = []
        for c in item['summaryResults']['ballotOptions']:
            votes = c['voteCount']
            candidates.append({'name': c['name'][0]['text'], 'party': 'NON', 'votes': votes,
                               'share': votes / total * 100 if total else None,
                               'is_write_in': bool(c.get('isWriteIn')), 'source_is_winner': c.get('isWinner')})
        assert sum(c['votes'] for c in candidates) == total
        races.append({'office': 'council', 'ward': int(match[1]) if match else None,
                      'seats': seats, 'total_votes': total,
                      'candidates': sorted(candidates, key=lambda c: -c['votes']),
                      'source_url': RESULTS + '/ballot-items/' + item['id']})
    assert sorted((r['ward'] or 0, r['seats']) for r in races) == [(0, 2), *[(n, 1) for n in range(1, 6)]]
    boxes = [bbox(f['geometry']) for f in precincts]
    extent = [min(b[0] for b in boxes)-.01, min(b[1] for b in boxes)-.01,
              max(b[2] for b in boxes)+.01, max(b[3] for b in boxes)+.01]
    members = ['Alberto Rivas-Lugo', 'Robert A. Ferri', 'Kevin K. Kazarian', 'Anthony Solano', 'Rafael Peguero']
    OUTPUT.mkdir(parents=True, exist_ok=True)
    save('wards.geojson', dissolved)
    save('precincts.geojson', {'type': 'FeatureCollection', 'features': precincts})
    save('overview.json', {
        'municipality': 'Central Falls', 'slug': 'central-falls', 'search_extent': extent,
        'current_officeholders': {n: {'council': {'name': name}} for n, name in enumerate(members, 1)},
        'citywide_officeholders': {'council': ['Tatiana Baena', 'Laurilim Rosado-Martinez']},
        'results': {'is_official': results['election'].get('isOfficialResults') is True,
                    'as_of': results['election']['asOf'], 'races': races},
        'sources': {'maps': GIS, 'council': ROSTER, 'election': RESULTS,
                    'state_lookup': 'https://vote.sos.ri.gov/Home/PollingPlaces'}
    })


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    build(parser.parse_args().source_dir)
