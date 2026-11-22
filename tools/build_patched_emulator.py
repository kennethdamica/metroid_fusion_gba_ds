#!/usr/bin/env python3
"""Build the pinned interpreter core with ARM9 abort and L4 interworking corrections."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run(*command, **kwargs):
    return subprocess.run(command, check=True, **kwargs)


def output(*command):
    return subprocess.check_output(command, text=True).strip()


def apply_exact_patch(source, patch):
    current = subprocess.check_output(['git', '-C', str(source), 'diff', 'HEAD', '--'])
    expected = patch.read_bytes()
    if current == expected:
        return
    if current:
        raise RuntimeError(f'Unexpected source edits in {source}; preserving them')
    run('git', '-C', str(source), 'apply', '--check', str(patch))
    run('git', '-C', str(source), 'apply', str(patch))
    if subprocess.check_output(['git', '-C', str(source), 'diff', 'HEAD', '--']) != expected:
        raise RuntimeError('Applied patch differs from the recorded patch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', type=int, default=8)
    args = parser.parse_args()
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        parser.error('This tested configuration targets Apple Silicon macOS')
    lock = json.loads((ROOT / 'tools/melonds-lock.json').read_text())
    source = ROOT / '.tools/melonds-ds-source'
    build = ROOT / '.tools/melonds-debug-build'
    report = ROOT / 'artifacts/melonds-patched'
    report.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        run('git', 'clone', 'https://github.com/JesseTG/melonds-ds.git', str(source))
        run('git', '-C', str(source), 'checkout', '--detach', lock['frontend_commit'])
    if output('git', '-C', str(source), 'rev-parse', 'HEAD') != lock['frontend_commit']:
        raise RuntimeError('Unexpected frontend revision')
    frontend_patch = ROOT / 'patches/melonds-ds-shared-wram.patch'
    cpu_patch = ROOT / 'patches/melonds-arm9-data-abort.patch'
    apply_exact_patch(source, frontend_patch)
    configure = ['cmake', '-S', str(source), '-B', str(build),
                 '-DCMAKE_BUILD_TYPE=RelWithDebInfo', '-DENABLE_OPENGL=OFF',
                 '-DENABLE_JIT=OFF', '-DBUILD_TESTING=OFF']
    for name, revision in lock['dependencies'].items():
        variable = name.upper().replace('-', '_')
        configure.append(f'-D{variable}_REPOSITORY_TAG={revision}')
    with (report / 'configure.log').open('w') as log:
        run(*configure, stdout=log, stderr=subprocess.STDOUT)
    for name, revision in lock['dependencies'].items():
        dependency = build / '_deps' / f'{name}-src'
        if output('git', '-C', str(dependency), 'rev-parse', 'HEAD') != revision:
            raise RuntimeError(f'Unexpected dependency revision: {name}')
    apply_exact_patch(build / '_deps/melonds-src', cpu_patch)
    with (report / 'build.log').open('w') as log:
        run('cmake', '--build', str(build), '-j', str(args.jobs), stdout=log, stderr=subprocess.STDOUT)
    core = ROOT / '.tools/melonds-custom/fixed/melondsds_libretro.dylib'
    core.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(build / 'src/libretro/melondsds_libretro.dylib', core)
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = dict(lock, core=str(core), core_sha256=digest(core), jit=False,
                    compiler=output('clang', '--version'), cmake=output('cmake', '--version'),
                    patch_sha256={p.name: digest(p) for p in (cpu_patch, frontend_patch)})
    (report / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Built patched interpreter: {core}')


if __name__ == '__main__':
    main()
