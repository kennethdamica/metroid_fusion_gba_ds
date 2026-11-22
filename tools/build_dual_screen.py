#!/usr/bin/env python3
"""Build the Fusion screen prototype in a separate copy of the pinned runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from build_baseline import ROOT, REVISION, LIBTWL, IMAGE, output


def copy_changed(source, target):
    if not target.exists() or source.read_bytes() != target.read_bytes():
        shutil.copyfile(source, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clean', action='store_true')
    parser.add_argument('--package-template', action='store_true', help='Build the bootstrap extractor and explicit path handoff')
    parser.add_argument('--hardware-diagnostics', action='store_true', help='Build a separate packaged runtime with visible startup stages')
    args = parser.parse_args()
    if args.hardware_diagnostics:
        args.package_template = True
    original = ROOT / 'vendor/GBARunner3'
    source = ROOT / ('.tools/gbarunner3-package' if args.package_template else '.tools/gbarunner3-dual')
    dest = ROOT / ('artifacts/package-runtime' if args.package_template else 'artifacts/dual-screen')
    if args.hardware_diagnostics:
        source = ROOT / '.tools/gbarunner3-hardware'
        dest = ROOT / 'artifacts/hardware-runtime'
    for repo, revision in ((original, REVISION), (original / 'code/libs/libtwl', LIBTWL)):
        if output('git', '-C', str(repo), 'rev-parse', 'HEAD') != revision or output('git', '-C', str(repo), 'diff', 'HEAD', '--'):
            raise RuntimeError(f'Expected clean pinned source: {repo}')
    if args.clean and source.exists():
        shutil.rmtree(source)
    # Copy tracked source only. The independent build never touches the baseline.
    for repo, relative in ((original, Path('.')), (original / 'code/libs/libtwl', Path('code/libs/libtwl'))):
        paths = subprocess.check_output(['git', '-C', str(repo), 'ls-files', '-z']).decode().split('\0')
        for name in filter(None, paths):
            path = repo / name
            if path.is_file():
                target = source / relative / name
                target.parent.mkdir(parents=True, exist_ok=True)
                copy_changed(path, target)
    patch = ROOT / 'patches/gbarunner3-dual-screen.patch'
    subprocess.run(['git', 'apply', '--unsafe-paths', str(patch)], cwd=source, check=True)
    overlay = ROOT / 'runtime/dual_screen'
    for old in (source / 'code/core/arm9/source/Application').glob('FusionScreen*.cpp'):
        if not (overlay / old.name).exists():
            old.unlink()
    for path in overlay.glob('*'):
        if path.suffix in ('.cpp', '.h'):
            copy_changed(path, source / 'code/core/arm9/source/Application' / path.name)
    inputs = [patch, *sorted(overlay.glob('*.h')), *sorted(overlay.glob('*.cpp'))]
    if args.package_template:
        package_patch = ROOT / 'patches/gbarunner3-package.patch'
        subprocess.run(['git', 'apply', str(package_patch)], cwd=source, check=True)
        package_sources = sorted((ROOT / 'runtime/package').glob('*'))
        inputs += [package_patch, *package_sources]
        bootstrap = source / 'code/bootstrap/arm9/source'
        for path in package_sources:
            copy_changed(path, bootstrap / path.name)
        for name in ('ff.c', 'ff.h', 'ffconf.h', 'ffunicode.c', 'ffsystem.c', 'diskio.h'):
            copy_changed(original / 'code/core/arm9/source/Fat' / name, bootstrap / name)
    if args.hardware_diagnostics:
        diagnostic_patch = ROOT / 'patches/gbarunner3-hardware-diagnostics.patch'
        subprocess.run(['git', 'apply', str(diagnostic_patch)], cwd=source, check=True)
        trace = ROOT / 'runtime/hardware/BootTrace.inc'
        screen = source / 'code/core/arm9/source/Application/FusionScreen.size.cpp'
        with screen.open('a') as stream:
            stream.write('\n' + trace.read_text())
        inputs += [diagnostic_patch, trace]
    dest.mkdir(parents=True, exist_ok=True)
    command = ['docker', 'run', '--rm', '--platform', 'linux/amd64', '--network', 'none',
               '--mount', f'type=bind,source={source},target=/src', '--workdir', '/src', IMAGE,
               'make', '-C', 'code']
    with (dest / 'build.log').open('w') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        print((dest / 'build.log').read_text()[-6000:], file=sys.stderr)
        return result.returncode
    package = dest / 'sdcard'
    (package / '_gba').mkdir(parents=True, exist_ok=True)
    binary = package / ('FusionTemplate.nds' if args.package_template else 'FusionDual.nds')
    shutil.copy2(source / 'code/bootstrap/GBARunner3.nds', binary)
    shutil.copytree(original / 'configs', package / '_gba/configs', dirs_exist_ok=True)
    debug = dest / 'debug'
    debug.mkdir(exist_ok=True)
    for path in source.glob('code/**/*.elf'):
        shutil.copy2(path, debug / str(path.relative_to(source)).replace('/', '_'))
    for path in source.glob('code/**/*.map'):
        shutil.copy2(path, debug / str(path.relative_to(source)).replace('/', '_'))
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = dict(gbarunner3_commit=REVISION, libtwl_commit=LIBTWL, image=IMAGE,
                    source_modified=True, rom_sha256=sha(binary), rom_bytes=binary.stat().st_size,
                    package_abi=1 if args.package_template else None,
                    hardware_diagnostics=args.hardware_diagnostics,
                    inputs={str(p.relative_to(ROOT)): sha(p) for p in inputs})
    (dest / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
