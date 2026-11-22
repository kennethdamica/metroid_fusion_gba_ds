#!/usr/bin/env python3
"""Developer helper: freeze Windows x64 CLI on a Mac/Linux host using Wine.

Docker/Python/Wine are build dependencies only, never end-user dependencies.
Downloads are checksum-locked. No game inputs enter the Docker build context.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'fusion-pack-windows-builder:0.1.0'


def run(command):
    subprocess.run(list(map(str, command)), cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'artifacts/packager')
    parser.add_argument('--test-output', type=Path,
                        help='also run the isolated executable tests (requires local ROM/BIOS)')
    args = parser.parse_args()
    # Containers use a fixed mount; refuse paths we cannot map into it.
    output = args.output.resolve().relative_to(ROOT)
    test_output = args.test_output.resolve().relative_to(ROOT) if args.test_output else None
    if (ROOT/output/'windows-x86_64').exists():
        parser.error('Windows output exists; choose a new --output directory')
    if test_output and (ROOT/test_output).exists():
        parser.error('Test output exists; choose a new --test-output directory')
    lock = json.loads((ROOT/'release/packager/windows-downloads.json').read_text())
    cache = ROOT/'.tools/windows-packager/downloads'
    cache.mkdir(parents=True, exist_ok=True)
    python = cache/lock['python']['filename']
    if not python.exists():
        temporary = python.with_suffix('.download')
        run(['curl', '--fail', '--location', '--retry', '2', '--output', temporary, lock['python']['url']])
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != lock['python']['sha256']:
            raise ValueError('Windows Python download checksum mismatch')
        temporary.rename(python)
    wheels = cache/'wheels'
    wheels.mkdir(exist_ok=True)
    missing = [item['requirement'] for item in lock['wheels'] if not (wheels/item['filename']).exists()]
    if missing:
        run([sys.executable, '-m', 'pip', 'download', '--only-binary=:all:', '--no-deps',
             '--platform', 'win_amd64', '--python-version', '313', '--implementation', 'cp',
             '--abi', 'cp313', '--dest', wheels, *missing])
    for base, item in [(cache, lock['python']), *[(wheels, item) for item in lock['wheels']]]:
        if hashlib.sha256((base/item['filename']).read_bytes()).hexdigest() != item['sha256']:
            raise ValueError(f'Download checksum mismatch: {item["filename"]}')
    # A fresh allowlisted context prevents cached/unrelated inputs entering an image.
    import tempfile
    import shutil
    with tempfile.TemporaryDirectory(prefix='fusion-windows-build-') as tmp:
        context = Path(tmp)
        shutil.copy2(python, context/python.name)
        (context/'wheels').mkdir()
        for item in lock['wheels']:
            shutil.copy2(wheels/item['filename'], context/'wheels'/item['filename'])
        run(['docker', 'build', '--platform', 'linux/amd64', '-f',
             ROOT/'release/packager/windows.Dockerfile', '-t', IMAGE, context])
    docker = ['docker', 'run', '--rm', '--platform', 'linux/amd64', '--network', 'none',
              '--mount', f'type=bind,source={ROOT},target=/project',
              '-e', 'FUSION_BUILD_ENV=Windows CPython 3.13.7 under Wine 10 on Debian trixie amd64',
              IMAGE, '/usr/lib/wine/wine64', '/python/tools/python.exe']
    run([*docker, 'Z:/project/tools/build_packager.py', '--output', 'Z:/project/'+output.as_posix()])
    if test_output:
        run([*docker, 'Z:/project/tools/test_packager_cli.py', '--executable',
             'Z:/project/'+output.as_posix()+'/windows-x86_64/fusion-pack.exe',
             '--output', 'Z:/project/'+test_output.as_posix()])


if __name__ == '__main__':
    main()
