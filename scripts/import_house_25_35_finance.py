"""Import the October 9 combined House filings, validating sources before writing."""
import copy, csv, datetime, html, io, json, re, subprocess, sys
from collections import defaultdict
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from import_house_1_25_finance import money, norm, parse, period

ROOT = Path(__file__).resolve().parents[1]
RECEIPT_LINES = ['1. Aggregate', '2. Individuals', '3. Political Parties',
    '4. Political Action Committees', '5. Loan Proceeds', '6. Payroll Check off',
    '7. Interest Received', '8. State Check Off', '9. Refund/Rebate',
    '10. Party Building', '11. Matching Public Funds', '13. Returned Contributions',
    '14. Returned Checks']
EXPENSE_LINES = ['a. Aggregate Expenses', 'b. Campaign Expenses',
    'c. Repayment of Loans', 'd. Account Payable Repayments', 'e. Other']

def summary_value(text, label):
    m = re.search(re.escape(label) + r'\s+\$?\s*(\(?-?[\d,]+(?:\.\d{2})?\)?)', text.split('\f')[0])
    assert m, label
    return money(m[1])

def enrich(snapshot, values):
    buckets, donors, expenses = defaultdict(float), defaultdict(float), defaultdict(float)
    for row in values['receipt_transactions']:
        buckets[row['type']] += row['amount']
        if row['type'] in ('Individual', 'PAC', 'Party') and row['donor'] != row['type']:
            donors[(row['donor'], row['type'])] += row['amount']
    for row in values['expenditure_transactions']:
        expenses[row['category']] += row['amount']
    snapshot.update(values)
    snapshot.update(source_buckets=[dict(label=k, amount=round(v, 2),
        description='Cash receipts in the selected filing.', class_name=k.lower()) for k,v in buckets.items()],
        top_donors=[dict(donor=k[0], type=k[1], amount=round(v, 2),
        notes='Named contributor in the selected filing.') for k,v in sorted(donors.items(), key=lambda x:-x[1])],
        spending_categories=[dict(title=k, amount=round(v, 2),
        description='Cash disbursements in the selected filing.') for k,v in sorted(expenses.items(), key=lambda x:-x[1])],
        takeaways=[], explainer_cards=[], summary_intro='Verified filing-period cash receipts, spending and ending cash.')

def verify(text, values):
    receipts = round(sum(summary_value(text, label) for label in RECEIPT_LINES), 2)
    spending = round(sum(summary_value(text, label) for label in EXPENSE_LINES), 2)
    assert receipts == values['money_raised'], ('CF-2 receipts', receipts, values['money_raised'])
    assert spending == values['money_spent'], ('CF-2 spending', spending, values['money_spent'])
    for field, total in [('receipt_transactions', receipts), ('expenditure_transactions', spending)]:
        assert round(sum(r['amount'] for r in values[field]), 2) == total, field
    assert round(values['beginning_cash'] + receipts - spending, 2) == values['ending_cash']
    assert round(values['ending_cash'] - values['total_liabilities'], 2) == values['total_fund_balance']
    values['in_kind_contributions'] = summary_value(text, '6. Report of In-Kind Contributions')
    assert round(sum(r['amount'] for r in values['in_kind_transactions']), 2) == values['in_kind_contributions']

def update_coverage(profiles):
    path = ROOT/'data/finance-28-day-coverage-2026-all.csv'
    with path.open() as f:
        reader = csv.DictReader(f); fields = reader.fieldnames; rows = list(reader)
    changed = {p['slug']:p for p in profiles}
    for row in rows:
        slug = row['finance_url'].split('slug=')[-1]
        if slug in changed:
            p = changed[slug]
            row.update(status='Already on site', report_period=p['reporting_period_label'],
                document_urls='https://www.rhodeislandelectionsproject.org'+p['latest_filing_href'],
                latest_report_label=p['report_label'])
    for filename, selected in [('finance-28-day-coverage-2026-all.csv', rows),
            ('finance-28-day-coverage-2026-already-on-site.csv', [r for r in rows if r['status']=='Already on site'])]:
        with (ROOT/'data'/filename).open('w', newline='') as f:
            writer=csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); writer.writeheader(); writer.writerows(selected)
    path = ROOT/'finance-report-coverage.html'; page=path.read_text(); esc=html.escape
    table=[]
    for row in rows:
        docs=' · '.join(f'<a href="{esc(url)}">PDF ↗</a>' for url in row['document_urls'].split(' | ') if url) or '—'
        table.append(f'<tr data-chamber="{esc(row["chamber"])}" data-status="{esc(row["status"])}"><td>{esc(row["chamber"])} {esc(row["district"])}</td><td><a href="{esc(row["finance_url"])}">{esc(row["candidate"])}</a><br><small>{esc(row["party"])}</small></td><td>{esc(row["status"])}</td><td>{esc(row["latest_report_label"])}<br><small>{esc(row["report_period"])}</small></td><td>{docs}</td></tr>')
    page=re.sub(r'<tbody>.*?</tbody>', lambda m:'<tbody>'+''.join(table)+'</tbody>', page, flags=re.S)
    counts={(c,s):sum(r['chamber']==c and r['status']==s for r in rows) for c in ['House','Senate'] for s in ['Already on site','Not on site']}
    intro=f'<strong>{counts[("House","Already on site")]} House candidates</strong> and <strong>{counts[("Senate","Already on site")]} Senate candidates</strong> already have October general-election source documents. {counts[("House","Not on site")]} House and {counts[("Senate","Not on site")]} Senate candidates do not have those documents stored here.'
    page=re.sub(r'<strong>\d+ House candidates</strong>.*?stored here\.',lambda m:intro,page)
    path.write_text(page)

def main(source):
    source=Path(source); reader=PdfReader(source)
    layout=subprocess.check_output(['pdftotext','-layout',str(source),'-'],text=True).split('\f')
    starts=[i for i,p in enumerate(reader.pages) if 'SUMMARY OF CAMPAIGN ACTIVITY' in p.extract_text()]
    assert len(starts)==13, ('Unexpected report count', len(starts))
    data=json.loads((ROOT/'data/candidate_finance_2026.json').read_text()); records=[]
    for i,start in enumerate(starts):
        stop=starts[i+1] if i+1<len(starts) else len(reader.pages)
        text='\f'.join(layout[start:stop]); name=re.search(r'Name of Candidate[^\n]*\n([^\n]+)',text)[1]
        name=re.sub(r'\s+\d+\s*$','',name).strip()
        matches=[p for p in data['profiles'] if p['chamber']=='house' and
            (norm(name)==norm(p['candidate_name']) or
            name.split()[0].lower()==p['candidate_name'].split()[0].lower() and
            name.split()[-1].lower().strip('.')==p['candidate_name'].split()[-1].lower().strip('.'))]
        assert len(matches)==1, (name, [p['slug'] for p in matches]); p=matches[0]
        assert 25<=int(p['district_number'])<=35, p['slug']
        assert p['party_label'] in text.split('\f')[0], (name,'Party mismatch')
        values,dates=parse(text); verify(text,values)
        assert dates[1]=='10/05/2026'
        href=f'/data/finance-documents/{p["slug"]}-28-days-before-election-2026.pdf'
        page=ROOT/'candidates'/f'{p["slug"]}.html'; assert page.is_file(), page
        assert len(re.findall(r'<section class="card" id="finance">.*?</section>',page.read_text(),re.S))==1
        writer=PdfWriter()
        for pg in reader.pages[start:stop]: writer.add_page(pg)
        buf=io.BytesIO();writer.write(buf)
        records.append(dict(profile=p,values=values,dates=dates,name=name,start_page=start+1,
            end_page=stop,href=href,pdf=buf.getvalue()))
    # All identities, summary lines, schedules and cash equations pass before any output is written.
    for record in records:
        p=record['profile']; values=record['values']; dates=record['dates']; href=record['href']
        same=p['reporting_period_label']==period(dates) and all(p[k]==values[k] for k in ['money_raised','money_spent','ending_cash'])
        if not same:
            p.setdefault('archived_reporting_periods',[]).append({k:copy.deepcopy(v) for k,v in p.items() if k not in ['archived_reporting_periods','filing_history']})
        for a in p.get('archived_reporting_periods',[]):
            a['original_documents']=[d for d in a.get('original_documents',[]) if (ROOT/d['href'].lstrip('/')).is_file()]
            q2=ROOT/'data/finance-documents'/f'{p["slug"]}-q2-2026.pdf'
            if q2.is_file() and a['reporting_period_label']=='6/30/2026':
                qtext=subprocess.check_output(['pdftotext','-layout',str(q2),'-'],text=True)
                qvalues,qdates=parse(qtext);verify(qtext,qvalues);enrich(a,qvalues)
                a.update(reporting_period_label=period(qdates),report_label='Q2 2026 campaign finance filing',
                    latest_filing_href='/'+str(q2.relative_to(ROOT)),
                    original_documents=[dict(label='Q2 2026 CF-2 report',period=period(qdates),href='/'+str(q2.relative_to(ROOT)),embed=True)])
            if not a['original_documents']:
                a['finance_audit_note']='Previously published summary retained for comparison. Its source PDF is not available on RIEP and was not independently reverified in this import.'
        history=p.setdefault('filing_history',[])
        if not same: history.append(dict(label='28-days-before-election 2026',reporting_period_label=period(dates),
            **{k:values[k] for k in ['money_raised','money_spent','ending_cash','net_change']},notes='Supplied CF-2 filing.'))
        for stale in ['finance_source_note','finance_snapshot_note','finance_audit_note',
                'itemized_contribution_records','individual_contribution_records','pac_contribution_records','receipts_label']:
            p.pop(stale,None)
        enrich(p,values)
        p.update(report_label='2026 28-days-before-election',reporting_period_label=period(dates),
            reporting_period_type='custom',reporting_period_start=datetime.datetime.strptime(dates[0],'%m/%d/%Y').strftime('%Y-%m-%d'),
            reporting_period_end='2026-10-05', latest_filing_href=href,finance_status='available',
            source_note='Supplied Rhode Island Board of Elections CF-2 report and supporting schedules; candidate identity and summary lines verified.',
            coverage_note='Cash receipt and expense schedules reconcile to the CF-2 summary. In-kind contributions and liabilities are separate from cash activity.')
        previous=next((a for a in reversed(p.get('archived_reporting_periods',[])) if 'June 30, 2026' in a['reporting_period_label'] or a['reporting_period_label']=='6/30/2026'),None)
        if previous and dates[0]=='07/01/2026' and round(previous['ending_cash']-p['beginning_cash'],2)!=0:
            p['finance_audit_note']=f'The previously published June 30 cash balance is ${previous["ending_cash"]:,.2f}; this filing reports ${p["beginning_cash"]:,.2f} opening cash on July 1. The earlier source has not been reverified. These source figures are retained without inventing a balancing adjustment.'
        docs=[d for d in p.get('original_documents',[]) if d['href']!=href and (ROOT/d['href'].lstrip('/')).is_file()]
        p['original_documents']=docs+[dict(label='28-days-before-election 2026 CF-2 report · supplied October 9',period=period(dates),href=href,embed=True)]
        (ROOT/href.lstrip('/')).write_bytes(record['pdf'])
        esc=html.escape
        metrics=''.join(f'<div class="metric"><b>${p[k]:,.2f}</b><span>{label}</span></div>' for k,label in [('money_raised','Total receipts'),('money_spent','Spent during period'),('ending_cash','Cash at period end')])
        audit=f'<p class="source">{esc(p["finance_audit_note"])}</p>' if p.get('finance_audit_note') else ''
        inkind=f'<p class="source">The filing separately reports ${p["in_kind_contributions"]:,.2f} in in-kind contributions; this is excluded from cash receipts.</p>' if p['in_kind_contributions'] else ''
        section=f'<section class="card" id="finance"><h2>Campaign finance snapshot</h2><p class="intro">{esc(p["report_label"]+" · "+p["reporting_period_label"])}</p><div class="metric-grid">{metrics}</div><a class="finance-profile-button" href="/finance.html?slug={p["slug"]}">View campaign finance →</a>{audit}{inkind}<p class="source"><a href="{href}">Open 28-days-before-election financial report (PDF) ↗</a></p><details><summary>Read the financial report on this page</summary><iframe title="{esc(p["candidate_name"])} campaign finance report" src="{href}" loading="lazy" style="width:100%;height:640px;border:1px solid #dbe4ef;margin-top:12px"></iframe></details></section>'
        path=ROOT/'candidates'/f'{p["slug"]}.html';s=path.read_text();s=re.sub(r'<section class="card" id="finance">.*?</section>',lambda m:section,s,flags=re.S)
        s=re.sub(r'<script src="finance-periods.js[^\"]*"></script>','',s);path.write_text(s)
        print(p['district_number'],p['candidate_name'],p['money_raised'],p['money_spent'],p['ending_cash'])
    slugs={r['profile']['slug'] for r in records}
    data['donor_index']=[d for d in data['donor_index'] if d['slug'] not in slugs]
    for r in records:
        p=r['profile']
        for d in p['top_donors']:data['donor_index'].append(dict(d,**{k:p[k] for k in ['candidate_id','candidate_name','chamber','district_number','party','slug']}))
    for f in ['data/candidate_finance_2026.json','candidate_finance_2026.json']:(ROOT/f).write_text(json.dumps(data,indent=2)+'\n')
    manifest=dict(source=source.name,report_count=len(records),findings=[dict(slug=r['profile']['slug'],
        candidate_name=r['profile']['candidate_name'],pdf_candidate_name=r['name'],district=r['profile']['district_number'],
        source_start_page=r['start_page'],source_end_page=r['end_page'],reporting_period=r['profile']['reporting_period_label'],
        identity_verified=True,summary_lines_verified=True,schedules_reconciled=True,
        **{k:r['values'][k] for k in ['beginning_cash','money_raised','money_spent','ending_cash','in_kind_contributions']},
        cash_continuity_note=r['profile'].get('finance_audit_note','')) for r in records])
    (ROOT/'data/house-25-35-finance-import.json').write_text(json.dumps(manifest,indent=2)+'\n')
    update_coverage([r['profile'] for r in records])

if __name__=='__main__': main(sys.argv[1])
