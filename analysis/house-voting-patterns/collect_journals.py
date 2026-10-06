"""Archive the official journals identified in the repository attendance inventory.
Compare collected inventory with freshly archived official year indexes before release.
"""
import json,hashlib,subprocess,urllib.request,concurrent.futures
from pathlib import Path
ROOT=Path(__file__).parent
manifest=[dict(year=s['year'],date=s['date'],url=s['source_url'],pdf=f"journals/HJ-{s['date']}.pdf",text=f"text/HJ-{s['date']}.txt") for s in json.loads((ROOT/'source_sessions.json').read_text())]
(ROOT/'journals').mkdir(exist_ok=True);(ROOT/'text').mkdir(exist_ok=True)
def fetch(x):
 p=ROOT/x['pdf'];t=ROOT/x['text']
 for attempt in range(3):
  try:
   if not p.exists():
    with urllib.request.urlopen(x['url'],timeout=45) as response:content=response.read()
    assert content.startswith(b'%PDF'),'Not a PDF'
    p.write_bytes(content)
   subprocess.run(['pdftotext','-layout',str(p),str(t)],check=True,capture_output=True)
   x.update(status='downloaded',sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
   return x
  except Exception as e:
   if attempt==2:x.update(status='failed',error=str(e));return x
out=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
 for x in ex.map(fetch,manifest):
  out.append(x)
  if len(out)%10==0 or x['status']=='failed':print('Collected',len(out),'/',len(manifest),x['date'],x['status'],flush=True)
(ROOT/'manifest.json').write_text(json.dumps(out,indent=2));assert all(x['status']=='downloaded' for x in out)
