"""Download the public ClerkBase 2026 minutes and resolutions, retaining originals.
Run: python -m pip install pymupdf beautifulsoup4; python scripts/collect_cranston_2026.py
No login, browser automation, or private data is used. The TOC, not guessed resolution
numbers, defines the import inventory. Original files are cached and hashed.
"""
from pathlib import Path
import urllib.request, concurrent.futures, json, re, hashlib, datetime
from urllib.parse import urljoin,urlparse
from bs4 import BeautifulSoup
import fitz
OUT=Path(__file__).resolve().parents[1]/'data/cranston/records-2026'
OUT.mkdir(parents=True,exist_ok=True)
BASE='https://clerkshq.com/'
def get(url):
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'RhodeIslandElectionsProject/1.0 (public council records research)'})
  with urllib.request.urlopen(req,timeout=40) as r: body=r.read()
  return body,None
 except Exception as e:return b'',str(e)
indexes=[];documents=[];seen=set()
def toc(url,category,in_year=False,depth=0):
 if url in seen or depth>6:return
 seen.add(url);body,err=get(url)
 indexes.append({'url':url,'status':'error' if err else 'ok','error':err,'text':body.decode('utf-8','replace')})
 if err:return
 soup=BeautifulSoup(body,'html.parser')
 for a in soup.select('a.js-doc-view'):
  title=a.get('title') or a.get_text(' ',strip=True)
  child=a.get('data-toc-url');path=a.get('data-path','')
  year=in_year or bool(re.search(r'2026',title+' '+path))
  if child:
   # Root contains years. Never traverse another year's subtree.
   if year or (not re.search(r'20\d\d',title+' '+path) and depth<2):toc(urljoin(BASE,child),category,year,depth+1)
  elif year and a.get('href'):
   documents.append({'title':title,'category':category,'url':urljoin(BASE,a['href']),'node_id':a.get('data-node-id'),'tree_path':path})
for cat,node in [('minutes','Cranston_Minutes'),('resolution','Cranston_resolutions')]:toc(BASE+'toc/Cranston-RI?path='+node+',',cat)
(OUT/'source-indexes.json').write_text(json.dumps(indexes,indent=2))
def download(doc):
 url=doc['url'];name=urlparse(url).path.rsplit('/',1)[-1]
 doc['id']=doc['category']+'-'+hashlib.sha256(url.encode()).hexdigest()[:12]
 # A category prefix avoids equal filenames in different folders.
 local=OUT/'originals'/(doc['category']+'-'+name);local.parent.mkdir(exist_ok=True)
 body=local.read_bytes() if local.exists() else get(url)[0]
 if not body:
  doc.update(status='unavailable',pages=[]);return doc
 local.write_bytes(body);doc['sha256']=hashlib.sha256(body).hexdigest();doc['local_path']='/'+str(local.relative_to(OUT.parents[2]))
 if body.startswith(b'%PDF'):
  pdf=fitz.open(stream=body,filetype='pdf');pages=[]
  for page in pdf:
   text=page.get_text(sort=True)
   method='embedded text'
   if len(text.strip())<40:
    try:text=page.get_textpage_ocr(language='eng',dpi=200,full=True).extractText();method='OCR'
    except Exception as e:text='';method='OCR unavailable: '+str(e)
   pages.append({'page':page.number+1,'text':text,'method':method})
  doc['pages']=pages;doc['links']=[l['uri'] for p in pdf for l in p.get_links() if l.get('uri')]
 else:
  soup=BeautifulSoup(body,'html.parser');doc['pages']=[{'page':1,'text':soup.get_text('\n',strip=True),'method':'HTML text'}]
  doc['links']=[urljoin(url,a['href']) for a in soup.select('a[href]')]
 doc['status']='downloaded' if any(p['text'].strip() for p in doc['pages']) else 'needs OCR'
 return doc
unique={d['url']:d for d in documents}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: docs=list(pool.map(download,unique.values()))
result={'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':'https://clerkshq.com/cranston-ri','year':2026,'documents':docs,'index_errors':[{'url':x['url'],'error':x['error']} for x in indexes if x['error']]}
(OUT/'sources.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({'documents':len(docs),'categories':{c:sum(d['category']==c for d in docs) for c in ['minutes','resolution']},'index_pages':len(indexes),'errors':result['index_errors']}))
