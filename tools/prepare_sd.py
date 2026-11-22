#!/usr/bin/env python3
"""Create a new local GBARunner3 SD folder from a user-supplied BIOS and ROM."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
from fusion_profile import BIOS_SHA256

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bios', type=Path, required=True, help='Original GBA BIOS .bin or .zip')
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--skip-intro', action='store_true')
    parser.add_argument('--probe', action='store_true', help='Disable capture/centering and saving for our diagnostic')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output must be new; existing saves are never overwritten')
    bios = args.bios.read_bytes()
    if zipfile.is_zipfile(args.bios):
        with zipfile.ZipFile(args.bios) as package:
            candidates = [i for i in package.infolist() if i.file_size == 16384 and not i.is_dir()]
            if len(candidates) != 1:
                parser.error('BIOS zip must contain exactly one 16 KiB file')
            bios = package.read(candidates[0])
    if hashlib.sha256(bios).hexdigest() != BIOS_SHA256:
        parser.error('BIOS hash differs from the verified original GBA BIOS')
    if not args.rom.is_file() or args.rom.stat().st_size < 192:
        parser.error('Missing or truncated GBA ROM')
    baseline = ROOT / 'artifacts/baseline/sdcard'
    if not (baseline / 'GBARunner3.nds').is_file():
        parser.error('Build baseline first')
    shutil.copytree(baseline, args.output)
    (args.output / '_gba/bios.bin').write_bytes(bios)
    shutil.copy2(args.rom, args.output / 'rom.gba')
    settings = {}
    if args.skip_intro:
        settings['runSettings'] = {'skipBiosIntro': True}
    if args.probe:
        settings.update(displaySettings={'enableCenterAndMask': False, 'borderImage': 'none'},
                        gameSettings={'saveType': 'none'})
    if settings:
        (args.output / '_gba/gbarunner3.json').write_text(json.dumps(settings, indent=2) + '\n')
    (args.output / 'LAUNCHING.txt').write_text(
        'Launch GBARunner3.nds with fat:/rom.gba as argv[1].\n'
        'Do not use the fallback path for games with saves: the pinned baseline\n'
        'can overwrite rom.gba when the fallback filename cannot be edited.\n'
        'On this Mac use tools/test_fusion.py, which supplies the argument.\n'
        'This SD folder has not been validated on physical hardware.\n')
    print(f'SD folder ready: {args.output.resolve()}')
    print('Launch with ROM argument fat:/rom.gba; see LAUNCHING.txt')
    print('ROM SHA1:', hashlib.sha1(args.rom.read_bytes()).hexdigest())

if __name__ == '__main__':
    main()
