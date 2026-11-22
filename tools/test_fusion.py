#!/usr/bin/env python3
"""Run the fixed-core Fusion boot, movement, room-transition and jump regression."""
import argparse
from pathlib import Path
import subprocess
import sys
from fusion_checks import CAPTURES

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--sd-dir', type=Path, default=ROOT / 'fixtures/local/fusion')
parser.add_argument('--dual-screen', action='store_true', help='Test the enhanced runtime and its bottom display')
args = parser.parse_args()
command = [sys.executable, str(ROOT / 'tools/emulator_test.py'),
           '--core', str(ROOT / '.tools/melonds-custom/fixed/melondsds_libretro.dylib'),
           '--rom', str(ROOT / ('artifacts/dual-screen/sdcard/FusionDual.nds' if args.dual_screen else 'artifacts/baseline/sdcard/GBARunner3.nds')),
           '--sd-dir', str(args.sd_dir),
           '--input-script', str(ROOT / 'tests/fusion/gameplay-inputs.json'),
           '--output', str(args.output), '--frames', '30000', '--capture', CAPTURES,
           '--timeout', '240', '--assert-fusion']
if args.dual_screen:
    command += ['--assert-fusion-screen']
else:
    command += ['--gba-rom-arg', 'fat:/rom.gba']
sys.exit(subprocess.call(command))
