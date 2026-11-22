"""Collect public Cranston source indexes. No personal or authenticated data."""
from pathlib import Path
import urllib.request, concurrent.futures, json, re
from urllib.parse import urljoin
OUT=Path("data/cranston/records-2026")
OUT.mkdir(parents=True,exist_ok=True)
def get(url):
 try:
  req=urllib.request.Request(url,headers={"User-Agent":"RhodeIslandElectionsProject/1.0 (public records research)"})
  with urllib.request.urlopen(req,timeout=25) as r: body=r.read()
  return {"url":url,"text":body.decode("utf-8","replace"),"status":"ok"}
 except Exception as e: return {"url":url,"status":"error","error":str(e)}
urls=["https://clerkshq.com/cranston-ri","https://www.cranstonri.gov/sitemap.xml","https://www.cranstonri.gov/city-council2026120/","https://web.cranstonri.org/clerkdocs/CouncilMinutes/2026/"]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: pages=list(ex.map(get,urls))
scripts=[]
for p in pages[:1]:
 for src in re.findall(r'<script[^>]+src=["\']([^"\']+)',p.get("text",""),re.I):
  if not any(x in src for x in ["google","jquery","bootstrap","fontawesome"]):scripts.append(urljoin(p["url"],src))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: pages+=list(ex.map(get,scripts))
(OUT/"source-indexes.json").write_text(json.dumps(pages,indent=2))
print([(p["url"],p["status"],len(p.get("text",""))) for p in pages])
