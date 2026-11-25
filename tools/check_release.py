#!/usr/bin/env python3
"""Validate runtime locks, version tags and the exact public release asset set."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile
from fusion_pack import VERSION
from package_fusion import ROOT
from release_checks import validated_runtimes
from check_repository import BINARY_SUFFIXES

PLATFORMS = ('macos-arm64', 'windows-x86_64')


def check_tag(tag):
    if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+', tag) or tag != 'v' + VERSION:
        raise ValueError(f'Release tag must match the CLI version: v{VERSION}')


def check_archives(directory, *, expected_commit=None):
    lock = json.loads((ROOT/'release/packager/runtime-lock.json').read_text())
    expected_names = {f'gba-ds-pack-{VERSION}-{p}-preview.zip' for p in PLATFORMS}
    names = {p.name for p in directory.iterdir()}
    if names != expected_names:
        raise ValueError('Release directory must contain exactly the two platform ZIPs')
    checksums = []
    for platform in PLATFORMS:
        name = f'gba-ds-pack-{VERSION}-{platform}-preview.zip'
        path = directory/name
        executable = 'gba-ds-pack.exe' if platform.startswith('windows') else 'gba-ds-pack'
        required = {'gba-ds-pack/'+n for n in (executable, 'README.txt', 'THIRD_PARTY_NOTICES.txt', 'build.json')}
        with zipfile.ZipFile(path) as archive:
            members = archive.namelist()
            if len(members) != len(set(members)) or not required.issubset(members):
                raise ValueError('Duplicate or missing release archive members')
            for member in members:
                parts = PurePosixPath(member).parts
                license_file = (len(parts) == 3 and parts[:2] == ('gba-ds-pack', 'licenses') and
                                parts[2] not in ('.', '..') and '\\' not in member and
                                PurePosixPath(member).suffix.lower() not in BINARY_SUFFIXES)
                if member not in required and not license_file:
                    raise ValueError('Unexpected release archive member: ' + member)
                if archive.getinfo(member).file_size > 64*1024*1024:
                    raise ValueError('Unexpectedly large release member')
                if member != 'gba-ds-pack/'+executable:
                    content = archive.read(member).decode('utf-8')
                    if '\0' in content:
                        raise ValueError('Binary data in a release text member')
            if 'gba-ds-pack/licenses/Python-LICENSE.txt' not in members:
                raise ValueError('Python license missing from release archive')
            for notice in (ROOT/'licenses').glob('*.txt'):
                if archive.read('gba-ds-pack/licenses/'+notice.name) != notice.read_bytes():
                    raise ValueError('Missing or changed third-party notice: ' + notice.name)
            report = json.loads(archive.read('gba-ds-pack/build.json'))
            binary = archive.read('gba-ds-pack/'+executable)
            if (report['version'] != VERSION or report['platform'] != platform or
                    report['executable_sha256'] != hashlib.sha256(binary).hexdigest() or
                    report['executable_bytes'] != len(binary) or report['runtime_lock'] != lock):
                raise ValueError('Release build provenance mismatch')
            if expected_commit and (report.get('git_commit') != expected_commit or report.get('git_dirty') is not False):
                raise ValueError('Release executable was built from another commit')
            for key, runtime in report['runtimes'].items():
                if runtime['rom_sha256'] != lock['games'][key]['template_sha256']:
                    raise ValueError('Unvalidated runtime in release')
            if set(report['runtimes']) != set(lock['games']):
                raise ValueError('Missing game runtime')
        checksums.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+name)
    return '\n'.join(checksums)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('runtimes', 'tag', 'assets'))
    parser.add_argument('value', nargs='?')
    parser.add_argument('--commit', help='require this build commit when checking release ZIPs')
    args = parser.parse_args()
    try:
        if args.mode == 'runtimes':
            data, _, _ = validated_runtimes()
            print(f'PASS: {len(data)} allowlisted runtime/compatibility files match the source and release locks')
        elif args.mode == 'tag':
            check_tag(args.value or '')
            print('PASS: tag matches CLI version')
        else:
            if not args.value:
                parser.error('assets requires a directory')
            directory = Path(args.value)
            checksums = check_archives(directory, expected_commit=args.commit)
            (directory/'SHA256SUMS').write_text(checksums, encoding='utf-8')
            print(checksums, end='')
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        parser.exit(1, str(error)+'\n')


if __name__ == '__main__':
    main()
