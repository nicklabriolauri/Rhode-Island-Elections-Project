#!/usr/bin/env python3
"""Maintain search metadata on the candidate profiles linked in the public directory.
No visible candidate content, election status or score data is changed.
"""
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://www.rhodeislandelectionsproject.org'

class DirectoryParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.profiles = []; self.card = None; self.field = None
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'a' and 'profile-card' in a.get('class', '').split():
            self.card = {'path': a['href'].lstrip('/'), 'name': '', 'district': ''}
        if self.card and tag == 'h2': self.field = 'name'
        if self.card and tag == 'p' and 'district' in a.get('class', '').split(): self.field = 'district'
    def handle_data(self, data):
        if self.card and self.field: self.card[self.field] += data
    def handle_endtag(self, tag):
        if tag in ('h2', 'p'): self.field = None
        if tag == 'a' and self.card:
            self.profiles.append({k: v.strip() for k, v in self.card.items()}); self.card = None

def profiles():
    parser = DirectoryParser(); parser.feed((ROOT / 'candidate-profiles.html').read_text())
    if not parser.profiles: raise ValueError('Public candidate directory contains no profile links')
    if len({p['path'] for p in parser.profiles}) != len(parser.profiles): raise ValueError('Duplicate profile URLs')
    for p in parser.profiles:
        if not re.fullmatch(r'candidates/[a-z0-9-]+\.html', p['path']): raise ValueError(p['path'])
        if not p['name'] or not re.fullmatch(r'(House|Senate) District \d+', p['district']): raise ValueError(p)
        if not (ROOT / p['path']).is_file(): raise FileNotFoundError(p['path'])
    return parser.profiles

def metadata(page, title, description, url, schema, page_type):
    head, sep, tail = page.partition('</head>')
    if not sep: raise ValueError('Missing HTML head')
    if re.search(r'<meta\b[^>]*content=[\"\'][^\"\']*\bnoindex\b', head, re.I):
        raise ValueError('Refusing to override an existing noindex instruction: ' + url)
    head = re.sub(r'\n?<!-- RIEP search metadata -->.*?<!-- /RIEP search metadata -->', '', head, flags=re.S)
    head = re.sub(r'<title>.*?</title>', '', head, flags=re.I|re.S)
    head = re.sub(r'<link\b(?=[^>]*\brel=[\"\']canonical[\"\'])[^>]*>', '', head, flags=re.I)
    head = re.sub(r'<meta\b(?=[^>]*\b(?:name|property)=[\"\'](?:description|robots|og:[^\"\']+|twitter:[^\"\']+)[\"\'])[^>]*>', '', head, flags=re.I)
    attr = lambda s: html.escape(s, quote=True)
    block = ['<!-- RIEP search metadata -->', f'<title>{html.escape(title)}</title>',
        f'<meta name="description" content="{attr(description)}">', '<meta name="robots" content="index,follow">',
        f'<link rel="canonical" href="{url}">', f'<meta property="og:type" content="{page_type}">',
        f'<meta property="og:title" content="{attr(title)}">', f'<meta property="og:description" content="{attr(description)}">',
        f'<meta property="og:url" content="{url}">', '<meta property="og:site_name" content="Rhode Island Elections Project">',
        f'<meta property="og:image" content="{BASE}/riep-logo-light.png">', '<meta name="twitter:card" content="summary">',
        f'<meta name="twitter:title" content="{attr(title)}">', f'<meta name="twitter:description" content="{attr(description)}">',
        '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False).replace('<', '\\u003c') + '</script>',
        '<!-- /RIEP search metadata -->']
    return head.rstrip() + '\n' + '\n'.join(block) + '\n' + sep + tail

def main():
    records = profiles(); changed = 0
    publisher = {'@type': 'Organization', 'name': 'Rhode Island Elections Project', 'url': BASE + '/'}
    for p in records:
        path = ROOT / p['path']; before = path.read_text(); url = BASE + '/' + p['path']
        title = f"{p['name']} | RI {p['district']} | RIEP"
        desc = f"Explore {p['name']}'s RIEP profile for Rhode Island {p['district']}: campaign priorities, election history, campaign finance and available public records."
        person = {'@type': 'Person', '@id': url + '#person', 'name': p['name'], 'url': url}
        schema = {'@context': 'https://schema.org', '@type': 'WebPage', '@id': url, 'url': url,
            'name': title, 'description': desc, 'inLanguage': 'en-US', 'about': person, 'publisher': publisher,
            'isPartOf': {'@type': 'WebSite', 'name': 'Rhode Island Elections Project', 'url': BASE + '/'}}
        after = metadata(before, title, desc, url, schema, 'article')
        if after != before: path.write_text(after); changed += 1
    path = ROOT / 'candidate-profiles.html'; before = path.read_text(); url = BASE + '/candidate-profiles.html'
    schema = {'@context': 'https://schema.org', '@type': 'CollectionPage', 'url': url,
        'name': 'Rhode Island Candidate Profiles', 'publisher': publisher,
        'mainEntity': {'@type': 'ItemList', 'numberOfItems': len(records), 'itemListElement': [
            {'@type': 'ListItem', 'position': i, 'name': p['name'], 'url': BASE + '/' + p['path']}
            for i, p in enumerate(records, 1)]}}
    after = metadata(before, 'Rhode Island Candidate Profiles | RIEP', 'Browse Rhode Island House and Senate candidate profiles, campaign priorities, election history, campaign finance and public records.', url, schema, 'website')
    if after != before: path.write_text(after)
    print(f'Updated search metadata on {changed} of {len(records)} published candidate profiles')

if __name__ == '__main__': main()
