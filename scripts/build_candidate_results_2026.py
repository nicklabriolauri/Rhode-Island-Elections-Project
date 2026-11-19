#!/usr/bin/env python3
"""Link profiles to official general-election candidates within the same district.
Run after importing results. Missing ballot matches are never assigned a result.
"""
import json
import re
import unicodedata
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def words(name):
    value = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()
    return [w for w in re.findall(r'[a-z0-9]+', value) if w not in ('jr', 'sr', 'ii', 'iii', 'iv')]

def match(candidate, race):
    name = words(candidate['name'])
    options = [c for c in race['candidates'] if not c['is_write_in']]
    exact = [c for c in options if words(c['name']) == name]
    if len(exact) == 1:
        return exact[0]
    # Middle names and initials differ between the roster and official ballot.
    matches = [c for c in options if words(c['name'])[0] == name[0] and words(c['name'])[-1] == name[-1] and c['party'] == candidate['party']]
    return matches[0] if len(matches) == 1 else None

def build():
    data = json.loads((ROOT/'data/general_results_2026.json').read_text())
    races = {(r['chamber'], r['district']): r for r in data['races']}
    roster = json.loads((ROOT/'data/mobile_guide_2026.json').read_text())['candidates']
    records = []
    for c in roster:
        race = races[(c['chamber'], int(c['district']))]
        official = match(c, race)
        records.append({k:c[k] for k in ('id','slug','name','party','chamber','district','profile')} | {'source_id': official['source_id'] if official else None})
    output = {'election_date':data['election_date'], 'candidates':records}
    (ROOT/'data/candidate_results_2026.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(f"Linked {sum(c['source_id'] is not None for c in records)}/{len(records)} roster candidates to general-election ballots")
    print('Not on ballot:', ', '.join(c['name'] for c in records if not c['source_id']))
if __name__ == '__main__':
    build()
