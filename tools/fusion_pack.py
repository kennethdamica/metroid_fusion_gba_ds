#!/usr/bin/env python3
"""End-user command-line interface for the standalone GBA DS packager."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile
from game_profiles import FUSION, ALTTP
from package_fusion import DEFAULT_RUNTIME, build, inspect_package

VERSION = '0.2.0'
PROFILES = {p.key: p for p in (FUSION, ALTTP)}


def runtime_directory(profile=FUSION):
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / 'runtime' / profile.key
    return DEFAULT_RUNTIME if profile == FUSION else DEFAULT_RUNTIME.parent / 'alttp-package-runtime'


def main(argv=None):
    # A redirected Windows console may use a legacy code page. File access
    # remains Unicode; printing a path must not turn a successful build into
    # an encoding failure. JSON already escapes non-ASCII characters.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(errors='backslashreplace')
    parser = argparse.ArgumentParser(
        prog='gba-ds-pack', description='Create a DS package for Metroid Fusion or Zelda ALttP from your ROM and GBA BIOS.',
        epilog='Example: gba-ds-pack "Metroid Fusion (USA).gba" --bios bios.bin -o Fusion.nds\n'
               'Works offline. No ROM or BIOS is included. Existing files are never overwritten.',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('rom', nargs='?', type=Path, help='supported US .gba file (game detected by SHA-1)')
    parser.add_argument('--bios', type=Path, help='your GBA BIOS (.bin or ZIP containing one 16 KiB BIOS)')
    parser.add_argument('-o', '--output', type=Path, help='destination .nds (default: Fusion.nds or Zelda.nds in the current folder)')
    parser.add_argument('--game', choices=tuple(PROFILES), help='choose the adapter; required for experimental ROMs')
    parser.add_argument('--allow-unsupported-rom', action='store_true', help='allow an unverified ROM variant after compatibility checks (requires --game)')
    parser.add_argument('--manifest', action='store_true', help='also save a companion build report (.manifest.json)')
    parser.add_argument('--json', action='store_true', help='print machine-readable results')
    parser.add_argument('--inspect', type=Path, metavar='NDS', help='verify an existing package without changing it')
    parser.add_argument('--list-games', action='store_true', help='show supported games and revisions')
    parser.add_argument('--version', action='version', version=f'gba-ds-pack {VERSION}')
    args = parser.parse_args(argv)
    if args.inspect or args.list_games:
        if args.rom or args.bios or args.output or args.manifest or args.game or args.allow_unsupported_rom or (args.inspect and args.list_games):
            parser.error('Use --inspect or --list-games on its own (optionally with --json)')
    elif not args.rom or not args.bios:
        parser.error('Supply a ROM and --bios. Run gba-ds-pack --help for an example.')
    if args.allow_unsupported_rom and not args.game:
        parser.error('--allow-unsupported-rom requires --game fusion or --game alttp')
    try:
        if args.list_games:
            games = [dict(game=p.key, name=p.title, sha1=p.rom_sha1) for p in PROFILES.values()]
            print(json.dumps(games, indent=2) if args.json else '\n'.join(f"{g['game']}: {g['name']}\nSHA-1: {g['sha1']}" for g in games))
            return 0
        if args.inspect:
            report = inspect_package(args.inspect.expanduser(), profile=None)
            verb, output = 'Verified', args.inspect.absolute()
        else:
            rom = args.rom.expanduser()
            if not rom.is_file() or rom.stat().st_size != 8 * 1024 * 1024:
                raise ValueError('ROM must be an 8 MiB .gba file')
            actual = hashlib.sha1(rom.read_bytes()).hexdigest()
            detected = next((p for p in PROFILES.values() if p.rom_sha1 == actual), None)
            profile = PROFILES[args.game] if args.game else detected
            if profile is None:
                raise ValueError('Unknown ROM SHA-1: '+actual+'. Use --game fusion or --game alttp with --allow-unsupported-rom for an experimental variant.')
            if detected is not None and detected != profile:
                raise ValueError('--game does not match the supplied ROM')
            output = (args.output or Path(profile.filename)).expanduser().absolute()
            if output.suffix.lower() != '.nds':
                parser.error('The output filename must end in .nds')
            report = build(runtime_directory(profile), rom, args.bios.expanduser(),
                           output, write_manifest=args.manifest, profile=profile,
                           allow_unsupported_rom=args.allow_unsupported_rom)
            verb = 'Created'
        if report.get('experimental'):
            print('WARNING: Experimental ROM variant. Compatibility is not guaranteed; this ROM has a separate save folder.', file=sys.stderr)
        if args.json:
            print(json.dumps(dict(tool_version=VERSION, output=str(output), **report), indent=2))
        else:
            print(f'{verb}: {output}\nSize: {report["package_bytes"]:,} bytes\nSHA-256: {report["package_sha256"]}')
            if not args.inspect:
                print(f'Copy to the flashcart SD root as {profile.filename}. Keep your existing {profile.directory} folder and saves.')
                print(f'Save: {report["save_path"]}')
                if args.manifest:
                    print(f'Build report: {output.with_suffix(".manifest.json")}')
        return 0
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, RuntimeError) as error:
        if args.json:
            print(json.dumps(dict(error=str(error))), file=sys.stderr)
        else:
            print(f'gba-ds-pack: {error}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('gba-ds-pack: Cancelled.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    sys.exit(main())
