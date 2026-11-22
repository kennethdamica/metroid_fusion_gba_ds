#!/usr/bin/env python3
"""Exercise the actual frozen executable outside the checkout with no Python PATH."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
from package_fusion import ROOT, build, read_bios


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--executable', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args=p.parse_args()
    executable=args.executable.resolve()
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    checks=[]
    def check(name, passed):
        checks.append(dict(name=name,passed=bool(passed)))
        print(('PASS ' if passed else 'FAIL ')+name,flush=True)
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    # Only the executable and explicitly supplied user files enter this tree.
    with tempfile.TemporaryDirectory(prefix='Fusion CLI isolated 日本語 ') as tmp:
        folder=Path(tmp); cli=folder/executable.name;shutil.copy2(executable,cli)
        rom=folder/'My Fusion ROM.gba';shutil.copy2(ROOT/'Metroid Fusion (USA).gba',rom)
        bios=folder/'My BIOS.zip';shutil.copy2(ROOT/'gba_bios.zip',bios)
        plain=folder/'bios.bin';plain.write_bytes(read_bios(bios))
        before={path.name:sha(path) for path in (rom,bios,plain)}
        env={k:v for k,v in os.environ.items() if not k.startswith(('PYTHON','PYINSTALLER','_PYI'))}
        env['PATH']='';env['PYTHONNOUSERSITE']='1'
        def run(*words):
            result=subprocess.run([str(cli),*map(str,words)],cwd=folder,env=env,
                                  text=True,capture_output=True,timeout=60)
            check('no_traceback_'+str(len(checks)), 'Traceback' not in result.stderr)
            return result
        check('version_without_Python_PATH', run('--version').stdout.strip()=='fusion-pack 0.1.0')
        check('help', 'Create a dual-screen Fusion NDS' in run('--help').stdout)
        check('missing_arguments_exit_2', run().returncode==2)
        listing=run('--list-games','--json')
        check('supported_revision_list', listing.returncode==0 and len(json.loads(listing.stdout))==1)
        destination=folder/'My output — DS 日本語'/'Fusion.nds'
        made=run(rom,'--bios',bios,'-o',destination,'--json')
        check('standalone_generates_NDS',made.returncode==0 and destination.is_file())
        if made.returncode:
            raise RuntimeError(made.stderr)
        check('only_NDS_by_default',sorted(x.name for x in destination.parent.iterdir())==['Fusion.nds'])
        expected=output/'reference.nds'
        build(ROOT/'artifacts/hardware-runtime',rom,bios,expected,write_manifest=False)
        check('exact_match_with_reference_builder',destination.read_bytes()==expected.read_bytes())
        lock=json.loads((ROOT/'release/packager/runtime-lock.json').read_text())
        check('matches_gameplay_validated_release',sha(destination)==lock['reference_package_sha256'])
        check('reports_user_destination',json.loads(made.stdout)['output']==str(destination))
        check('DS_paths_use_forward_slashes',all('\\' not in json.loads(made.stdout)[key]
              for key in ('data_directory','save_path')))
        original=sha(destination)
        check('existing_NDS_refused',run(rom,'--bios',bios,'-o',destination).returncode==1)
        check('existing_NDS_preserved',sha(destination)==original)
        verified=run('--inspect',destination,'--json')
        check('inspect_matches_generated_hash',verified.returncode==0 and json.loads(verified.stdout)['package_sha256']==original)
        human=run('--inspect',destination)
        check('Unicode_path_in_human_output',human.returncode==0 and 'Verified:' in human.stdout)
        with_report=run(rom,'--bios',plain,'--manifest')
        check('default_name_and_raw_BIOS',with_report.returncode==0 and (folder/'Fusion.nds').read_bytes()==expected.read_bytes())
        check('optional_manifest',(folder/'Fusion.manifest.json').is_file())
        wrong=folder/'wrong.gba';wrong.write_bytes(b'not a supported game')
        bad=folder/'bad.nds'
        check('unsupported_ROM_rejected',run(wrong,'--bios',bios,'-o',bad).returncode==1 and not bad.exists())
        bad_bios=folder/'bad.bin';bad_bios.write_bytes(b'\0'*16384)
        check('wrong_BIOS_rejected',run(rom,'--bios',bad_bios,'-o',bad).returncode==1 and not bad.exists())
        check('missing_BIOS_rejected',run(rom,'--bios',folder/'absent.bin','-o',bad).returncode==1 and not bad.exists())
        bad_zip=folder/'bad.zip';bad_zip.write_bytes(b'PK\x03\x04broken')
        check('invalid_ZIP_rejected',run(rom,'--bios',bad_zip,'-o',bad).returncode==1 and not bad.exists())
        check('bad_output_extension_rejected',run(rom,'--bios',bios,'-o',folder/'wrong.gba').returncode==2)
        check('conflicting_modes_rejected',run(rom,'--inspect',destination).returncode==2)
        corrupt=folder/'corrupt.nds';data=bytearray(destination.read_bytes());data[-1024]^=1;corrupt.write_bytes(data)
        check('corrupt_package_rejected',run('--inspect',corrupt).returncode==1)
        blocker=folder/'not-a-directory';blocker.write_text('keep me')
        check('unwritable_destination_explained',run(rom,'--bios',bios,'-o',blocker/'Fusion.nds').returncode==1)
        check('input_files_preserved',all(sha(path)==before[path.name] for path in (rom,bios,plain)))
        check('no_temporary_output_files',not list(folder.rglob('*.tmp')))
        shutil.copy2(destination,output/'Fusion.nds')
        (output/'generated-report.json').write_text(made.stdout)
    # Inspect the frozen data, rather than relying solely on the distribution size.
    from PyInstaller.archive.readers import CArchiveReader
    archive=CArchiveReader(str(executable))
    members=list(archive.toc)
    normalized={name.replace('\\','/'):name for name in members}
    runtime=[name for name in normalized if name.startswith('runtime/')]
    check('bundled_runtime_allowlist',sorted(runtime)==['runtime/manifest.json','runtime/sdcard/FusionTemplate.nds'])
    check('bundled_template_matches',archive.extract(normalized['runtime/sdcard/FusionTemplate.nds']) ==
          (ROOT/'artifacts/hardware-runtime/sdcard/FusionTemplate.nds').read_bytes())
    check('no_game_or_BIOS_members',not any(name.lower().endswith(('.gba','bios.bin','bios.zip')) for name in members))
    # Inspect every outer payload for exact supplied game/BIOS content hashes.
    prohibited={hashlib.sha256((ROOT/'Metroid Fusion (USA).gba').read_bytes()).hexdigest(),
                hashlib.sha256(read_bios(ROOT/'gba_bios.zip')).hexdigest()}
    check('no_proprietary_payload_bytes',not any(hashlib.sha256(archive.extract(name)).hexdigest() in prohibited
          for name in members if archive.toc[name][-1]!='o'))
    status='passed' if all(c['passed'] for c in checks) else 'failed'
    (output/'result.json').write_text(json.dumps(dict(status=status,executable_sha256=sha(executable),
        test_environment=os.environ.get('FUSION_BUILD_ENV',platform.platform()),
        test_script_sha256=sha(Path(__file__)),
        generated_NDS_sha256=sha(output/'Fusion.nds'),checks=checks,frozen_members=members),indent=2)+'\n')
    return status!='passed'


if __name__=='__main__':
    sys.exit(main())
