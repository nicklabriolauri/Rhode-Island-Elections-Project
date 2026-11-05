"""Check vote arithmetic, full coverage, and conservative result status."""
import copy
import json
import unittest
from collections import Counter
from pathlib import Path
from import_general_results_2026 import normalize

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    items = []
    for office, count in [('Representative', 75), ('Senator', 38)]:
        for district in range(1, count + 1):
            items.append({
                'id': f'{office}-{district}',
                'name': [{'languageId': 'en', 'text': f'{office} in General Assembly District {district}'}],
                'voteTotal': 100,
                'summaryResults': {'ballotOptions': [
                    {'id':'a', 'name':[{'languageId':'en','text':'Candidate A (DEM)'}], 'voteCount':60, 'party':{'abbreviation':'DEM'}, 'isWriteIn':False, 'isWinner':None},
                    {'id':'b', 'name':[{'languageId':'en','text':'Candidate B (REP)'}], 'voteCount':40, 'party':{'abbreviation':'REP'}, 'isWriteIn':False, 'isWinner':None},
                ]},
                'reportingStatus': {'reportingUnits':1, 'totalUnits':1},
            })
    return {'election': {'electionDate':'2026-11-03', 'isPrimary':False, 'isOfficialResults':False, 'asOf':'2026-11-05T01:02:59Z'}, 'ballotItems':items}


class ImportTests(unittest.TestCase):
    def test_complete_reporting_does_not_call_race(self):
        result = normalize(fixture())
        self.assertEqual(len(result['races']), 113)
        self.assertTrue(all(r['status'] == 'leading' for r in result['races']))

    def test_rejects_incomplete_and_duplicate_districts(self):
        raw = fixture()
        raw['ballotItems'].pop()
        with self.assertRaises(ValueError): normalize(raw)
        raw = fixture()
        raw['ballotItems'][-1] = copy.deepcopy(raw['ballotItems'][0])
        with self.assertRaises(ValueError): normalize(raw)

    def test_rejects_bad_vote_sum(self):
        raw = fixture()
        raw['ballotItems'][0]['voteTotal'] = 101
        with self.assertRaises(ValueError): normalize(raw)

    def test_tie_and_no_votes_have_no_leader(self):
        for total, a, b, expected in [(100,50,50,'tied'), (0,0,0,'no-votes')]:
            raw = fixture()
            raw['ballotItems'][0]['voteTotal'] = total
            options = raw['ballotItems'][0]['summaryResults']['ballotOptions']
            options[0]['voteCount'], options[1]['voteCount'] = a, b
            race = normalize(raw)['races'][0]
            self.assertEqual(race['status'], expected)
            self.assertIsNone(race['leader_name'])

    def test_explicit_source_winner_flag(self):
        raw = fixture()
        raw['ballotItems'][0]['summaryResults']['ballotOptions'][0]['isWinner'] = True
        self.assertEqual(normalize(raw)['races'][0]['status'], 'winner')

    def test_published_snapshot(self):
        result = json.loads((ROOT/'data/general_results_2026.json').read_text())
        keys = {(r['chamber'], r['district']) for r in result['races']}
        self.assertEqual(keys, {(c,d) for c,n in [('house',75),('senate',38)] for d in range(1,n+1)})
        for r in result['races']:
            self.assertEqual(sum(c['votes'] for c in r['candidates']), r['total_votes'])
            if r['total_votes']:
                for c in r['candidates']:
                    self.assertAlmostEqual(c['pct'], 100*c['votes']/r['total_votes'], places=5)
            if r['status'] == 'leading':
                self.assertEqual(r['leader_name'], max(r['candidates'], key=lambda c:c['votes'])['name'])
        for chamber in ['house','senate']:
            self.assertEqual(result['seat_leads'][chamber], dict(Counter(r['leader_party'] or 'UNASSIGNED' for r in result['races'] if r['chamber'] == chamber)))

    def test_all_general_candidates_in_three_way_race(self):
        result = json.loads((ROOT/'data/general_results_2026.json').read_text())
        r = next(r for r in result['races'] if r['chamber'] == 'house' and r['district'] == 15)
        self.assertEqual(len([c for c in r['candidates'] if not c['is_write_in']]), 3)
        self.assertEqual(r['leader_party'], 'IND')
        self.assertEqual(r['margin_votes'], r['candidates'][0]['votes'] - r['candidates'][1]['votes'])


if __name__ == '__main__':
    unittest.main()
