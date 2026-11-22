#!/usr/bin/env python3
"""Test single-NDS first boot, gameplay, reuse/save preservation and recovery."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from fusion_checks import CAPTURES
from package_fusion import ROOT, DATA_DIR, DATA_ROOT, inspect_package


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reuse-first-run', type=Path, help='Reuse a completed, passing 30,000-frame run of this exact package')
    args = parser.parse_args()
    package = args.package.resolve()
    info = inspect_package(package)
    root = args.output.resolve()
    if root.exists():
        parser.error('Output directory must be new')
    root.mkdir(parents=True)
    checks, runs = [], {}
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
        print(('PASS ' if condition else 'FAIL ') + name, flush=True)
    def sd_for(name):
        if name == 'first-boot' and args.reuse_first_run:
            return args.reuse_first_run.resolve() / 'state/save/melonDS DS/dldi_sd_card'
        return root / name / 'state/save/melonDS DS/dldi_sd_card'
    def run(name, source, full=False, rom=package, launcher='fat:/Fusion.nds', error=None, frames=1200):
        command = [sys.executable, str(ROOT/'tools/emulator_test.py'),
                   '--core', str(ROOT/'.tools/melonds-custom/fixed/melondsds_libretro.dylib'),
                   '--rom', str(rom), '--sd-dir', str(source), '--output', str(root/name),
                   '--nds-launch-path', launcher, '--wait-package', '--timeout', '600',
                   '--frames', '30000' if full else str(frames),
                   '--capture', CAPTURES if full else str(frames),
                   '--press-a-start', '0', '--press-a-end', '0']
        if full:
            command += ['--input-script',str(ROOT/'tests/fusion/gameplay-inputs.json'),
                        '--assert-fusion','--assert-fusion-screen']
        with (root/f'{name}.driver.log').open('w') as log:
            code = subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
        report = json.loads((root/name/'result.json').read_text())
        runs[name] = dict(exit_code=code, package_boot=report.get('package_boot'), report=str(root/name/'result.json'))
        if error is None:
            check(name+'_boots', code == 0 and report.get('package_boot',{}).get('marker') == 'PKGREADY')
            if code:
                raise RuntimeError(f'{name} failed; see {root/name}')
        else:
            boot=report.get('package_boot',{})
            check(name+'_rejected', code != 0 and boot.get('marker') == 'PKGERROR' and boot.get('error_code') == error)
        return report

    try:
        first = root/'input-first';first.mkdir()
        shutil.copy2(package,first/'Fusion.nds')
        check('initial_SD_contains_only_one_NDS', sorted(p.name for p in first.iterdir()) == ['Fusion.nds'])
        if args.reuse_first_run:
            report=json.loads((args.reuse_first_run/'result.json').read_text())
            core=ROOT/'.tools/melonds-custom/fixed/melondsds_libretro.dylib'
            if (report.get('rom_sha256')!=info['package_sha256'] or report.get('core_sha256')!=sha(core)
                    or report.get('status')!='passed' or report.get('frames_completed')!=30000
                    or report.get('sd_inputs')!={'Fusion.nds': info['package_sha256']}):
                raise ValueError('Reusable first run must pass and match the exact package hash')
            runs['first-boot']=dict(reused_report=str((args.reuse_first_run/'result.json').resolve()))
        else:
            report = run('first-boot',first,full=True)
        check('first_boot_extracts_three_files', report['package_boot']['extracted']==3 and report['package_boot']['reused']==0)
        check('all_gameplay_and_display_assertions_pass', len(report['assertions'])>=74 and all(a['passed'] for a in report['assertions']))
        installed = sd_for('first-boot')
        for name in ('rom.gba','bios.bin','config.json'):
            check('extracted_'+name+'_matches_bundle', sha(installed/DATA_DIR/name)==info['payloads'][name]['sha256'])
        save = installed/DATA_ROOT/'rom.sav'
        saved_hash=sha(save)
        check('first_boot_has_separate_save', save.stat().st_size==32768)

        # Reinstall the original NDS to model copying a package update over the
        # launcher. Retain the entire extracted tree and the actual game save.
        second=root/'input-second';shutil.copytree(installed,second)
        shutil.copy2(package,second/'Fusion.nds')
        before={str(p.relative_to(second)):sha(p) for p in (second/DATA_ROOT).rglob('*') if p.is_file()}
        report=run('second-handoff',second,frames=300)
        check('second_boot_reuses_all_without_extraction', report['package_boot']['extracted']==0 and report['package_boot']['reused']==3)
        after=sd_for('second-handoff')
        check('second_handoff_preserves_save_bytes',sha(after/DATA_ROOT/'rom.sav')==saved_hash)
        check('second_handoff_preserves_all_extracted_bytes',all((after/p).is_file() and sha(after/p)==h for p,h in before.items()))
        run('second-boot',second)
        old_save=(second/DATA_ROOT/'rom.sav').read_bytes()
        new_save=(sd_for('second-boot')/DATA_ROOT/'rom.sav').read_bytes()
        # Fusion creates/repairs its redundant A backup on this boot. The pinned
        # decomp's SaveFile is 0x1200 bytes; primary slots start at 0x200/2600/4A00.
        check('second_game_boot_preserves_all_primary_save_slots',all(old_save[i:i+0x1200]==new_save[i:i+0x1200] for i in (0x200,0x2600,0x4A00)))
        check('second_game_boot_has_matching_A_backup',new_save[0x200:0x1400]==new_save[0x1400:0x2600])
        check('second_game_boot_keeps_nonempty_A_save',any(b!=255 for b in new_save[0x200:0x1400]))

        recovery=root/'input-recovery';shutil.copytree(second,recovery)
        (recovery/DATA_DIR/'bios.bin').unlink()
        (recovery/DATA_DIR/'bios.bin.part').write_bytes(b'interrupted write')
        report=run('recovery',recovery,launcher='menu:/no-argv',frames=300)
        after=sd_for('recovery')
        check('fallback_filename_and_partial_extraction_recover',report['package_boot']['extracted']==1 and report['package_boot']['reused']==2)
        check('recovered_BIOS_matches_bundle',sha(after/DATA_DIR/'bios.bin')==info['payloads']['bios.bin']['sha256'])
        check('recovery_preserves_save_bytes',sha(after/DATA_ROOT/'rom.sav')==saved_hash)
        check('no_partial_files_remain',not list((after/DATA_ROOT).rglob('*.part')))

        damaged=root/'input-damaged';damaged.mkdir()
        data=bytearray(package.read_bytes())
        fat=struct.unpack_from('<I',data,0x48)[0]
        rom_start=struct.unpack_from('<I',data,fat+8)[0]
        data[rom_start+0x1000]^=1
        bad=root/'damaged.nds';bad.write_bytes(data)
        shutil.copy2(bad,damaged/'Fusion.nds')
        run('damaged-payload',damaged,rom=bad,error=4)
        after=sd_for('damaged-payload')
        check('damaged_payload_never_installed',not (after/DATA_DIR/'rom.gba').exists())
        check('damaged_payload_never_creates_save',not (after/DATA_ROOT/'rom.sav').exists())

        malformed=root/'input-malformed';malformed.mkdir()
        data=bytearray(package.read_bytes());struct.pack_into('<I',data,fat+8,0)
        bad=root/'malformed.nds';bad.write_bytes(data);shutil.copy2(bad,malformed/'Fusion.nds')
        run('invalid-bounds',malformed,rom=bad,error=8)
        check('invalid_bounds_never_install_data',not (sd_for('invalid-bounds')/DATA_DIR).exists())
        check('source_NDS_unchanged',sha(package)==info['package_sha256'])
    except Exception as e:
        check('suite_completed',False)
        runs['error']=str(e)
    passed=all(c['passed'] for c in checks)
    result=dict(status='passed' if passed else 'failed',package=info,assertions=checks,runs=runs)
    (root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    suite=ET.Element('testsuite',name='Fusion package',tests=str(len(checks)),failures=str(sum(not c['passed'] for c in checks)))
    for c in checks:
        case=ET.SubElement(suite,'testcase',name=c['name'])
        if not c['passed']: ET.SubElement(case,'failure',message=c['name'])
    ET.ElementTree(suite).write(root/'junit.xml',encoding='utf-8',xml_declaration=True)
    print(f"{result['status']}: {root/'result.json'}")
    return 0 if passed else 1


if __name__=='__main__':
    sys.exit(main())
