#!/usr/bin/env python3
"""Smoke-test the frozen CLI and audit its payload allowlist without game data."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from fusion_pack import VERSION, PROFILES
from release_checks import validated_runtimes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    checks = []

    def check(name, passed):
        checks.append(dict(name=name, passed=bool(passed)))
        print(('PASS ' if passed else 'FAIL ') + name, flush=True)

    with tempfile.TemporaryDirectory(prefix='GBA DS standalone 日本語 ') as temporary:
        folder = Path(temporary)
        executable = folder / args.executable.name
        shutil.copy2(args.executable, executable)
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(('PYTHON', 'PYINSTALLER', '_PYI'))}
        env['PATH'] = ''
        env['PYTHONNOUSERSITE'] = '1'

        def run(*words):
            result = subprocess.run([str(executable), *map(str, words)], cwd=folder,
                                    env=env, capture_output=True, text=True, timeout=60)
            check('no_traceback_' + str(len(checks)), 'Traceback' not in result.stderr)
            return result

        result = run('--version')
        check('version', result.returncode == 0 and result.stdout.strip() == f'gba-ds-pack {VERSION}')
        result = run('--help')
        check('help', result.returncode == 0 and '--allow-unsupported-rom' in result.stdout)
        result = run('--list-games', '--json')
        check('both_profiles', result.returncode == 0 and
              {g['game']: g['sha1'] for g in json.loads(result.stdout)} ==
              {p.key: p.rom_sha1 for p in PROFILES.values()})
        check('missing_arguments', run().returncode == 2)
        check('conflicting_modes', run('--list-games', '--inspect', 'missing.nds').returncode == 2)
        check('override_requires_game', run('missing.gba', '--bios', 'missing.bin',
                                           '--allow-unsupported-rom').returncode == 2)
        rom = folder/'invalid.gba'
        rom.write_bytes(b'Original malformed-input fixture, not a ROM.')
        destination = folder/'output.nds'
        result = run(rom, '--bios', 'missing.bin', '-o', destination, '--json')
        check('malformed_input_rejected', result.returncode == 1 and
              'error' in json.loads(result.stderr) and not destination.exists())
        result = run('--inspect', rom, '--json')
        check('invalid_inspection', result.returncode == 1 and 'error' in json.loads(result.stderr))
        check('input_unchanged', rom.read_bytes() == b'Original malformed-input fixture, not a ROM.')
        check('no_outputs_created', sorted(p.name for p in folder.iterdir()) ==
              sorted((executable.name, rom.name)))

    from PyInstaller.archive.readers import CArchiveReader
    archive = CArchiveReader(str(args.executable))
    normalized = {name.replace('\\', '/'): name for name in archive.toc}
    expected, _, _ = validated_runtimes()
    data_members = {name for name in normalized if name.startswith('runtime/') or
                    name == 'rom_compatibility.json'}
    check('exact_runtime_allowlist', data_members == set(expected))
    for name, path in expected.items():
        check('bundled_' + name, name in normalized and
              archive.extract(normalized[name]) == path.read_bytes())
    check('no_game_or_BIOS_members', not any(name.lower().endswith(('.gba', 'bios.bin', 'bios.zip'))
                                           for name in normalized))
    passed = all(c['passed'] for c in checks)
    report = dict(status='passed' if passed else 'failed', checks=checks,
                  executable_sha256=hashlib.sha256(args.executable.read_bytes()).hexdigest(),
                  scope='ROM-free native CLI smoke test and runtime payload audit; not gameplay acceptance')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as output:
        output.write(json.dumps(report, indent=2)+'\n')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
