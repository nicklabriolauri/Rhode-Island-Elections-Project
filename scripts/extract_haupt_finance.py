"""Extract transaction schedules from Haupt's supplied CF-3/CF-4 PDFs.

Run from any directory; writes JSON to stdout. The published summary and source
version audit are in data/municipal_campaign_finance_2026.json and
 data/sara-jane-haupt-finance-audit.json. Requires PyMuPDF.
"""
from pathlib import Path
from decimal import Decimal
import fitz,re,json
def clean(s):return ' '.join(s.split())

def extract(documents):
 out={}
 for original_name, f in documents.items():
  doc=fitz.open(f);receipts=[];expenses=[]
  for page_no,page in enumerate(doc,1):
   t=page.get_text()
   if 'Receipt Date\nDeposit Date\nContribution Amount' in t:
    blocks=re.findall(r'Item\s*\nReceipt Date\nDeposit Date\nContribution Amount\n(.*?)Contributor Information',t,re.S)
    for block in blocks:
     values=block.split('Transaction Type')[0]
     if not re.search(r'([\d,]+\.\d{2})',values):continue
     dates=re.findall(r'\d{2}/\d{2}/\d{4}',values);amount=re.search(r'([\d,]+\.\d{2})',values).group(1)
     first=re.search(r'Prefix\nFirst Name\nMI\n(.*?)Last Name or PAC/Party Committee Name',block,re.S).group(1)
     last=re.search(r'Last Name or PAC/Party Committee Name\nSuffix\n(.*?)Street Address',block,re.S).group(1)
     typ=re.search(r'Transaction Type\nContribution Type\n(.*?)In Kind/Other Receipts Description',block,re.S).group(1)
     note=re.search(r'In Kind/Other Receipts Description\n(.*?)Prefix',block,re.S).group(1)
     employer=re.search(r'Employer Name\n(.*?)Street Address',block,re.S).group(1)
     receipts.append({'date':dates[0],'deposit_date':dates[1] if len(dates)>1 else None,'donor':clean(first+' '+last).title(),'amount':float(Decimal(amount.replace(',',''))),'type':'In-kind' if 'In-Kind' in typ else 'Individual','notes':clean(note),'employer':clean(employer),'source_page':page_no})
   if 'Check #\nExpenditure Date' in t:
    for match in re.finditer(r'Check #\nExpenditure Date\nPayment Date\nExpenditure Amount\nDisbursement Type\nExpenditure Type\nPurpose of Expenditure\n(.*?)Payee Information',t,re.S):
     b=match.group(1);amount=re.search(r'\$([\d,]+\.\d{2})',b).group(1);dates=re.findall(r'\d{2}/\d{2}/\d{4}',b.split('Campaign Expenditure')[0]);category=b.split('Campaign Expenditure\n')[1].split('\n')[0];payee=re.search(r'Zip\n(.*?)\nSuffix\nLastName or Vendor Name',b,re.S).group(1)
     # Read the purpose from its labeled PDF rectangle, excluding address fields.
     purpose_labels=page.search_for('Purpose of Expenditure');headers=page.search_for('Check #')
     idx=len([m for m in re.finditer(r'Check #\nExpenditure Date',t[:match.start()])]);rect=purpose_labels[idx]
     purpose=clean(page.get_text(clip=fitz.Rect(27,rect.y1+1,590,rect.y1+14)))
     expenses.append({'date':dates[0],'payee':clean(payee),'amount':float(Decimal(amount.replace(',',''))),'type':'Expenditure','category':clean(category),'purpose':purpose,'source_page':page_no})
  out[original_name]={'receipts':receipts,'expenses':expenses,'pages':len(doc)}
 return out

if __name__ == '__main__':
 root=Path(__file__).resolve().parents[1]
 audit=json.loads((root/'data/sara-jane-haupt-finance-audit.json').read_text())
 documents={v['original_filename']:root/v['href'].lstrip('/') for v in audit['documents'].values()}
 print(json.dumps(extract(documents),indent=2))
