#!/usr/bin/env python3
"""Freeze a ROM-free standalone CLI using an explicit per-game runtime allowlist."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile
from package_fusion import ROOT
from fusion_pack import VERSION
from release_checks import validated_runtimes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'artifacts/packager')
    args = parser.parse_args()
    if importlib.metadata.version('pyinstaller') != '6.22.3':
        parser.error('Install requirements-packager.txt in the build environment')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    bundled, runtimes, runtime_lock = validated_runtimes()
    system = {'Darwin':'macos', 'Windows':'windows', 'Linux':'linux'}[platform.system()]
    machine = platform.machine().lower()
    architecture = {'amd64':'x86_64', 'aarch64':'arm64'}.get(machine, machine)
    label = f'{system}-{architecture}'
    output = args.output.resolve()/label
    if output.exists():
        parser.error(f'Choose a new output directory; preserving {output}')
    work = ROOT/'.tools/packager-build'/label
    work.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True)
    # Never collect artifacts/, fixtures/, the user's ROM/BIOS, or a generated NDS.
    command = [sys.executable, '-m', 'PyInstaller', '--onefile', '--noupx',
               '--name', 'gba-ds-pack', '--distpath', str(output), '--workpath', str(work/'work'),
               '--specpath', str(work), '--paths', str(ROOT/'tools')]
    for destination, source in bundled.items():
        command += ['--add-data', f'{source.resolve()}:{Path(destination).parent.as_posix()}']
    command.append(str(ROOT/'tools/gba_ds_pack.py'))
    env = os.environ.copy()
    env['PYINSTALLER_CONFIG_DIR'] = str(work/'cache')
    with (output/'build.log').open('w') as log:
        subprocess.run(command, env=env, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    executable = output/('gba-ds-pack.exe' if system == 'windows' else 'gba-ds-pack')
    readme = 'README-windows.txt' if system == 'windows' else 'README.txt'
    shutil.copy2(ROOT/'release/packager'/readme, output/'README.txt')
    shutil.copy2(ROOT/'release/packager/THIRD_PARTY_NOTICES.txt', output/'THIRD_PARTY_NOTICES.txt')
    licenses = output/'licenses'; licenses.mkdir()
    # Reviewed third-party notices accompany the archive, not the runtime data.
    notice_files = sorted((ROOT/'licenses').glob('*.txt'))
    for notice in notice_files:
        shutil.copyfile(notice, licenses/notice.name)
    for package in ('pyinstaller', 'pyinstaller-hooks-contrib', 'altgraph', 'macholib', 'packaging', 'setuptools',
                    'pefile', 'pywin32-ctypes'):
        try:
            distribution = importlib.metadata.distribution(package)
        except importlib.metadata.PackageNotFoundError:
            continue
        for path in distribution.files or []:
            if any(word in path.name.lower() for word in ('license', 'copying')):
                source = distribution.locate_file(path)
                if source.is_file():
                    shutil.copyfile(source, licenses/(package+'-'+path.name))
    import sysconfig
    for python_license in (Path(sysconfig.get_path('stdlib'))/'LICENSE.txt', Path(sys.base_prefix)/'LICENSE.txt'):
        if python_license.exists():
            shutil.copyfile(python_license, licenses/'Python-LICENSE.txt')
            break
    report = dict(version=VERSION, platform=label, python=platform.python_version(),
                  pyinstaller=importlib.metadata.version('pyinstaller'),
                  build_environment=os.environ.get('FUSION_BUILD_ENV', platform.platform()),
                  git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  git_dirty=bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
                  github_run_url=(f'https://github.com/{os.environ["GITHUB_REPOSITORY"]}/actions/runs/'
                                  f'{os.environ["GITHUB_RUN_ID"]}' if os.environ.get('GITHUB_RUN_ID') else None),
                  executable_sha256=sha(executable), executable_bytes=executable.stat().st_size,
                  third_party_notice_hashes={p.name:sha(p) for p in notice_files},
                  bundled_data={name:sha(path) for name,path in bundled.items()},
                  runtimes=runtimes, runtime_lock=runtime_lock, public_release_ready=False,
                  remaining_release_work=['Resolve GBARunner3/libtwl redistribution permission and remaining dependency notices',
                                          'Choose project license',
                                          'Windows game-package acceptance with user-supplied inputs and Authenticode signing' if system == 'windows'
                                          else 'Developer ID signing and notarization for macOS'],
                  source_hashes={name:sha(ROOT/name) for name in
                      ('tools/gba_ds_pack.py','tools/fusion_pack.py','tools/rom_compatibility.py','tools/rom_compatibility.json','tools/package_fusion.py','tools/fusion_profile.py','tools/nds_banner.py','tools/game_profiles.py','tools/build_packager.py','tools/release_checks.py',
                       'requirements-packager.txt','release/packager/runtime-lock.json',
                       'release/packager/'+readme)})
    if system == 'windows':
        report['source_hashes'].update({name:sha(ROOT/name) for name in
            ('tools/build_windows_packager.py', 'release/packager/windows.Dockerfile',
             'release/packager/windows-downloads.json')})
    (output/'build.json').write_text(json.dumps(report, indent=2)+'\n')
    archive = args.output.resolve()/f'gba-ds-pack-{VERSION}-{label}-preview.zip'
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as package:
        for path in sorted(output.rglob('*')):
            if path.is_file() and path.name != 'build.log':
                package.write(path, Path('gba-ds-pack')/path.relative_to(output))
    print(json.dumps(dict(executable=str(executable), archive=str(archive),
                         archive_sha256=sha(archive), **report), indent=2))


if __name__ == '__main__':
    main()
