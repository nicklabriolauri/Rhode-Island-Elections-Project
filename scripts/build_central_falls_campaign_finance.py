"""Rebuild Central Falls transaction schedules using the shared Cranston PDF reader.

Run from any directory with Python and PyMuPDF. The first original document in
each period is the selected CF-2. Additional exports supply transaction evidence.
"""
import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from municipal_finance_filings import read_filing

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/municipal_campaign_finance_2026.json'
DOCS = ROOT / 'data/finance-documents'
SUPPLEMENTS = {
    ('franklin-solano', '2026-10-05'): ['6887-RICF2-241824-b63'],
    ('tatiana-baena', '2026-10-05'): [
        '8998-RICF2-241796-e4', '8998-RICF2-241796-d4',
    ],
    ('rafael-peguero', '2026-10-05'): ['9489-RICF2-241812-a621'],
}
NOTES = {
    'franklin-solano': 'The alternate export itemizes the same $1,234.23 in receipts and reports $250 in disbursements. Its $100 basketball payment matches the selected $100 CF-2 spending total. The $150 Progreso Latino entry appears only in the alternate schedule and is shown separately below.',
    'tatiana-baena': 'The two supporting schedules supply $425 and $600 in named contributions and reconcile to the selected $1,025 cash receipts. Karen Alzate appears in two exports and is counted once. The selected export labels the second $300 as Other Receipt without a name. The supporting export names Sandra Cano and classifies the full $1,025 as individual contributions.',
    'rafael-peguero': 'The two exports document $1,875.15 in cash disbursement rows against $1,900.99 on the selected CF-2. The remaining $25.84 is unreconciled. The supporting export also lists $25.84 in payable entries. Those obligations are shown separately because the supplied schedules do not establish that they were paid.',
}
BUCKETS = {
    'Individual': ('Itemized individual contributions', 'individuals'),
    'PAC': ('PAC contributions', 'pacs'),
    'Party': ('Political party contributions', 'other'),
    'Aggregate': ('Aggregate contributions (unnamed)', 'aggregate'),
    'Loan': ('Loan proceeds', 'other'),
    'Refund/Rebate': ('Refunds and rebates', 'other'),
    'Other Receipt': ('Other receipts', 'other'),
}
INDEX_FIELDS = ('candidate_id', 'candidate_name', 'chamber', 'district_number', 'party', 'slug')


def cents(amount):
    return int(Decimal(str(amount)) * 100)


def total(rows):
    return sum(cents(row['amount']) for row in rows) / 100


def update_snapshot(snapshot):
    slug = snapshot['slug']
    path = ROOT / snapshot['original_documents'][0]['href'].lstrip('/')
    paths = [path]
    for prefix in SUPPLEMENTS.get((slug, snapshot['period_end']), []):
        matches = list(DOCS.glob(prefix + '*.pdf'))
        assert len(matches) == 1, prefix
        paths.extend(matches)

    files = [read_filing(p) for p in paths]
    summary = files[0]['summary']
    for field in ('beginning_cash', 'money_raised', 'money_spent', 'ending_cash'):
        assert cents(snapshot[field]) == cents(summary[field]), (slug, field)
    period = snapshot['reporting_period_label']
    documents = [
        dict(label='Displayed CF-2 summary' if i == 0 else 'Supporting / alternate export',
             href='/' + p.relative_to(ROOT).as_posix(), period=period,
             original_filename=p.name, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        for i, p in enumerate(paths)
    ]

    def combine(schedule):
        unique = {}
        for i, filing in enumerate(files):
            occurrences = Counter()
            for row in filing[schedule]:
                if slug == 'tatiana-baena' and len(files) > 1 and i == 0 and not row.get('donor'):
                    # The corresponding $300 line is named in the supporting export.
                    continue
                key = (row['date'], row.get('donor', row.get('payee')), row['amount'],
                       row['type'], row.get('purpose', row.get('notes')), row.get('check_number'))
                occurrences[key] += 1
                unique.setdefault((key, occurrences[key]), row | {'source_document': documents[i]['href']})
        return list(unique.values())

    receipts = combine('receipts')
    expenses = combine('expenses')
    alternate = []
    if slug == 'franklin-solano' and len(files) > 1:
        alternate = [row for row in expenses if row['payee'] == 'Progreso Latino']
        assert total(alternate) == 150
        expenses = [row for row in expenses if row not in alternate]
    cash = [row for row in receipts if row['type'] != 'In-kind']
    inkind = [row for row in receipts if row['type'] == 'In-kind']
    spent = [row for row in expenses if row['type'] != 'Account Payable']
    payables = [row for row in expenses if row['type'] == 'Account Payable']
    assert cents(total(cash)) == cents(summary['money_raised']), (slug, period)
    assert cents(total(inkind)) == cents(summary['in_kind_total']), (slug, period)
    difference = cents(summary['money_spent']) - cents(total(spent))
    assert difference == (2584 if slug == 'rafael-peguero' and len(files) > 1 else 0), (slug, period)

    donors = defaultdict(list)
    categories = defaultdict(list)
    for row in cash:
        if row['donor'] and row['type'] in {'Individual', 'PAC', 'Party'}:
            donors[row['donor'], row['type']].append(row)
    for row in spent:
        category = row['category'] if row['type'] in {'Campaign Expenditure', 'Aggregate Expenditure'} else row['type']
        categories[category].append(row)
    snapshot.pop('summary_only', None)
    snapshot.update({k: v for k, v in summary.items() if k not in ('period_start', 'period_end')})
    snapshot.update(
        receipt_transactions=cash, in_kind_transactions=inkind, expenditure_transactions=spent,
        accounts_payable_transactions=payables, alternate_expenditure_transactions=alternate,
        unreconciled_cash_disbursements=difference / 100,
        original_documents=documents, latest_filing_href=documents[0]['href'],
        source_summary_variants=[dict(filing['summary'], document=doc['href'], displayed=i == 0)
                                 for i, (filing, doc) in enumerate(zip(files, documents))],
        top_donors=sorted(
            (dict(donor=name, type=kind, amount=total(rows), interest_group=kind,
                  notes='; '.join(sorted({f'Employer as filed: {x["employer"]}' for x in rows if x['employer']})))
             for (name, kind), rows in donors.items()), key=lambda x: (-x['amount'], x['donor'])),
        source_buckets=[dict(label=label, amount=total(rows), class_name=style)
                        for kind, (label, style) in BUCKETS.items()
                        if (rows := [row for row in cash if row['type'] == kind])],
        spending_categories=[dict(title=label, amount=total(rows),
                                  description='Cash disbursements itemized in the supplied CF-4 schedules.')
                             for label, rows in categories.items()],
        coverage_note='Amounts cover this reporting period. Accounts-payable entries record obligations and are shown separately from cash disbursements. In-kind support is separate from cash receipts.',
        finance_audit_note=NOTES[slug] if len(files) > 1 else
        ('Cash receipt and disbursement schedules reconcile to the selected CF-2.'
         if cash or spent else 'The selected CF-2 reports no cash receipts or cash disbursements this period.'),
        summary_intro='Central Falls City Council campaign finance. Switch reporting periods to view the corresponding cash totals, donors, expenses and source PDFs.',
    )


def main():
    data = json.loads(DATA.read_text())
    profiles = [p for p in data['profiles'] if p['municipality'] == 'Central Falls']
    slugs = {p['slug'] for p in profiles}
    index = [row for row in data['donor_index'] if row['slug'] not in slugs]
    for profile in profiles:
        for snapshot in [profile, *profile['archived_reporting_periods']]:
            update_snapshot(snapshot)
            # Index both periods, with the reporting dates attached to each result.
            index.extend(row | {key: profile[key] for key in INDEX_FIELDS}
                         | {'reporting_period_label': snapshot['reporting_period_label']}
                         for row in snapshot['top_donors'])
    data['donor_index'] = index
    data['coverage_note'] = 'Nine Cranston and seven Central Falls council finance profiles. CF-2 totals and CF-3/CF-4 schedules are filed by period. Source conflicts and unmatched amounts are documented.'
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
