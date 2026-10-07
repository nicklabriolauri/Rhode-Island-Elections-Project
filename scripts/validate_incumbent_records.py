"""Reject incomplete official bill and Journal attendance data before publication."""
import json
import sys


def validate():
    with open('data/incumbent_records_2026.json') as f:
        records = json.load(f).get('records', [])
    with open('data/attendance_audit_2025_2026.json') as f:
        audit = json.load(f)
    bad = []
    for r in records:
        legislation = r.get('legislation', {})
        attendance = r.get('attendance', {})
        if any(legislation.get(k) is None for k in
               ('prime_sponsored', 'cosponsored', 'passed_chamber', 'became_law')):
            bad.append((r.get('candidate_name'), 'legislation'))
        if attendance.get('status') != 'verified_from_official_journals':
            bad.append((r.get('candidate_name'), 'attendance'))
    coverage = audit.get('coverage', {})
    failed_journals = audit.get('excluded_or_failed_journals', [])
    required = ('2025_house', '2025_senate', '2026_house', '2026_senate')
    thin = {k: coverage.get(k, 0) for k in required if coverage.get(k, 0) < 20}
    print('records:', len(records))
    print('coverage:', coverage)
    print('failed journals:', len(failed_journals))
    print('records requiring review:', len(bad))
    if bad or failed_journals or thin:
        print('thin coverage:', thin)
        print(*bad[:30], sep='\n')
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(validate())
