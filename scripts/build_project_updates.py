"""Build the public updates archive, RSS feed and homepage updates from one dated list."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from email.utils import format_datetime
from html import escape as e
import json,re,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
BASE='https://www.rhodeislandelectionsproject.org'
def build():
 data=json.loads((ROOT/'data/project-updates.json').read_text());items=data['updates'];ids=set()
 for x in items:
  assert re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',x['id']),x['id']
  assert x['id'] not in ids;ids.add(x['id'])
  dt=datetime.fromisoformat(x['published_at'].replace('Z','+00:00'));assert dt.tzinfo is not None
  for link in x['links']:assert link['url'].startswith(('/', 'https://'))
 items.sort(key=lambda x:x['published_at'],reverse=True)
 def published(x):
  return datetime.fromisoformat(x['published_at'].replace('Z','+00:00')).astimezone(ZoneInfo('America/New_York'))
 def metadata(x, date_format):
  return f'<div class="update-meta"><span>{e(x["category"])}</span><time datetime="{e(x["published_at"])}">{published(x).strftime(date_format)}</time></div>'
 articles=[]
 for x in items:
  paragraphs=''.join('<p>'+e(p)+'</p>' for p in x['body'])
  links=''.join(f'<a href="{e(l["url"])}">{e(l["label"])}</a>' for l in x['links'])
  articles.append(f'''<article id="{x['id']}" class="update-notice">{metadata(x, "%b %-d, %Y · %-I:%M %p %Z")}<h2>{e(x['title'])}</h2>{paragraphs}<div class="update-links">{links}</div><a class="permalink" href="/updates.html#{x['id']}" aria-label="Permanent link to {e(x['title'])}">Permalink</a></article>''')
 html='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Project Updates | Rhode Island Elections Project</title><meta name="description" content="The latest Rhode Island Elections Project coverage announcements, new tools and data updates, with publication dates and links."><link rel="canonical" href="https://www.rhodeislandelectionsproject.org/updates.html"><link rel="icon" href="/favicon.ico"><link rel="alternate" type="application/rss+xml" title="RIEP Project Updates" href="/updates.xml"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700;800&amp;family=Sora:wght@600;700;800&amp;display=swap"><link rel="stylesheet" href="/updates.css?v=20261126"><meta property="og:title" content="Project Updates | Rhode Island Elections Project"><meta property="og:description" content="New coverage, data and tools from RIEP, with dated announcements."><meta property="og:type" content="website"><meta property="og:url" content="https://www.rhodeislandelectionsproject.org/updates.html"></head><body><a class="skip-link" href="#updates">Skip to updates</a><header><div class="header-inner"><a class="brand" href="/"><img src="/riep-logo-light.png" alt="" width="62" height="54"><span>Rhode Island<br>Elections Project</span></a><nav aria-label="Site navigation"><a href="/">Home</a><a href="/general-results.html">Election results</a><a href="/candidate-profiles.html">Candidate profiles</a><a href="/updates.html" aria-current="page">Project updates</a></nav></div></header><main><div class="page-intro"><h1>Project updates</h1><p>New election coverage, public records and tools from the Rhode Island Elections Project.</p><p class="archive-note">This announcement archive begins November 22, 2026. Times show when notices were published, in Eastern Time. Earlier project work is summarized in the opening notices.</p><a class="feed-link" href="/updates.xml">Subscribe via RSS</a></div><section id="updates" aria-label="Latest project announcements" class="updates-grid">'''+''.join(articles)+'''</section></main><footer>Rhode Island Elections Project · Independent, nonpartisan public information.<br><a href="/">Return to the homepage</a></footer></body></html>'''
 (ROOT/'updates.html').write_text(html+'\n')
 rss=ET.Element('rss',version='2.0');ch=ET.SubElement(rss,'channel')
 for k,v in [('title','RIEP Project Updates'),('link',BASE+'/updates.html'),('description','Coverage, public records and tools from the Rhode Island Elections Project.'),('language','en-us')]:ET.SubElement(ch,k).text=v
 for x in items:
  entry=ET.SubElement(ch,'item');url=BASE+'/updates.html#'+x['id']
  for k,v in [('title',x['title']),('link',url),('guid',url),('description','\n\n'.join(x['body'])),('pubDate',format_datetime(datetime.fromisoformat(x['published_at'].replace('Z','+00:00'))))]:ET.SubElement(entry,k).text=v
 (ROOT/'updates.xml').write_bytes(ET.tostring(rss,encoding='utf-8',xml_declaration=True))
 index=ROOT/'index.html';s=index.read_text()
 ticker=''.join(f'<a href="/updates.html#{x["id"]}">{e(x.get("ticker",x["title"]))}</a>' for x in items[:5])
 s,n=re.subn(r'<div class="riep-ticker-group">.*?</div>',lambda _:'<div class="riep-ticker-group">'+ticker+'</div>',s,count=1,flags=re.S);assert n==1,'Ticker group missing'
 cards=[]
 for x in items[:3]:
  url=f'/updates.html#{x["id"]}'
  summary=f'<p>{e(x["body"][0])}</p>' if x['body'] else ''
  cards.append(f'<article class="home-update-card">{metadata(x, "%b %-d, %Y")}<h3><a href="{url}">{e(x["title"])}</a></h3>{summary}</article>')
 start='<!-- project-updates-preview:start -->'
 end='<!-- project-updates-preview:end -->'
 preview=(f'<section class="home-updates-preview" aria-labelledby="homeUpdatesTitle">'
          '<div class="home-updates-heading"><h2 id="homeUpdatesTitle">Project updates</h2>'
          '<a href="/updates.html">View all updates <span aria-hidden="true">→</span></a></div>'
          f'<div class="home-updates-grid">{"".join(cards)}</div></section>')
 s,n=re.subn(re.escape(start)+r'.*?'+re.escape(end),lambda _:start+preview+end,s,count=1,flags=re.S)
 assert n==1,'Homepage updates preview markers missing'
 index.write_text(s)
 print(f'Built {len(items)} dated notices, RSS and homepage ticker')
if __name__=='__main__':build()
