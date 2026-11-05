#!/usr/bin/env python3
"""Import a dated official statewide General Assembly results snapshot.

Usage: python scripts/import_general_results_2026.py [--input saved-state-feed.json]
No winner is inferred from a lead or from reporting-unit completeness.
"""
import argparse
import json
import re
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE_URL = 'https://electionresults.ri.gov/results/public/RhodeIsland/elections/2026StatewideGeneralElection'
FEED_URL = 'https://electionresults.ri.gov/results/public/api/elections/RhodeIsland/2026StatewideGeneralElection/data'


def text(value):
    if not value:
        return ''
    return next((x['text'] for x in value if x.get('languageId') == 'en'), value[0]['text'])


def normalize(payload):
    election = payload['election']
    if election['electionDate'][:10] != '2026-11-03' or election.get('isPrimary'):
        raise ValueError('Not the November 3, 2026 general election')
    historical = json.loads((ROOT / 'data/race_data.json').read_text())
    races = []
    for item in payload['ballotItems']:
        name = text(item['name'])
        match = re.fullmatch(r'(Senator|Representative) in General Assembly District (\d+)', name, re.I)
        if not match:
            continue
        chamber = 'senate' if match[1].lower() == 'senator' else 'house'
        district = int(match[2])
        total = item['voteTotal']
        if not isinstance(total, int) or total < 0:
            raise ValueError(f'Invalid vote total: {name}')
        candidates = []
        for option in item['summaryResults']['ballotOptions']:
            votes = option['voteCount']
            if not isinstance(votes, int) or votes < 0:
                raise ValueError(f'Invalid candidate votes: {name}')
            party = (option.get('party') or {}).get('abbreviation') or 'OTHER'
            party = party.upper()
            candidates.append({
                'source_id': option['id'],
                'name': re.sub(r'\s*\([^()]+\)$', '', text(option['name'])),
                'party': party, 'votes': votes,
                'pct': round(votes / total * 100, 6) if total else None,
                'is_write_in': bool(option.get('isWriteIn')),
                'source_is_winner': option.get('isWinner'),
            })
        if sum(c['votes'] for c in candidates) != total:
            raise ValueError(f'Candidate vote sum differs from contest total: {name}')
        candidates.sort(key=lambda c: (-c['votes'], c['is_write_in'], c['name']))
        tied = len(candidates) > 1 and candidates[0]['votes'] == candidates[1]['votes']
        leader = candidates[0] if total and not tied else None
        certified = election.get('isOfficialResults') is True
        named = [c for c in candidates if not c['is_write_in']]
        unopposed = len(named) == 1
        old_party = historical.get(f'{chamber}|2024|{district}', {}).get('winner_party', '').upper()
        races.append({
            'chamber': chamber, 'district': district, 'contest': name,
            'source_id': item['id'],
            'source_url': f"{PAGE_URL}/ballot-items/{item['id']}",
            'total_votes': total, 'candidates': candidates,
            'leader_name': leader['name'] if leader else None,
            'leader_party': leader['party'] if leader else None,
            'status': 'no-votes' if not total else 'tied' if tied else 'winner' if certified or leader['source_is_winner'] is True else 'leading',
            'is_unopposed': unopposed,
            'margin_votes': (candidates[0]['votes'] - candidates[1]['votes']) if len(candidates) > 1 and total else None,
            'margin_pct': round((candidates[0]['votes'] - candidates[1]['votes']) / total * 100, 6) if len(candidates) > 1 and total else None,
            'previous_party': old_party or None,
            'party_change': bool(leader and old_party and old_party != leader['party']),
            'reporting': item.get('reportingStatus'),
        })
    keys = [(r['chamber'], r['district']) for r in races]
    expected = {(c, d) for c, n in [('house', 75), ('senate', 38)] for d in range(1, n + 1)}
    if len(keys) != 113 or len(set(keys)) != 113 or set(keys) != expected:
        raise ValueError('Expected exactly 75 House and 38 Senate districts; refusing incomplete/duplicate import')
    races.sort(key=lambda r: (r['chamber'], r['district']))
    return {
        'election_date': '2026-11-03', 'is_official': election.get('isOfficialResults') is True,
        'source': 'Rhode Island Board of Elections', 'source_url': PAGE_URL,
        'source_feed_url': FEED_URL, 'source_as_of': election['asOf'],
        'source_published_at': election.get('publishDate'),
        'source_publish_version': election.get('publishVersionId'),
        'imported_at': datetime.now(timezone.utc).isoformat(),
        'notes': [
            'Percentages include write-in votes; they are not two-party shares.',
            'Leading does not mean called or certified. Winner status requires an official source flag or certified results.',
            'Reporting units are the source\'s reporting jurisdictions, not an estimate of ballots counted.',
            'Unopposed means one named ballot candidate; write-ins are still included.',
            'This is a dated snapshot, not a live feed. Party changes compare current leaders with the party that won in 2024.',
        ],
        'seat_leads': {c: dict(Counter(r['leader_party'] or 'UNASSIGNED' for r in races if r['chamber'] == c)) for c in ['house', 'senate']},
        'races': races,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path)
    args = parser.parse_args()
    if args.input:
        raw = json.loads(args.input.read_text())
    else:
        with urllib.request.urlopen(FEED_URL, timeout=60) as response:
            raw = json.load(response)
    result = normalize(raw)
    path = ROOT / 'data/general_results_2026.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f"Imported {len(result['races'])} districts: {result['seat_leads']}; as of {result['source_as_of']}")
