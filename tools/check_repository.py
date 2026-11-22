#!/usr/bin/env python3
"""Check public source contents and local documentation links without game data."""
import argparse
import ast
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOTS = {'vendor', '.tools', '.venv', 'artifacts', '.codex', '.agents'}
BINARY_SUFFIXES = {
    '.gba', '.nds', '.bin', '.rom', '.sav', '.srm', '.dsv', '.state', '.dump',
    '.ram', '.img', '.iso', '.zip', '.7z', '.tar', '.gz', '.exe', '.dll', '.dylib',
    '.elf', '.o', '.map', '.log', '.pyc', '.pyo', '.pem', '.key',
}


def source_files(root=ROOT):
    """Include tracked files even if ignored; also check untracked candidates.

    Before git init, use temporary Git metadata so Git itself interprets the
    ignore rules. This never initializes or stages the user's working folder.
    """
    probe = subprocess.run(['git', '-C', str(root), 'rev-parse', '--show-toplevel'],
                           capture_output=True, text=True)
    with tempfile.TemporaryDirectory(prefix='fusion-source-check-') as temporary:
        if probe.returncode == 0 and Path(probe.stdout.strip()).resolve() == root.resolve():
            command = ['git', '-C', str(root)]
        else:
            metadata = Path(temporary)/'index.git'
            subprocess.run(['git', 'init', '--bare', '--quiet', str(metadata)], check=True)
            command = ['git', '--git-dir='+str(metadata), '--work-tree='+str(root)]
        output = subprocess.check_output(command + [
            'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root)
    return sorted(set(output.decode('utf-8').rstrip('\0').split('\0')) - {''})


def check(root, names):
    errors = []
    public = set(names)
    for name in names:
        relative = Path(name)
        path = root/relative
        if (relative.parts[0] in PRIVATE_ROOTS or name.startswith('fixtures/local/')
                or 'build' in relative.parts or '__pycache__' in relative.parts
                or relative.suffix.lower() in BINARY_SUFFIXES
                or relative.name.startswith('.env') or relative.name == '.DS_Store'):
            errors.append(f'{name}: private/generated file in source candidates')
            continue
        if path.is_symlink() or not path.is_file():
            errors.append(f'{name}: expected a regular source file')
            continue
        if path.stat().st_size > 2*1024*1024:
            errors.append(f'{name}: unexpectedly large source file; review before publishing')
            continue
        try:
            content = path.read_text(encoding='utf-8')
            if '\0' in content:
                raise ValueError('binary content')
            if re.search(r'/(?:Users|home)/[A-Za-z0-9_][^/\s]*/', content):
                errors.append(f'{name}: personal home-directory path')
            if path.suffix == '.py':
                ast.parse(content, filename=name)
            elif path.suffix == '.json':
                json.loads(content)
            elif path.suffix == '.md':
                # Inline Markdown links only; remote URLs/anchors are not fetched.
                for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', content):
                    link = urlsplit(target)
                    if link.scheme or link.netloc or not link.path:
                        continue
                    destination = (path.parent/unquote(link.path)).resolve()
                    if not destination.is_relative_to(root.resolve()):
                        errors.append(f'{name}: link escapes repository: {target}')
                        continue
                    key = destination.relative_to(root.resolve()).as_posix()
                    if key not in public and not any(n.startswith(key+'/') for n in names):
                        errors.append(f'{name}: link absent from public source: {target}')
        except (UnicodeError, ValueError, SyntaxError) as error:
            errors.append(f'{name}: {error}')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true', help='print candidate paths after validation')
    args = parser.parse_args()
    names = source_files()
    errors = check(ROOT, names)
    if errors:
        print('\n'.join(errors))
        return 1
    if args.list:
        print('\n'.join(names))
    else:
        print(f'PASS: {len(names)} source files; contents, syntax and local Markdown links checked.')
        print('Game/runtime tests and Git history/secret review are separate checks.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
