"""Profile isolation and deterministic Zelda packaging with local private inputs."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'tools'))
from game_profiles import ALTTP, FUSION
from package_fusion import build, inspect_package, ROOT


class ZeldaPackageTests(unittest.TestCase):
    def test_profile_identity_and_save_isolation(self):
        self.assertNotEqual(ALTTP.data_root, FUSION.data_root)
        self.assertEqual(len(ALTTP.nds_title), 12)
        self.assertEqual(len(ALTTP.magic), 8)
        self.assertNotEqual(ALTTP.magic, FUSION.magic)

    def test_local_package_and_cross_game_rejection(self):
        runtime=ROOT/'artifacts/alttp-package-runtime'
        rom=ROOT/'Legend of Zelda, The - A Link to the Past & Four Swords (USA).gba'
        bios=ROOT/'gba_bios.zip'
        if not all(p.exists() for p in (runtime/'manifest.json',rom,bios)):
            self.skipTest('Requires local Zelda build, ROM and BIOS')
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'Zelda.nds'
            report=build(runtime,rom,bios,out,profile=ALTTP)
            self.assertEqual(report['save_path'],str(ALTTP.data_root/'rom.sav'))
            self.assertEqual(inspect_package(out,profile=ALTTP)['package_sha256'],report['package_sha256'])
            with self.assertRaises(ValueError): inspect_package(out)
            with self.assertRaises(ValueError): build(runtime,rom,bios,Path(temp)/'wrong.nds')
            another=Path(temp)/'again.nds'
            build(runtime,rom,bios,another,profile=ALTTP)
            self.assertEqual(out.read_bytes(),another.read_bytes())
            with self.assertRaises(ValueError): build(runtime,rom,bios,out,profile=ALTTP)
            wrong=Path(temp)/'runtime';shutil.copytree(runtime,wrong)
            manifest=json.loads((wrong/'manifest.json').read_text());manifest['game']='fusion'
            (wrong/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'another game'):
                build(wrong,rom,bios,Path(temp)/'wrong-profile.nds',profile=ALTTP)
