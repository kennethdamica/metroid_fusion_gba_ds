"""Local experimental-ROM tests. No ROM data is embedded in this source."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from game_profiles import FUSION, ALTTP
from package_fusion import build, inspect_package
from rom_compatibility import validate_rom


class VariantTests(unittest.TestCase):
    def test_variants_and_integrity(self):
        for profile, filename, runtime in (
            (FUSION, 'Metroid Fusion (USA).gba', 'hardware-runtime'),
            (ALTTP, 'Legend of Zelda, The - A Link to the Past & Four Swords (USA).gba', 'alttp-package-runtime'),
        ):
            with self.subTest(game=profile.key), tempfile.TemporaryDirectory() as temp:
                source = ROOT / filename
                runtime = ROOT / 'artifacts' / runtime
                if not source.exists() or not (runtime / 'manifest.json').exists():
                    self.skipTest('Local ROMs and ABI 2 runtimes required')
                original = source.read_bytes()
                work = Path(temp)
                variant = bytearray(original)
                variant[-1] ^= 1  # Synthetic identity change in end padding.
                rom = work / 'variant.gba'
                rom.write_bytes(variant)
                output = work / 'variant.nds'
                with self.assertRaisesRegex(ValueError, 'verified US'):
                    build(runtime, rom, ROOT / 'gba_bios.zip', output, profile=profile)
                self.assertFalse(output.exists())
                report = build(runtime, rom, ROOT / 'gba_bios.zip', output, profile=profile,
                               allow_unsupported_rom=True)
                actual = hashlib.sha1(variant).hexdigest()
                self.assertEqual(report['rom_sha1'], actual)
                self.assertTrue(report['experimental'])
                self.assertEqual(report['save_path'], f'{profile.directory}/{actual}/rom.sav')
                self.assertNotEqual(report['save_path'], (profile.data_root / 'rom.sav').as_posix())
                self.assertEqual(inspect_package(output, profile=None)['game'], profile.key)
                variant[-2] ^= 1
                second = validate_rom(variant, profile, True)
                self.assertNotEqual(second['rom_sha1'], actual)
                # Integrity still covers bytes outside protected adapter ranges.
                package = bytearray(output.read_bytes())
                fat = struct.unpack_from('<I', package, 0x48)[0]
                manifest = struct.unpack_from('<I', package, fat)[0]
                payload = struct.unpack_from('<I', package, fat + 8)[0]
                corrupt = work / 'corrupt.nds'
                damaged = bytearray(package); damaged[payload + len(original) - 2] ^= 1
                corrupt.write_bytes(damaged)
                with self.assertRaisesRegex(ValueError, 'Payload hash mismatch'):
                    inspect_package(corrupt, profile=None)
                for flags in (0, 2):
                    damaged = bytearray(package)
                    struct.pack_into('<I', damaged, manifest + 76, flags)
                    corrupt.write_bytes(damaged)
                    with self.assertRaises(ValueError):
                        inspect_package(corrupt, profile=None)
                for offset, error in ((0x100, 'adapter layout'), (0xAC, 'region'),
                                      (0xBC, 'revision'), (0xBD, 'checksum')):
                    damaged = bytearray(original); damaged[offset] ^= 1
                    with self.assertRaisesRegex(ValueError, error):
                        validate_rom(damaged, profile, True)
                with self.assertRaisesRegex(ValueError, '8 MiB'):
                    validate_rom(original[:-1], profile, True)
                if profile == ALTTP:
                    damaged = bytearray(original); damaged[0x3BFC58] = 0
                    with self.assertRaisesRegex(ValueError, 'graphics stream'):
                        validate_rom(damaged, profile, True)
                # New readers retain compatibility with verified ABI 1 packages.
                known = work / 'known.nds'
                build(runtime, source, ROOT / 'gba_bios.zip', known, profile=profile)
                legacy = bytearray(known.read_bytes())
                fat = struct.unpack_from('<I', legacy, 0x48)[0]
                manifest = struct.unpack_from('<I', legacy, fat)[0]
                struct.pack_into('<I', legacy, fat + 4, manifest + 76)
                struct.pack_into('<II', legacy, manifest + 8, 1, 1)
                known.write_bytes(legacy)
                self.assertFalse(inspect_package(known, profile=None)['experimental'])


if __name__ == '__main__':
    unittest.main()
