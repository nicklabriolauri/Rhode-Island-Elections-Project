"""Exercise the workflow's publishing shell in disposable Git repositories."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load((ROOT / '.github/workflows/build-race-pages-2026.yml').read_text())
PUBLISH = next(s['run'] for s in WORKFLOW['jobs']['build']['steps']
               if s.get('name') == 'Commit generated pages')

def run(*args, cwd, env=None):
    return subprocess.run(args, cwd=cwd, env=env, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout

class RacePageWorkflow(unittest.TestCase):
    def exercise(self, changed, concurrent=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote, job, other = (root / n for n in ('remote.git', 'job', 'other'))
            run('git', 'init', '--bare', '--initial-branch=main', str(remote), cwd=root)
            run('git', 'clone', str(remote), str(job), cwd=root)
            run('git', 'config', 'user.name', 'Test', cwd=job)
            run('git', 'config', 'user.email', 'test@example.com', cwd=job)
            (job / 'scripts').mkdir(); (job / 'races').mkdir()
            (job / 'data.txt').write_text('old')
            (job / 'races/test.html').write_text('old')
            (job / 'scripts/build_race_pages_2026.py').write_text(
                'from pathlib import Path\n'
                'Path("races/test.html").write_text(Path("data.txt").read_text())\n')
            run('git', 'add', '.', cwd=job)
            run('git', 'commit', '-m', 'Initial', cwd=job)
            run('git', 'push', 'origin', 'main', cwd=job)
            run('git', 'clone', str(remote), str(other), cwd=root)
            run('git', 'config', 'user.name', 'Other', cwd=other)
            run('git', 'config', 'user.email', 'other@example.com', cwd=other)
            if changed:
                (job / 'data.txt').write_text('new')
                run('git', 'add', 'data.txt', cwd=job)
                run('git', 'commit', '-m', 'Input update', cwd=job)
                run('git', 'push', 'origin', 'main', cwd=job)
                run('git', 'pull', '--ff-only', cwd=other)
                run('python', 'scripts/build_race_pages_2026.py', cwd=job)
            # Advance main after this runner's checkout, before publishing.
            if concurrent:
                (other / 'sitemap.xml').write_text('concurrent sitemap')
                run('git', 'add', 'sitemap.xml', cwd=other)
                run('git', 'commit', '-m', 'Concurrent sitemap', cwd=other)
                run('git', 'push', 'origin', 'main', cwd=other)
            result = run('bash', '-e', '-o', 'pipefail', '-c', PUBLISH, cwd=job)
            run('git', 'pull', '--ff-only', cwd=other)
            self.assertEqual((other / 'races/test.html').read_text(), 'new' if changed else 'old')
            if concurrent:
                self.assertEqual((other / 'sitemap.xml').read_text(), 'concurrent sitemap')
            if not changed:
                self.assertIn('already current', result)

    def test_no_changes_skips_push(self): self.exercise(False, True)
    def test_changed_pages_publish(self): self.exercise(True)
    def test_concurrent_update_retries_and_preserves_it(self): self.exercise(True, True)

if __name__ == '__main__': unittest.main()
