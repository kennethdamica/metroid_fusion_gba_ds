"""Public CI coverage: no copyrighted inputs, built runtime or installed packages."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PublicCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT/'tools/fusion_pack.py'), *map(str, args)],
                              cwd=ROOT, text=True, capture_output=True, timeout=15)

    def test_help_without_runtime(self):
        result = self.run_cli('--help')
        self.assertEqual(result.returncode, 0)
        self.assertIn('--bios', result.stdout)
        self.assertIn('--output', result.stdout)

    def test_version(self):
        result = self.run_cli('--version')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), 'fusion-pack 0.1.0')

    def test_supported_game_list_is_json(self):
        result = self.run_cli('--list-games', '--json')
        self.assertEqual(result.returncode, 0)
        games = json.loads(result.stdout)
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]['sha1'], 'ca33f4348c2c05dd330d37b97e2c5a69531dfe87')

    def test_missing_arguments_are_usage_error(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('Traceback', result.stderr)

    def test_conflicting_modes_are_usage_error(self):
        result = self.run_cli('--list-games', '--inspect', 'unused.nds')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('Traceback', result.stderr)

    def test_bad_input_creates_no_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            rom = folder/'invalid.gba'
            rom.write_bytes(b'Original test data, not a game ROM.')
            result = self.run_cli(rom, '--bios', folder/'absent.bin',
                                  '-o', folder/'output.nds', '--json')
            self.assertEqual(result.returncode, 1)
            self.assertIn('error', json.loads(result.stderr))
            self.assertEqual(list(folder.iterdir()), [rom])

    def test_invalid_package_is_read_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'invalid.nds'
            original = b'Original malformed-container test data.'
            path.write_bytes(original)
            result = self.run_cli('--inspect', path, '--json')
            self.assertEqual(result.returncode, 1)
            self.assertIn('error', json.loads(result.stderr))
            self.assertEqual(path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
