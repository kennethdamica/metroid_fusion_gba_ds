#!/usr/bin/env python3
"""Full-boot Zelda package/touch regression; original ROM/save files are untouched."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from alttp_checks import CAPTURES, verify
from game_profiles import ALTTP
from package_fusion import ROOT, inspect_package


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package',type=Path,default=ROOT/'artifacts/alttp-world-map-v2/Zelda.nds')
    p.add_argument('--core',type=Path,default=ROOT/'.tools/melonds-custom/fixed/melondsds_libretro.dylib')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--maps',action='store_true',help='Also exercise dungeon displays with test-only location fixtures')
    p.add_argument('--video-stability',action='store_true',help='Compare consecutive frames in stable inventory/map scenes; requires --maps')
    p.add_argument('--video-debug-address',type=lambda s:int(s,0),help='gZeldaVideoDebug address from this runtime link map')
    p.add_argument('--transitions',action='store_true',help='Stress repeated item/tab/floor changes; requires --maps')
    p.add_argument('--render-debug-address',type=lambda s:int(s,0),help='gZeldaRenderDebug address; requires --transitions')
    p.add_argument('--record-audio',action='store_true',help='Record item/map transition audio from frame 20000 onward')
    args=p.parse_args()
    if args.video_debug_address is not None and (not args.video_stability or not 0x02040000<=args.video_debug_address<=0x023FFFE0):p.error('Video debug address requires --video-stability and a valid runtime RAM address')
    if args.video_stability and not args.maps:p.error('--video-stability requires --maps')
    if args.transitions and not args.maps:p.error('--transitions requires --maps')
    if args.render_debug_address is not None and (not args.transitions or not 0x02040000<=args.render_debug_address<=0x023FFFE0):p.error('Render debug address requires --transitions and runtime RAM')
    if args.output.exists():p.error('Output must be new; existing saves are never overwritten')
    info=inspect_package(args.package,profile=ALTTP)
    root=args.output.resolve();root.mkdir(parents=True)
    checks=[];runs={}
    captures=CAPTURES
    input_script=ROOT/'tests/alttp/live-input.json'
    memory_script=ROOT/'tests/alttp/owned-items.json'
    if args.maps:
        from alttp_map_checks import MAP_CAPTURES
        captures += ','+MAP_CAPTURES
        for name,base,extra in [('input',input_script,'map-input.json'),('memory',memory_script,'map-states.json')]:
            combined=json.loads(base.read_text())+json.loads((ROOT/'tests/alttp'/extra).read_text())
            (root/f'{name}.json').write_text(json.dumps(combined,indent=2)+'\n')
        input_script=root/'input.json';memory_script=root/'memory.json'
    if args.transitions:
        from alttp_transition_checks import TRANSITION_CAPTURES
        captures+=','+TRANSITION_CAPTURES
        combined=json.loads(input_script.read_text())+json.loads((ROOT/'tests/alttp/transition-input.json').read_text())
        input_script=root/'transition-input.json';input_script.write_text(json.dumps(combined,indent=2)+'\n')
    def check(name,passed):checks.append(dict(name=name,passed=bool(passed)))
    if args.video_stability:
        from alttp_video_checks import VIDEO_CAPTURES
        captures += ','+VIDEO_CAPTURES
    def sd(run):return root/run/'state/save/melonDS DS/dldi_sd_card'
    def run(name,source,live=False):
        command=[sys.executable,str(ROOT/'tools/emulator_test.py'),'--core',str(args.core.resolve()),
            '--rom',str(args.package.resolve()),'--sd-dir',str(source),'--wait-package',
            '--output',str(root/name),'--frames',('22650' if args.transitions else '21960' if args.maps else '21400') if live else '1200','--capture',captures if live else '1200',
            '--timeout','600','--press-a-start','0','--press-a-end','0']
        if live:command += ['--input-script',str(input_script),'--memory-script',str(memory_script)]
        if live and args.record_audio:command += ['--audio-start','20000','--audio-end','22650' if args.transitions else '21960' if args.maps else '21400']
        with (root/f'{name}.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
        result=json.loads((root/name/'result.json').read_text());runs[name]=result
        return result
    try:
        first=root/'input-first';first.mkdir();shutil.copy2(args.package,first/ALTTP.filename)
        result=run('first',first,True)
        check('first_launch_extracts_three_files',result['package_boot']['extracted']==3 and result['package_boot']['reused']==0)
        for name in ('rom.gba','bios.bin','config.json'):
            check(f'extracted_{name}_matches_bundle',hashlib.sha256((sd('first')/ALTTP.data_dir/name).read_bytes()).hexdigest()==info['payloads'][name]['sha256'])
        runs['gameplay']=verify(root/'first',(sd('first')/ALTTP.data_dir/'rom.gba').read_bytes(),check)
        if args.maps:
            from alttp_map_checks import verify_maps
            verify_maps(root/'first',check,args.render_debug_address)
        if args.video_stability:
            from alttp_video_checks import verify_video
            runs['video_stability']=verify_video(root/'first',check,args.video_debug_address)
        if args.transitions:
            from alttp_transition_checks import verify_transitions
            runs['transitions']=verify_transitions(root/'first',check,args.render_debug_address)
        save=sd('first')/ALTTP.data_root/'rom.sav'
        saved=save.read_bytes();check('separate_8KiB_save',len(saved)==8192 and any(b!=255 for b in saved))
        second=root/'input-second';shutil.copytree(sd('first'),second)
        shutil.copy2(args.package,second/ALTTP.filename)
        result=run('second',second)
        check('second_launch_reuses_three_files',result['package_boot']['extracted']==0 and result['package_boot']['reused']==3)
        check('second_launch_preserves_save_bytes',(sd('second')/ALTTP.data_root/'rom.sav').read_bytes()==saved)
        check('package_unchanged',hashlib.sha256(args.package.read_bytes()).hexdigest()==info['package_sha256'])
    except Exception as error:
        check('suite_completed',False);runs['error']=str(error)
    result=dict(status='passed' if all(c['passed'] for c in checks) else 'failed',
        fixture='Ownership of boomerang and lamp, plus magic, is seeded only in emulator RAM. Item selection is real touch input.',
        map_fixture=args.maps,
        assertions=checks,runs=runs)
    (root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f"{result['status']}: {root/'result.json'}")
    return result['status']!='passed'


if __name__=='__main__':sys.exit(main())
