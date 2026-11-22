#!/usr/bin/env python3
"""Regress real demo exit, saved-game load, pause/resume and map highlighting."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from PIL import Image
from fusion_checks import decode
from fusion_screen_checks import map_image, read_digit
from package_fusion import ROOT, DATA_ROOT, DATA_DIR, inspect_package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--sd-dir', type=Path, required=True, help='Extracted SD with the initial playable save from the full regression')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    package = args.package.resolve()
    info = inspect_package(package)
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    source = root / 'input'
    shutil.copytree(args.sd_dir, source)
    shutil.copy2(package, source/'Fusion.nds')
    saved = (source/DATA_ROOT/'rom.sav').read_bytes()
    events = [dict(start=f, end=f+15, buttons=['start']) for f in range(6200, 8100, 300)]
    events += [dict(start=f, end=f+12, buttons=['a']) for f in range(8400, 16000, 120)]
    events += [dict(start=18020, end=18040, buttons=['start']),
               dict(start=18460, end=18480, buttons=['start']),
               dict(start=19000, end=19300, buttons=['left'])]
    script=root/'inputs.json';script.write_text(json.dumps(events, indent=2)+'\n')
    command=[sys.executable, str(ROOT/'tools/emulator_test.py'), '--core',
             str(ROOT/'.tools/melonds-custom/fixed/melondsds_libretro.dylib'),
             '--rom', str(package), '--sd-dir', str(source), '--output', str(root/'run'),
             '--wait-package', '--nds-launch-path', 'fat:/Fusion.nds', '--frames', '20000',
             '--capture', '6000,17000,18000,18400,18800,20000', '--input-script', str(script),
             '--fusion-state', '--timeout', '600']
    with (root/'driver.log').open('w') as log:
        code=subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
    checks=[]
    def check(name, passed):
        checks.append(dict(name=name, passed=bool(passed)))
        print(('PASS ' if passed else 'FAIL ')+name, flush=True)
    check('emulator_completes', code == 0)
    run=root/'run'
    report=json.loads((run/'result.json').read_text())
    check('reuses_extracted_files', report.get('package_boot',{}).get('reused')==3)
    rom=(source/DATA_DIR/'rom.gba').read_bytes()
    states={}
    for frame in (6000,17000,18000,18400,18800,20000):
        shared=(run/f'shared-wram-{frame:06d}.bin').read_bytes()
        state=decode(shared);states[frame]=state
        if frame in (17000,18000,18800,20000):
            live=state['main_mode']==1 and state['sub_mode']==2 and state['demo']==0
            check(f'normal_gameplay_after_demo_{frame}', live and state['demo_seen']!=0)
            if live:
                actual=Image.open(run/f'bottom-{frame:06d}.png').convert('RGB')
                expected=map_image(rom,(run/f'ram-{frame:06d}.bin').read_bytes(),state,shared)
                check(f'geographic_map_after_demo_{frame}',actual.crop((0,24,256,184)).tobytes()==expected.tobytes())
    check('attract_demo_was_started', states[6000]['demo_seen'] != 0)
    check('idle_gameplay_keeps_frame_rate', (states[18000]['game_frame']-states[17000]['game_frame'])%65536 >= 999)
    paused=Image.open(run/'bottom-018400.png').convert('RGB')
    check('pause_is_not_live_gameplay',states[18400]['main_mode']!=1 or states[18400]['sub_mode']!=2)
    check('pause_hides_live_ids', ''.join(read_digit(paused,48+i*8,8) for i in range(2))=='--')
    colors=paused.crop((0,24,256,184)).getcolors(40960)
    check('pause_keeps_map_without_gold_highlight',len(colors)>3 and not any(r>240 and 160<g<200 and b<70 for n,(r,g,b) in colors))
    check('room_transition_updates_map',states[20000]['room']!=states[18800]['room'])
    after=(run/'state/save/melonDS DS/dldi_sd_card'/DATA_ROOT/'rom.sav').read_bytes()
    check('primary_save_slots_preserved',all(saved[i:i+0x1200]==after[i:i+0x1200] for i in (0x200,0x2600,0x4A00)))
    status='passed' if all(c['passed'] for c in checks) else 'failed'
    (root/'result.json').write_text(json.dumps(dict(status=status,package_sha256=info['package_sha256'],checks=checks,states=states),indent=2)+'\n')
    return status!='passed'


if __name__=='__main__':
    sys.exit(main())
