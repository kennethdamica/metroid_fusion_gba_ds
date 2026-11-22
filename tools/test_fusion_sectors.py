#!/usr/bin/env python3
"""Load real Fusion sector rooms through emulator-only transition injection.

These are controlled warps, not a full-game playthrough. The release runtime
never writes game state. Every run has an isolated SD card and save.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from PIL import Image
from fusion_checks import decode
from fusion_screen_checks import ROOM_CELLS, centered_frame, map_image, read_digit
from package_fusion import ROOT, DATA_DIR, inspect_package

# Door 1 destination and room-cell fixtures checked against pinned mf room
# headers, clipdata dimensions and original minimap artwork.
SECTORS = [
    (1, 0, 5, 1, 2, 2), (2, 0, 6, 2, 2, 4),
    (3, 0, 8, 2, 2, 4), (4, 2, 19, 4, 1, 1),
    (5, 0, 4, 2, 2, 3), (6, 0, 3, 2, 3, 2),
]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--reuse-run', type=Path, help='Verify an existing matching sector run')
    args = p.parse_args()
    info = inspect_package(args.package)
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    events = []
    captures = [24000]
    for area, room, x, y, w, h in SECTORS:
        frame = 24001 + (area - 1) * 700
        captures.append(frame + 499)
        # Use the game's normal room loader and fade-in, after reaching real
        # gameplay through the existing new-game input script. Unlock map
        # downloads only in this test to inspect each whole sector's artwork.
        for offset, data in ((0x2C, bytes([area])), (0x2E, b'\x01'),
                             (0xBE0, b'\0\0'), (0x4E58, b'\x02'+b'\0'*7),
                             (0x1310, (999).to_bytes(2, 'little')*2),
                             (0x131E, b'\x7f')):
            events.append(dict(frame=frame, region='shared', offset=offset, hex=data.hex()))
        ROOM_CELLS[area, room] = {(i, j) for j in range(y, y+h) for i in range(x, x+w)}
    # Room bounds overlap other rooms. ARC room 00 has a cutout beneath its
    # upper-right cell (including room 33 at 5,4). NOC room 29, the recharge
    # station at 3,2, lies inside room 00's bounds. Their closed map walls must
    # keep them unhighlighted. Checked against room headers and map artwork.
    ROOM_CELLS[5, 0] -= {(5, 3), (5, 4)}
    ROOM_CELLS[6, 0] -= {(3, 2)}
    script = root/'warps.json'
    script.write_text(json.dumps(events, indent=2)+'\n')
    inputs = [e for e in json.loads((ROOT/'tests/fusion/gameplay-inputs.json').read_text())
              if e['end'] < 24000]
    (root/'inputs.json').write_text(json.dumps(inputs, indent=2)+'\n')
    if args.reuse_run:
        run = args.reuse_run.resolve()
    else:
        sd = root/'input-sd'; sd.mkdir()
        shutil.copy2(args.package, sd/'Fusion.nds')
        run = root/'run'
        command = [sys.executable, str(ROOT/'tools/emulator_test.py'), '--core',
                   str(ROOT/'.tools/melonds-custom/fixed/melondsds_libretro.dylib'),
                   '--rom', str(args.package.resolve()), '--sd-dir', str(sd), '--output', str(run),
                   '--wait-package', '--nds-launch-path', 'fat:/Fusion.nds', '--frames', '28300',
                   '--capture', ','.join(map(str, captures)), '--fusion-state', '--timeout', '600',
                   '--input-script', str(root/'inputs.json'), '--memory-script', str(script)]
        with (root/'driver.log').open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    report = json.loads((run/'result.json').read_text())
    if report['rom_sha256'] != info['package_sha256'] or report.get('memory_test_events') != events:
        raise ValueError('Sector evidence must match the package and exact warp script')
    rom = (run/'state/save/melonDS DS/dldi_sd_card'/DATA_DIR/'rom.gba').read_bytes()
    checks, states = [], []
    def check(name, passed):
        checks.append(dict(name=name, passed=bool(passed)))
        print(('PASS ' if passed else 'FAIL ')+name, flush=True)
    for area, frame in enumerate(captures):
        shared = (run/f'shared-wram-{frame:06d}.bin').read_bytes()
        ram = (run/f'ram-{frame:06d}.bin').read_bytes()
        state = decode(shared); states.append(dict(frame=frame, **state))
        expected_room = 0 if area != 4 else 2
        check(f'area_{area}_real_gameplay', state['main_mode']==1 and state['sub_mode']==2 and
              state['demo']==0 and state['area']==area and state['room']==expected_room)
        top = Image.open(run/f'top-{frame:06d}.png').convert('RGB')
        bottom = Image.open(run/f'bottom-{frame:06d}.png').convert('RGB')
        check(f'area_{area}_centered_frame', centered_frame(top))
        check(f'area_{area}_game_visible', len(top.getcolors(49152) or []) >= 32)
        check(f'area_{area}_live_label', ''.join(read_digit(bottom, 48+i*8, 8) for i in range(2)) == f'{area:02X}')
        if (state['area'],state['room']) in ROOM_CELLS:
            expected = map_image(rom, ram, state, shared)
            expected.save(root/f'expected-area-{area}.png')
            check(f'area_{area}_map_and_highlight_pixels',
                  bottom.crop((0,24,256,184)).tobytes() == expected.tobytes())
    status = 'passed' if all(c['passed'] for c in checks) else 'failed'
    (root/'result.json').write_text(json.dumps(dict(status=status, package_sha256=info['package_sha256'],
        core_sha256=report['core_sha256'], test_method='emulator-assisted real room loads',
        checks=checks, states=states), indent=2)+'\n')
    return status != 'passed'


if __name__ == '__main__':
    sys.exit(main())
