"""Check adopted-PDF assignments, source geometry, election arithmetic and source dates."""
import json
import unittest
from pathlib import Path
from build_cranston_map import contains

ROOT=Path(__file__).resolve().parents[1]
def read(name):return json.loads((ROOT/'data/cranston'/name).read_text())

class CranstonMapTests(unittest.TestCase):
    def test_full_adopted_geography(self):
        wards=read('wards.geojson')['features'];precincts=read('precincts.geojson')['features'];audit=read('overview.json')['pdf_validation']['assignments']
        self.assertEqual({f['properties']['ward'] for f in wards},set(range(1,7)))
        self.assertEqual(len(precincts),27)
        self.assertEqual({f['properties']['precinct'] for f in precincts},set(audit))
        self.assertEqual([f['properties']['precinct_count'] for f in wards],[3,5,4,4,6,5])
        for f in precincts:
            p=f['properties'];self.assertEqual({k:p[k] for k in ['ward','local_label','house','senate']},audit[p['precinct']])
            self.assertTrue(contains(f['geometry'],p['label']))
            self.assertTrue(contains(next(w for w in wards if w['properties']['ward']==p['ward'])['geometry'],p['label']))
    def test_local_races_and_citywide_arithmetic(self):
        d=read('overview.json');rs=d['results']['races']
        self.assertEqual(len(rs),14)
        self.assertEqual({(r['office'],r['ward']) for r in rs},{(o,w) for o in ['school','council'] for w in [None,1,2,3,4,5,6]})
        for r in rs:
            self.assertEqual(sum(c['votes'] for c in r['candidates']),r['total_votes'])
            self.assertAlmostEqual(sum(c['share'] for c in r['candidates']),100,places=4)
        city=next(r for r in rs if r['office']=='council' and r['ward'] is None)
        self.assertEqual(city['seats'],3)
        self.assertEqual(city['total_votes'],67212)
        self.assertEqual(next(r for r in rs if r['office']=='council' and r['ward']==2)['candidates'][0]['name'],'Sara Jane Haupt')
        self.assertNotEqual(d['current_officeholders']['2']['council']['name'],'Sara Jane Haupt')
    def test_no_private_contact_fields(self):
        text=(ROOT/'data/cranston/overview.json').read_text()
        for private in ['HomePhone','CellPhone','StreetAddress','MayorZIP']:
            self.assertNotIn(private,text)
    def test_dates_and_officeholders_are_separate(self):
        d=read('overview.json');self.assertEqual(d['ward_adopted_on'],'2022-03-30');self.assertEqual(d['precinct_adopted_on'],'2022-04-12')
        self.assertEqual(d['results']['election_date'],'2026-11-03');self.assertEqual(d['current_council_term_ends'],'2027-01-04')
        self.assertEqual(len(d['citywide_officeholders']['council']),3)
        self.assertEqual(len(d['citywide_officeholders']['school']),1)
    def test_context_and_streets_available_locally(self):
        self.assertGreater(len(read('roads.geojson')['features']),5000)
        towns={f['properties']['name'] for f in read('context.geojson')['features']}
        self.assertTrue({'Cranston','Providence','Warwick','Johnston','Scituate'}.issubset(towns))

if __name__=='__main__':unittest.main()
