"""Read Rhode Island Board of Elections CF-2 totals and CF-3/CF-4 schedules."""
import bisect
import re
from decimal import Decimal

import fitz

clean=lambda s:' '.join(s.split())
left={'beginning_cash':313.1,'aggregate_receipts':349.1,'individual_receipts':397.1,'party_receipts':409.1,'pac_receipts':421.1,'loan_receipts':433.1,'refund_receipts':481.1,'total_cash':601.1,'aggregate_expenses':625.1,'campaign_expenses':637.1,'loan_repayments':649.1,'ap_repayments':661.1}
right={'ending_cash':373.1,'in_kind_total':427.1,'total_assets':517.1,'accounts_payable':559.1,'loans_payable':571.1,'total_liabilities':637.1,'total_fund_balance':649.1}

def read_filing(path):
 doc=fitz.open(path);texts=[p.get_text() for p in doc];offsets=[];pos=0
 for t in texts:offsets.append(pos);pos+=len(t)+1
 text='\n'.join(texts);summary={}
 for side,fields in [(0,left),(1,right)]:
  for k,y in fields.items():
   words=[w[4] for w in doc[0].get_text('words') if abs(w[1]-y)<.3 and (240<w[0]<290 if side==0 else 530<w[0]<590)];v=''.join(words).replace('$','').replace(',','').strip();summary[k]=float(Decimal(v.replace('(','-').replace(')','')))
 summary['money_raised']=round(summary['total_cash']-summary['beginning_cash'],2);summary['money_spent']=round(summary['total_cash']-summary['ending_cash'],2)
 summary['period_start'],summary['period_end']=re.findall(r'\d{2}/\d{2}/\d{4}',texts[0])[:2]
 receipts=[];expenses=[]
 for m in re.finditer(r'Item\s*\nReceipt Date\nDeposit Date\nContribution Amount\n(.*?)Contributor Information',text,re.S):
  b=m.group(1);v=b.split('Transaction Type')[0];a=re.search(r'([\d,]+\.\d{2})',v)
  if not a:continue
  dates=re.findall(r'\d{2}/\d{2}/\d{4}',v);first=re.search(r'Prefix\nFirst Name\nMI\n(.*?)Last Name or PAC/Party Committee Name',b,re.S)[1];last=re.search(r'Last Name or PAC/Party Committee Name\nSuffix\n(.*?)Street Address',b,re.S)[1];typ=clean(re.search(r'Transaction Type\nContribution Type\n(.*?)In Kind/Other Receipts Description',b,re.S)[1]);note=clean(re.search(r'In Kind/Other Receipts Description\n(.*?)Prefix',b,re.S)[1]);emp=clean(re.search(r'Employer Name\n(.*?)Street Address',b,re.S)[1])
  receipts.append(dict(date=dates[0],deposit_date=dates[1] if len(dates)>1 else None,donor=clean(first+' '+last),amount=float(Decimal(a[1].replace(',',''))),type='Refund/Rebate' if 'Refund/Rebate' in typ else 'Loan' if 'Loan Proceeds' in typ else 'Aggregate' if 'Aggregate' in typ else 'In-kind' if 'In-Kind' in typ else 'PAC' if typ.endswith('PAC') else 'Party' if typ.endswith('Party') else 'Individual',notes=note,employer=emp,source_page=bisect.bisect_right(offsets,m.start()),source_type=typ))
 for m in re.finditer(r'Check #\nExpenditure Date\nPayment Date\nExpenditure Amount\nDisbursement Type\nExpenditure Type\nPurpose of Expenditure\n(.*?)Payee Information',text,re.S):
  b=m[1];am=re.search(r'\$([\d,]+\.\d{2})',b)
  if not am:continue
  after=b[am.end():].strip().splitlines();kind=after[0];cat=after[1];dates=re.findall(r'\d{2}/\d{2}/\d{4}',b[:am.start()]);payee=re.search(r'Zip\n(.*?)Suffix\nLastName or Vendor Name',b,re.S)[1];pn=bisect.bisect_right(offsets,m.start());page=doc[pn-1];before=text[offsets[pn-1]:m.start()];idx=len(re.findall(r'Check #\nExpenditure Date',before));labels=page.search_for('Purpose of Expenditure');rect=labels[idx];purpose=clean(page.get_text(clip=fitz.Rect(27,rect.y1+1,590,rect.y1+14)))
  expenses.append(dict(check_number=clean(b[:re.search(r'\d{2}/\d{2}/\d{4}',b).start()]),date=dates[0],payment_date=dates[1] if len(dates)>1 else None,payee=clean(payee) or 'Aggregate expenditure',amount=float(Decimal(am[1].replace(',',''))),type=kind,category=cat,purpose=purpose,source_page=pn))
 return dict(summary=summary,receipts=receipts,expenses=expenses,pages=len(doc))
