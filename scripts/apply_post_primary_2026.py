#!/usr/bin/env python3
import json, re
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'whos_running_2026.json'
RESULTS = ROOT / 'data' / 'primary_results_2026.json'
STATUS = ROOT / 'data' / 'post_primary_status_2026.json'
PAGES = [ROOT/'running.html', ROOT/'ballot.html', ROOT/'index.html']
SCRIPT_TAG = '<script src="post-primary-2026.js?v=20260910"></script>'

def norm(s):
    return re.sub(r'[^a-z0-9]+',' ',str(s or '').lower()).strip()

payload = json.loads(DATA.read_text())
results = json.loads(RESULTS.read_text())

race_results = {}
for race in results.get('races', []):
    key = (str(race.get('chamber','')).lower(), str(race.get('district')), str(race.get('party_code','')).upper())
    rows = race.get('candidates') or []
    if rows:
        top = max((int(c.get('votes') or 0) for c in rows), default=0)
        race_results[key] = {norm(c.get('name')): (int(c.get('votes') or 0), float(c.get('pct') or 0), int(c.get('votes') or 0)==top and top>0) for c in rows}

statuses = []
for chamber, districts in payload.get('chambers', {}).items():
    for district, rec in districts.items():
        primary = deepcopy(rec.get('candidates') or [])
        existing_general = deepcopy(rec.get('general_candidates') or [])
        rec['primary_candidates'] = deepcopy(primary)
        active, lost = [], []
        for c in primary:
            party = str(c.get('party','')).upper()
            rr = race_results.get((chamber, str(district), party))
            result = rr.get(norm(c.get('name'))) if rr else None
            won = result[2] if result else True  # no contested result means no primary opponent in this dataset
            c['primary_result'] = 'won' if won else 'lost'
            c['election_status'] = 'general_candidate' if won else 'lost_primary'
            c['on_primary_ballot'] = True
            c['on_election_ballot'] = bool(won)
            c['ballot_stage'] = 'general' if won else 'primary_complete'
            if result:
                c['primary_votes'], c['primary_pct'] = result[0], result[1]
            (active if won else lost).append(c)
        for c in existing_general:
            c['primary_result'] = 'not_applicable'
            c['election_status'] = 'general_candidate'
            c['on_election_ballot'] = True
            c['ballot_stage'] = 'general'
            active.append(c)
        # Running/search should retain primary losers; ballot JS removes them.
        rec['candidates'] = active + lost
        rec['general_candidates'] = []
        rec['historical_candidates'] = deepcopy(lost)
        rec['candidate_total'] = len(rec['candidates'])
        rec['general_candidate_total'] = len(active)
        rec['general_status'] = 'unopposed' if len(active)==1 else ('contested' if len(active)>1 else 'no_candidate')
        rec['general_label'] = 'Unopposed in general election' if len(active)==1 else (f'{len(active)} general-election candidates' if active else 'No general-election candidate currently listed')
        rec['primary_status'] = 'complete'
        rec['primary_label'] = 'Primary complete'
        for c in rec['candidates']:
            c['unopposed_general'] = len(active)==1 and c.get('election_status')=='general_candidate'
            party_label = c.get('party_label') or c.get('party_raw') or c.get('party') or ''
            if c.get('election_status')=='lost_primary':
                label = f'Lost {party_label} Primary'.replace('Democratic Primary','Democratic Primary').replace('Republican Primary','Republican Primary')
            elif c.get('unopposed_general'):
                label = 'Unopposed in General Election'
            elif str(c.get('party','')).upper() not in ('DEM','REP'):
                label = 'Independent / General Election'
            elif c.get('primary_result')=='won':
                label = f'Won {party_label} Primary'
            else:
                label = 'General Election Candidate'
            c['status_label'] = label
            statuses.append({
                'candidate_id': c.get('candidate_id'), 'name': c.get('name'), 'chamber': chamber,
                'district': int(district), 'party': c.get('party'), 'party_label': party_label,
                'election_status': c.get('election_status'), 'primary_result': c.get('primary_result'),
                'unopposed_general': c.get('unopposed_general',False), 'status_label': label
            })

payload['generated_at'] = datetime.now(timezone.utc).isoformat()
payload['election_stage'] = 'post_primary_general_election'
payload['post_primary_note'] = 'September 9, 2026 primary results applied. Primary losers retained for historical/search display; general-election-only candidates included in candidate lists.'
DATA.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n')
STATUS.write_text(json.dumps({'generated_at': datetime.now(timezone.utc).isoformat(), 'candidates': statuses}, indent=2, ensure_ascii=False) + '\n')

for page in PAGES:
    if not page.exists(): continue
    text = page.read_text()
    if 'post-primary-2026.js' not in text:
        text = text.replace('</body>', f'  {SCRIPT_TAG}\n</body>')
        page.write_text(text)

print(f'Updated {len(statuses)} candidate statuses and patched {sum(p.exists() for p in PAGES)} pages.')
