"""Download the public ClerkBase 2026 minutes and resolutions, retaining originals.
Run: python -m pip install pymupdf beautifulsoup4; python scripts/collect_cranston_2026.py
No login, browser automation, or private data is used. The TOC, not guessed resolution
numbers, defines the import inventory. Original files are cached and hashed.
"""
from pathlib import Path
import urllib.request, concurrent.futures, json, re, hashlib, datetime
from urllib.parse import urljoin,urlparse,urldefrag
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
   documents.append({'title':title,'category':category,'url':urldefrag(urljoin(BASE,a['href']))[0],'node_id':a.get('data-node-id'),'tree_path':path})
for cat,node in [('minutes','Cranston_Minutes'),('resolution','Cranston_resolutions')]:toc(BASE+'toc/Cranston-RI?path='+node+',',cat)
(OUT/'source-indexes.json').write_text(json.dumps(indexes,indent=2))
def download(doc):
 url=doc['url'];name=urlparse(url).path.rsplit('/',1)[-1];name=(hashlib.sha256(url.encode()).hexdigest()[:12]+'.pdf') if 'DownloadMeetingFiles?' in url else name
 doc['id']=doc['category']+'-'+hashlib.sha256(url.encode()).hexdigest()[:12]
 # A category prefix avoids equal filenames in different folders.
 local=OUT/'originals'/(doc['category']+'-'+name);local.parent.mkdir(exist_ok=True)
 body,error=get(url)
 if error and local.exists():
  body=local.read_bytes();doc['collection_note']='Refresh failed; retained prior cached version: '+error
 if body and local.exists() and local.read_bytes()!=body:
  old=local.read_bytes();archive=OUT/'previous-versions';archive.mkdir(exist_ok=True);(archive/(hashlib.sha256(old).hexdigest()+'-'+local.name)).write_bytes(old)
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
# Supplement ClerkBase with the state's current public meeting filings.
SOS='https://opengov.sos.ri.gov'
dash_url=SOS+'/OpenMeetingsPublic/OpenMeetingDashboard?EntityID=715'
body,err=get(dash_url)
if err:raise RuntimeError('State meeting index unavailable; preserving previous import: '+err)
dash=BeautifulSoup(body,'html.parser');inventory=[]
for tr in dash.select('#YesterDayEntitiesSummary tbody tr'):
 cell=tr.select_one('[onclick]');stamp=tr.select_one('#hdnDateSeq')
 if not cell or not stamp or not stamp.get_text().startswith('2026'):continue
 mid=re.search(r'ViewMeetingDetails\((\d+)\)',cell.get('onclick',''))[1]
 date=stamp.get_text()[:8];date=date[:4]+'-'+date[4:6]+'-'+date[6:8]
 inventory.append({'meeting_id':mid,'date':date,'meeting':' '.join(tr.stripped_strings),'source_url':dash_url+'&MeetingID='+mid})
def details(m):
 body,err=get(SOS+'/OpenMeetingsPublic/ViewMeetingDetailByID?MeetingID='+m['meeting_id'])
 soup=BeautifulSoup(body,'html.parser');links=[]
 for a in soup.select('a[onclick]'):
  x=re.search(r"DownloadMeetingFiles\('([^']+)'\)",a['onclick'])
  if x and 'Minutes filed' in a.get_text():
   # Javascript source contains doubled backslashes. Decode only that escape.
   path=x[1].replace('\\\\','\\')
   from urllib.parse import quote
   links.append({'url':SOS+'/Common/DownloadMeetingFiles?FilePath='+quote(path,safe=''),'label':a.get_text(' ',strip=True)})
 approved=[x for x in links if x['label'].lower().startswith('approved')]
 selected=approved[0] if approved else links[0] if links else None
 m['minutes_status']='Approved' if approved else 'Draft' if selected else 'No minutes on file'
 m['minutes_url']=selected['url'] if selected else None
 m['all_minute_versions']=links
 if selected:documents.append({'title':m['date']+' City Council minutes','category':'minutes','url':selected['url'],'expected_date':m['date'],'minutes_status':m['minutes_status'],'state_meeting_id':m['meeting_id']})
 return m
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:inventory=list(pool.map(details,inventory))
# City-hosted special budget minutes are not listed in the state dashboard.
documents.append({'title':'2026-04-29 Special council budget meeting','category':'minutes','url':'https://web.cranstonri.org/ClerkDocs/CouncilMinutes/2026/2026-04-29Special_BudgetAdoptionandAmendments.pdf','expected_date':'2026-04-29','minutes_status':'City-posted minutes; approval not established'})
unique={d['url']:d for d in documents}
# The builder prefers state PDFs over older HTML and deduplicates identical meeting text.
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: docs=list(pool.map(download,unique.values()))
# Parse the adopted resolution index and resolve its attachment references.
resolutions=[]
for d in list(docs):
 if d['category']!='resolution':continue
 body,_=get(d['url']);soup=BeautifulSoup(body,'html.parser')
 for tr in soup.select('tr'):
  cells=tr.find_all('td');a=tr.select_one('a[href]')
  if len(cells)<3 or not a:continue
  num=a.get_text(strip=True)
  if not re.fullmatch(r'2026-\d+[A-Z]?',num):continue
  resolutions.append({'number':num,'title':' '.join(cells[2].stripped_strings),'adopted_date_text':' '.join(cells[1].stripped_strings),'attachment_call':a['href'],'source_url':d['url'],'original_path':None})
# Attachment template is defined by ClerkBase's public /Scripts/getAttach.js.
for res in resolutions:
 filename=re.search(r"getAttach\('([^']+)'\)",res['attachment_call'])[1]
 res['source_url']=BASE+'Content/Attachments/Cranston-RI/'+filename+'?clientSite=Cranston-RI'
 d=download({'title':res['number']+' '+res['title'],'category':'adopted-resolution','url':res['source_url']})
 docs.append(d);res['source_id']=d['id'];res['original_path']=d.get('local_path');res['document_status']=d['status']
result={'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':'https://clerkshq.com/cranston-ri','year':2026,'documents':docs,'resolutions':resolutions,'meeting_inventory':inventory,'index_errors':[{'url':x['url'],'error':x.get('error')} for x in indexes if x['status']=='error']}
if not resolutions or not inventory:raise RuntimeError('Source inventory incomplete; previous records have not been overwritten')
(OUT/'sources.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
# Retain only the TOC inventories and document-view diagnostics, not third-party JS.
(OUT/'source-indexes.json').write_text(json.dumps(indexes,indent=2))
print(json.dumps({'documents':len(docs),'meetings':len(inventory),'minutes':sum(bool(x['minutes_url']) for x in inventory),'resolutions':len(resolutions)}))
