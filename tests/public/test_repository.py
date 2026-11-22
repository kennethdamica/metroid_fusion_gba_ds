"""Verify the publication check rejects tracked private files and broken links."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
from check_repository import check, source_files


class RepositoryChecks(unittest.TestCase):
    def test_git_ignores_private_inputs_at_multiple_depths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'.gitignore').write_bytes((ROOT/'.gitignore').read_bytes())
            for name in ('game.gba', 'fixtures/custom/BIOS.BIN', 'saved/game.sav',
                         'artifacts/report.json', 'build.log'):
                path = root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('Original test placeholder.')
            (root/'README.md').write_text('# Example\n')
            self.assertEqual(source_files(root), ['.gitignore', 'README.md'])
            self.assertFalse((root/'.git').exists())

    def test_tracked_ignored_input_is_still_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(['git', 'init', '--quiet', str(root)], check=True)
            (root/'.gitignore').write_text('*.gba\n')
            (root/'private.gba').write_text('Original test placeholder.')
            subprocess.run(['git', '-C', str(root), 'add', '--force', 'private.gba'], check=True)
            names = source_files(root)
            self.assertIn('private.gba', names)
            self.assertTrue(any('private/generated' in error for error in check(root, names)))

    def test_link_to_unpublished_local_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'README.md').write_text('[Report](artifacts/report.json)\n')
            (root/'artifacts').mkdir()
            (root/'artifacts/report.json').write_text('{}')
            self.assertTrue(any('link absent' in error for error in check(root, ['README.md'])))

    def test_valid_public_link_and_syntax(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'README.md').write_text('[Tool](tool.py)\n')
            (root/'tool.py').write_text('print("hello")\n')
            self.assertEqual(check(root, ['README.md', 'tool.py']), [])


if __name__ == '__main__':
    unittest.main()
