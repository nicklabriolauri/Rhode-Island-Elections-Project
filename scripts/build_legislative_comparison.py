"""Apply Burke's three-stage formula to CEL's full historical roster.
Source snapshot retains original precision. Run from any directory; no network.
"""
import json,math,csv,io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def ranks(v): return [1+sum(w>x for w in v) for x in v]
def average_ranks(v): return [1+sum(w<x for w in v)+(sum(w==x for w in v)-1)/2 for x in v]
def correlation(x,y):
 mx=sum(x)/len(x);my=sum(y)/len(y)
 return sum((a-mx)*(b-my) for a,b in zip(x,y))/math.sqrt(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))
def build():
 src=json.loads((ROOT/'data/cel_source_2023_2024.json').read_text());output={'session':'2023–2024','source_url':'https://thelawmakers.org/find-legislators','retrieved_at':'2026-10-02','formula':'N / 3 × (introduced / total introduced + passed chamber / total passed chamber + became law / total became law)','coverage':'All CEL RI 2023–2024 records; 75 House and 39 Senate legislator records (38 Senate districts, including both District 1 officeholders). Not current-incumbent-only. N counts legislator records, matching the historical roster.','bill_scope':'Unweighted substantive plus substantive-and-significant bill counts; commemorative category excluded. Source-category approximation to RIEP non-resolution bill counts, not a fresh official bill-level recount.','limitations':'Shared input data make this a methodological comparison, not independent validation. CEL uses five progress stages and significance weights; RIEP uses three unweighted stages. Neither measures all dimensions of representation.','chambers':{},'records':[]}
 for chamber,source_chamber,expected in [('house','lower',75),('senate','upper',39)]:
  rows=[r for r in src['records'] if r['row']['chamber']==source_chamber];assert len(rows)==expected
  assert len({r['row']['slesId'] for r in rows})==expected
  result=[]
  for r in rows:
   counts=[sum(r['overall'][p+'_'+stage] for p in ['s','ss']) for stage in ['bill','pass','law']]
   assert all(isinstance(x,int) and x>=0 for x in counts)
   assert counts[0]>=counts[1]>=counts[2]
   result.append({'name':r['row']['name'],'chamber':chamber,'district':r['row']['district'],'party':r['row']['party'],'cel_id':r['row']['slesId'],'introduced':counts[0],'passed_chamber':counts[1],'became_law':counts[2],'cel_sles':r['row']['sles']})
  totals=[sum(r[k] for r in result) for k in ['introduced','passed_chamber','became_law']];assert min(totals)>0
  for r in result:r['riep_index']=expected/3*sum(r[k]/t for k,t in zip(['introduced','passed_chamber','became_law'],totals))
  x=[r['riep_index'] for r in result];y=[r['cel_sles'] for r in result];assert math.isclose(sum(x)/expected,1)
  for r,rx,ry in zip(result,ranks(x),ranks(y)):r.update(riep_rank=rx,cel_rank=ry,rank_difference=rx-ry,score_difference=r['riep_index']-r['cel_sles'])
  output['chambers'][chamber]={'n':expected,'totals':dict(zip(['introduced','passed_chamber','became_law'],totals)),'pearson_r':correlation(x,y),'spearman_rho':correlation(average_ranks(x),average_ranks(y)),'mean_absolute_score_difference':sum(abs(a-b) for a,b in zip(x,y))/expected,'mean_absolute_rank_difference':sum(abs(a-b) for a,b in zip(ranks(x),ranks(y)))/expected}
  output['records']+=result
 (ROOT/'data/legislative_comparison_2023_2024.json').write_text(json.dumps(output,indent=2)+'\n')
 with (ROOT/'data/legislative_comparison_2023_2024.csv').open('w') as f:
  writer=csv.DictWriter(f,fieldnames=list(output['records'][0]),lineterminator="\n");writer.writeheader();writer.writerows(output['records'])
 print(json.dumps(output['chambers'],indent=2))
 for r in output['records']:
  if any(n in r['name'] for n in ['Burke','Ciccone']):print(r)
if __name__=='__main__':build()
