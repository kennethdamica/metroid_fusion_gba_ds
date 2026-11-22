#!/usr/bin/env python3
"""Reproduce the old L4 return failure, then verify the fixed package boots."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
from fusion_checks import decode

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--broken-package', type=Path, required=True)
    p.add_argument('--fixed-package', type=Path, required=True)
    p.add_argument('--fixed-map', type=Path, required=True)
    p.add_argument('--broken-stage-address', type=lambda s: int(s, 0), default=0x020415E0,
                   help='gFusionBootStage in the archived Test 3 build')
    p.add_argument('--core', type=Path, default=ROOT/'.tools/melonds-custom/fixed/melondsds_libretro.dylib')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--reuse-broken-run', type=Path)
    p.add_argument('--reuse-fixed-run', type=Path)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    match = re.search(r'(0x[0-9a-fA-F]+)\s+gFusionBootStage\b', a.fixed_map.read_text())
    if not match:
        raise ValueError('Missing fixed-build stage symbol')
    checks = []

    def check(name, ok):
        checks.append(dict(name=name, passed=bool(ok)))

    def run(name, package, reuse):
        directory = reuse or a.output/name
        if reuse is None:
            subprocess.run([sys.executable, str(ROOT/'tools/emulator_test.py'),
                '--rom', str(package), '--core', str(a.core), '--output', str(directory),
                '--wait-package', '--nds-launch-path', 'fat:/Fusion.nds',
                '--frames', '600', '--capture', '180,600', '--timeout', '120',
                '--press-a-start', '500', '--press-a-end', '515'], check=True)
        report = json.loads((directory/'result.json').read_text())
        if (report['rom_sha256'] != sha(package) or report['core_sha256'] != sha(a.core)
                or report['status'] not in ('passed', 'observed')):
            raise ValueError(f'{name} run must match the package and corrected core')
        check(name+'_extraction_completed', report['package_boot']['marker'] == 'PKGREADY')
        return directory

    broken = run('broken', a.broken_package, a.reuse_broken_run)
    fixed = run('fixed', a.fixed_package, a.reuse_fixed_run)

    def stages(directory, address):
        return [struct.unpack_from('<I', f.read_bytes(), address-0x02000000)[0]
                for f in sorted(directory.glob('ram-*.bin'))]

    old_stages = stages(broken, a.broken_stage_address)
    new_stages = stages(fixed, int(match[1], 16))
    check('old_build_reproduces_stage_01_stall', len(old_stages) >= 2 and all(v == 1 for v in old_stages))
    check('fixed_build_passes_startup', len(new_stages) >= 2 and all(v == 12 for v in new_stages))
    frames = [decode(f.read_bytes())['game_frame'] for f in sorted(fixed.glob('shared-wram-*.bin'))]
    check('fixed_game_executes', len(frames) >= 2 and 0 < (frames[-1]-frames[0]) % 65536 < 1000)
    status = 'passed' if all(c['passed'] for c in checks) else 'failed'
    (a.output/'result.json').write_text(json.dumps(dict(status=status, assertions=checks,
        core_sha256=sha(a.core), broken_package_sha256=sha(a.broken_package),
        fixed_package_sha256=sha(a.fixed_package), broken_stages=old_stages,
        fixed_stages=new_stages, guest_frame_samples=frames), indent=2)+'\n')
    print(f'{status}: {a.output / "result.json"}')
    return status != 'passed'


if __name__ == '__main__':
    sys.exit(main())
