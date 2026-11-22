"""Regression checks for public sponsorship attribution and profile rendering."""
import json, unittest
from pathlib import Path
from html.parser import HTMLParser
from cranston_sponsorship import ROOT, DATA, build, render_profile, attribution

class Structure(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag=='a':self.links.append(a.get('href',''))

class SponsorshipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=build()
    def test_distinct_counts_and_role_separation(self):
        d=self.data;self.assertEqual(len(d['proposals']),42)
        expected={'Wall':(17,3),'Ritz':(13,2),'Andujar':(12,3),'Traficante':(12,3),'Vaziri':(10,4),'Haroian':(12,4),'Graziano':(8,2),'Buonanno':(15,3),'Campopiano':(7,0)}
        for m in d['members']:
            c=m['counts'];self.assertEqual((c['sponsor'],c['cosponsor']),expected[m['surname']])
            self.assertEqual(c['sponsor'],sum(c[k] for k in ['ordinance','position','symbolic','recognition']))
        for p in d['proposals']:self.assertFalse(set(p['sponsors'])&set(p['cosponsors']))
    def test_repeat_item_not_new_sponsorship(self):
        p=next(p for p in self.data['proposals'] if p['id']=='ordinance-06-15-02')
        self.assertEqual(len(p['observations']),2)
        self.assertEqual(p['sponsors'],['bridget-r-graziano'])
    def test_mover_does_not_receive_sponsorship(self):
        ps,co,ev=attribution('On motion by Councilman Andujar, seconded by Councilwoman Vaziri',self.data['members'])
        self.assertEqual((ps,co,ev),([],[],''))
        p=next(p for p in self.data['proposals'] if p['id']=='ordinance-09-22-02')
        self.assertEqual(p['sponsors'],['frank-j-ritz-jr'])
        self.assertNotIn('christopher-e-buonanno',p['sponsors'])
    def test_incoming_members_do_not_inherit_predecessor_counts(self):
        for slug in ['sara-jane-haupt','avery-therese-mangahas','steven-a-stycos']:
            text=(ROOT/'candidates'/(slug+'.html')).read_text()
            text=render_profile(text,slug,self.data)
            section=text.split('id="sponsorship"',1)[1].split('</section>',1)[0]
            self.assertNotIn('sponsorship-stats',section)
            self.assertIn('incoming term begins January 4, 2027',section)
    def test_idempotence_anchors_and_sources(self):
        for path in (ROOT/'candidates').glob('*.html'):
            slug=path.stem;text=path.read_text()
            if 'id="sponsorship"' not in text:continue
            out=render_profile(text,slug,self.data)
            self.assertEqual(out,render_profile(out,slug,self.data))
            parser=Structure();parser.feed(out)
            self.assertEqual(len(parser.ids),len(set(parser.ids)),slug)
            self.assertEqual(parser.ids.count('sponsorship'),1)
            self.assertIn('#sponsorship',parser.links)
            for href in parser.links:
                if href.startswith('#'):self.assertIn(href[1:],parser.ids)
        for p in self.data['proposals']:
            self.assertTrue(p['observations'])
            for o in p['observations']:self.assertTrue(o['source_url'].startswith('https://'))

if __name__=='__main__':unittest.main()
