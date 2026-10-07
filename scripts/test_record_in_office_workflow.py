"""Test the actual workflow publisher against a concurrent main-branch update."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load((ROOT / '.github/workflows/update-record-in-office.yml').read_text())
PUBLISH = next(s['run'] for s in WORKFLOW['jobs']['build-records']['steps']
               if s.get('name') == 'Commit verified dataset')


def run(*args, cwd, check=True):
    return subprocess.run(args, cwd=cwd, check=check, capture_output=True, text=True)


class RecordWorkflow(unittest.TestCase):
    def exercise(self, changed=True, concurrent=False, invalid=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote, job, other = (root / n for n in ('remote.git', 'job', 'other'))
            run('git', 'init', '--bare', '--initial-branch=main', str(remote), cwd=root)
            run('git', 'clone', str(remote), str(job), cwd=root)
            run('git', 'config', 'user.name', 'Test', cwd=job)
            run('git', 'config', 'user.email', 'test@example.com', cwd=job)
            (job / 'scripts').mkdir(); (job / 'data').mkdir()
            shutil.copyfile(ROOT / 'scripts/validate_incumbent_records.py',
                            job / 'scripts/validate_incumbent_records.py')
            (job / 'source.txt').write_text('initial')
            (job / 'build_incumbent_records_2026.py').write_text(
                'import json\nfrom pathlib import Path\n'
                'source=Path("source.txt").read_text()\n'
                'legislation={k:1 for k in ("prime_sponsored","cosponsored","passed_chamber","became_law")}\n'
                'if source=="invalid":legislation["became_law"]=None\n'
                'record={"candidate_name":"Test","source_revision":source,"legislation":legislation,"attendance":{"status":"verified_from_official_journals"}}\n'
                'Path("data/incumbent_records_2026.json").write_text(json.dumps({"records":[record]}))\n'
                'Path("data/incumbent_records_2026_audit.json").write_text(json.dumps({"source_revision":source}))\n')
            (job / 'build_attendance_2025_2026.py').write_text(
                'import json\nfrom pathlib import Path\n'
                'Path("data/attendance_sessions_2025_2026.json").write_text("[]")\n'
                'Path("data/attendance_audit_2025_2026.json").write_text(json.dumps({"coverage":{k:40 for k in ("2025_house","2025_senate","2026_house","2026_senate")},"excluded_or_failed_journals":[]}))\n')
            for script in ['build_incumbent_records_2026.py', 'build_attendance_2025_2026.py']:
                run(sys.executable, script, cwd=job)
            run('git', 'add', '.', cwd=job)
            run('git', 'commit', '-m', 'Initial', cwd=job)
            run('git', 'push', 'origin', 'main', cwd=job)
            run('git', 'clone', str(remote), str(other), cwd=root)
            run('git', 'config', 'user.name', 'Other', cwd=other)
            run('git', 'config', 'user.email', 'other@example.com', cwd=other)
            if changed:
                (job / 'source.txt').write_text('first update')
                run('git', 'add', 'source.txt', cwd=job)
                run('git', 'commit', '-m', 'Change inputs', cwd=job)
                run('git', 'push', 'origin', 'main', cwd=job)
                run('git', 'pull', '--ff-only', cwd=other)
                run(sys.executable, 'build_incumbent_records_2026.py', cwd=job)
            before = run('git', 'rev-parse', 'HEAD', cwd=other).stdout.strip()
            if concurrent:
                (other / 'candidate.html').write_text('New candidate profile and finance PDF')
                if changed:
                    (other / 'source.txt').write_text('invalid' if invalid else 'newest inputs')
                run('git', 'add', '.', cwd=other)
                run('git', 'commit', '-m', 'Concurrent candidate and source updates', cwd=other)
                run('git', 'push', 'origin', 'main', cwd=other)
                before = run('git', 'rev-parse', 'HEAD', cwd=other).stdout.strip()
            result = run('bash', '-e', '-o', 'pipefail', '-c', PUBLISH, cwd=job, check=not invalid)
            if invalid:
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('records requiring review: 1', result.stdout)
                self.assertEqual(run('git', 'ls-remote', 'origin', 'main', cwd=other).stdout.split()[0], before)
            else:
                run('git', 'pull', '--ff-only', cwd=other)
                records = json.loads((other / 'data/incumbent_records_2026.json').read_text())['records']
                expected = 'newest inputs' if concurrent and changed else 'first update' if changed else 'initial'
                self.assertEqual(records[0]['source_revision'], expected)
                if not changed:self.assertIn('already current', result.stdout)
            if concurrent:
                self.assertEqual((other / 'candidate.html').read_text(), 'New candidate profile and finance PDF')

    def test_no_changes_skips_push(self): self.exercise(False, True)
    def test_verified_changes_publish(self): self.exercise()
    def test_concurrent_update_rebuilds_from_latest_inputs(self): self.exercise(concurrent=True)
    def test_invalid_retry_data_is_not_published(self): self.exercise(concurrent=True, invalid=True)


if __name__ == '__main__': unittest.main()
