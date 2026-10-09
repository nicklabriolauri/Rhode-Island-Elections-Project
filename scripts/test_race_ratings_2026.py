"""Check rating boundaries, current roster eligibility and source vote arithmetic."""
import unittest
from build_race_ratings_2026 import build,build_baseline,category,render,ROOT
from lxml import html
class RatingsTests(unittest.TestCase):
 def test_boundaries(self):
  for margin,expected in [(0,'Toss Up'),(1.999,'Toss Up'),(2,'Tilt'),(4.999,'Tilt'),(5,'Lean'),(9.999,'Lean'),(10,'Likely'),(14.999,'Likely'),(15,'Solid'),(20,'Solid')]:self.assertEqual(category(margin),expected)
 def test_all_districts(self):
  d=build();self.assertEqual(len(d['races']),113);self.assertEqual(len({(r['chamber'],r['district']) for r in d['races']}),113)
 def test_rated_eligibility(self):
  for r in build_baseline()['races']:
   if r['status']=='Rated':
    self.assertGreaterEqual(len(r['candidates']),2);self.assertLessEqual(r['margin_pp'],20)
    a,b=r['baseline_candidates'];self.assertNotEqual(a['party'],b['party']);self.assertAlmostEqual(r['margin_pp'],100*(a['votes']-b['votes'])/(a['votes']+b['votes']))
   if r['status']=='Unopposed':self.assertIsNone(r['rating'])
 def test_specific_cases(self):
  rows={(r['chamber'],r['district']):r for r in build()['races']}
  self.assertEqual(rows['house',15]['rating'],'Likely D');self.assertEqual(len(rows['house',15]['candidates']),3)
  self.assertEqual(rows['house',41]['status'],'Rated');self.assertTrue(rows['house',41]['watch'])
  self.assertIsNone(rows['house',5]['rating']);self.assertEqual(rows['senate',34]['rating'],'Lean D')
 def test_swing_arithmetic(self):
  for r in build()['races']:
   for scenario in r['scenarios']:
    self.assertAlmostEqual(scenario['dem_rep_margin_pp'],r['baseline_dem_margin_pp']+2*scenario['dem_vote_share_swing_pp'])
    self.assertAlmostEqual(sum(scenario['conditional_shares_pct'].values()),100)
 def test_key_transitions_and_independents(self):
  rows={(r['chamber'],r['district']):r for r in build()['races']}
  for key,labels in [(('house',53),['Toss Up','Tilt D','Lean D']),(('senate',17),['Tilt R','Tilt R','Toss Up']),(('house',41),['Solid R','Solid R','Likely R']),(('house',15),['Likely D','Likely D','Solid D'])]:self.assertEqual([x['rating'] for x in rows[key]['scenarios']],labels)
  self.assertEqual(rows['senate',19]['scenarios'],[]);self.assertEqual(rows['senate',19]['baseline_rating'],'Likely D');self.assertIsNone(rows['senate',19]['rating'])
 def test_reproducible_and_links(self):
  self.assertEqual(build(),build());doc=html.fromstring(render(build()));self.assertEqual(len(doc.xpath('//section[contains(@class,"ratings-board")]')),6);self.assertEqual(len(doc.xpath('//table[@class="comparison"]/tbody/tr')),13)
  for url in doc.xpath('//a[starts-with(@href,"/")]/@href'):
   path=url.split('?')[0].split('#')[0]
   if path!='/':self.assertTrue((ROOT/path.lstrip('/')).exists(),url)
if __name__=='__main__':unittest.main()
