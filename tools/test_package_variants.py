#!/usr/bin/env python3
"""Local patched-melonDS extraction tests for synthetic ROM identities.

These exercise packaging/save isolation, not general ROM-hack compatibility.
Requires private ROM/BIOS inputs and built ABI 2 templates.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from fusion_pack import PROFILES, runtime_directory
from package_fusion import ROOT, build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    checks = []

    def check(name, passed):
        checks.append(dict(name=name, passed=bool(passed)))
        print(('PASS ' if passed else 'FAIL ') + name, flush=True)

    def run(profile, package, sd, output, error=None):
        command = [sys.executable, str(ROOT/'tools/emulator_test.py'),
                   '--core', str(ROOT/'.tools/melonds-custom/fixed/melondsds_libretro.dylib'),
                   '--rom', str(package), '--sd-dir', str(sd), '--output', str(output),
                   '--nds-launch-path', 'fat:/'+profile.filename, '--wait-package',
                   '--frames', '300', '--capture', '300', '--timeout', '600',
                   '--press-a-start', '0', '--press-a-end', '0']
        with output.with_suffix('.log').open('w') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        boot = json.loads((output/'result.json').read_text()).get('package_boot', {})
        check(profile.key+'_'+output.name, (result.returncode == 0 and boot.get('marker') == 'PKGREADY')
              if error is None else (result.returncode != 0 and boot.get('error_code') == error))
        return boot, output/'state/save/melonDS DS/dldi_sd_card'

    for profile, filename in zip(PROFILES.values(), (
            'Metroid Fusion (USA).gba',
            'Legend of Zelda, The - A Link to the Past & Four Swords (USA).gba')):
        work = root/profile.key; work.mkdir()
        source = ROOT/filename
        variant = bytearray(source.read_bytes()); variant[-1] ^= 1
        rom = work/'synthetic-variant.gba'; rom.write_bytes(variant)
        package = work/profile.filename
        report = build(runtime_directory(profile), rom, ROOT/'gba_bios.zip', package,
                       profile=profile, allow_unsupported_rom=True)
        data = Path(report['data_directory'])
        save = Path(report['save_path'])
        sd = work/'input'; sd.mkdir()
        shutil.copy2(package, sd/profile.filename)
        original_save = profile.data_root/'rom.sav'
        (sd/original_save).parent.mkdir(parents=True)
        sentinel = bytes(range(256))*128
        (sd/original_save).write_bytes(sentinel)
        boot, installed = run(profile, package, sd, work/'first')
        check(profile.key+'_extracts_three', boot.get('extracted') == 3 and boot.get('reused') == 0)
        check(profile.key+'_installs_actual_variant', (installed/data/'rom.gba').read_bytes() == variant)
        check(profile.key+'_original_save_isolated', (installed/original_save).read_bytes() == sentinel)
        second = work/'input-second'; shutil.copytree(installed, second)
        shutil.copy2(package, second/profile.filename)
        (second/save).write_bytes(sentinel[::-1])
        boot, reused = run(profile, package, second, work/'second')
        check(profile.key+'_reuses_three', boot.get('extracted') == 0 and boot.get('reused') == 3)
        check(profile.key+'_variant_save_preserved', (reused/save).read_bytes() == sentinel[::-1])
        check(profile.key+'_original_save_still_preserved', (reused/original_save).read_bytes() == sentinel)
        # Corruption changes bytes outside compatibility ranges: it must still fail hashing.
        blob = bytearray(package.read_bytes())
        fat = struct.unpack_from('<I', blob, 0x48)[0]
        payload = struct.unpack_from('<I', blob, fat+8)[0]
        manifest = struct.unpack_from('<I', blob, fat)[0]
        for name, offset, value, error in (
            ('corrupt-payload', payload+len(variant)-2, blob[payload+len(variant)-2]^1, 4),
            ('missing-opt-in', manifest+76, 0, 4),
            ('unknown-flags', manifest+76, 2, 8),
        ):
            damaged = bytearray(blob); damaged[offset] = value
            bad = work/(name+'.nds'); bad.write_bytes(damaged)
            bad_sd = work/('input-'+name); bad_sd.mkdir()
            shutil.copy2(bad, bad_sd/profile.filename)
            _, failed = run(profile, bad, bad_sd, work/name, error=error)
            check(profile.key+'_'+name+'_not_installed', not (failed/data/'rom.gba').exists())
            check(profile.key+'_'+name+'_no_save', not (failed/save).exists())
    passed = all(c['passed'] for c in checks)
    (root/'result.json').write_text(json.dumps(dict(status='passed' if passed else 'failed',
                                                    checks=checks), indent=2)+'\n')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
