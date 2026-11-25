"""Release guards use original fixtures, never a game ROM or compiled runtime."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
from check_release import check_archives, check_tag, PLATFORMS
from fusion_pack import VERSION


class ReleaseTests(unittest.TestCase):
    def fixture(self, folder, change=None):
        lock = json.loads((ROOT/'release/packager/runtime-lock.json').read_text())
        for platform in PLATFORMS:
            executable = 'gba-ds-pack.exe' if platform.startswith('windows') else 'gba-ds-pack'
            binary = b'Original release-audit test fixture.'
            report = dict(version=VERSION, platform=platform, executable_bytes=len(binary),
                          executable_sha256=hashlib.sha256(binary).hexdigest(), runtime_lock=lock,
                          git_commit='test-commit', git_dirty=False, runtimes={key: dict(rom_sha256=value['template_sha256'])
                                                            for key, value in lock['games'].items()})
            entries = {executable: binary, 'README.txt': b'Fixture',
                       'THIRD_PARTY_NOTICES.txt': b'Fixture', 'licenses/Python-LICENSE.txt': b'Fixture'}
            entries.update({'licenses/'+p.name: p.read_bytes() for p in (ROOT/'licenses').glob('*.txt')})
            if change:
                change(entries, report)
            entries['build.json'] = json.dumps(report).encode()
            with zipfile.ZipFile(folder/f'gba-ds-pack-{VERSION}-{platform}-preview.zip', 'w') as archive:
                for name, content in entries.items():
                    archive.writestr('gba-ds-pack/'+name, content)

    def test_tag_must_match_version(self):
        check_tag('v'+VERSION)
        for tag in ('v999.0.0', 'main', VERSION, 'v'+VERSION+'-unexpected', 'v'+VERSION+'\n'):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                check_tag(tag)

    def test_valid_assets_and_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory); self.fixture(folder)
            sums = check_archives(folder, expected_commit='test-commit')
            self.assertEqual(len(sums.splitlines()), 2)
            with self.assertRaisesRegex(ValueError, 'another commit'):
                check_archives(folder, expected_commit='other-commit')

    def test_extra_local_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory); self.fixture(folder)
            (folder/'private.nds').write_bytes(b'Original fixture')
            with self.assertRaisesRegex(ValueError, 'exactly the two'):
                check_archives(folder)

    def test_archive_members_and_provenance(self):
        changes = [
            lambda entries, report: entries.update({'rom.gba': b'Original fixture'}),
            lambda entries, report: entries.update({'../escape.txt': b'Original fixture'}),
            lambda entries, report: entries.update({'licenses/binary.txt': b'\0bad'}),
            lambda entries, report: entries.pop('licenses/Python-LICENSE.txt'),
            lambda entries, report: report.update(executable_sha256='wrong'),
            lambda entries, report: report.update(runtimes={}),
        ]
        for index, change in enumerate(changes):
            with self.subTest(case=index), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory); self.fixture(folder, change)
                with self.assertRaises(ValueError):
                    check_archives(folder)


if __name__ == '__main__':
    unittest.main()
