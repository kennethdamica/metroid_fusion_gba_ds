#!/usr/bin/env python3
"""End-user command-line interface for the standalone Fusion packager."""
import argparse
import json
from pathlib import Path
import sys
import zipfile
from fusion_profile import GAME_NAME, FUSION_SHA1
from package_fusion import DEFAULT_RUNTIME, build, inspect_package

VERSION = '0.1.0'


def runtime_directory():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / 'runtime'
    return DEFAULT_RUNTIME


def main(argv=None):
    # A redirected Windows console may use a legacy code page. File access
    # remains Unicode; printing a path must not turn a successful build into
    # an encoding failure. JSON already escapes non-ASCII characters.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(errors='backslashreplace')
    parser = argparse.ArgumentParser(
        prog='fusion-pack', description='Create a dual-screen Fusion NDS from your ROM and GBA BIOS.',
        epilog='Example: fusion-pack "Metroid Fusion (USA).gba" --bios bios.bin -o Fusion.nds\n'
               'Works offline. No ROM or BIOS is included. Existing files are never overwritten.',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('rom', nargs='?', type=Path, help='original US Fusion .gba file')
    parser.add_argument('--bios', type=Path, help='your GBA BIOS (.bin or ZIP containing one 16 KiB BIOS)')
    parser.add_argument('-o', '--output', type=Path, help='destination .nds (default: Fusion.nds in the current folder)')
    parser.add_argument('--manifest', action='store_true', help='also save a companion build report (.manifest.json)')
    parser.add_argument('--json', action='store_true', help='print machine-readable results')
    parser.add_argument('--inspect', type=Path, metavar='NDS', help='verify an existing package without changing it')
    parser.add_argument('--list-games', action='store_true', help='show supported games and revisions')
    parser.add_argument('--version', action='version', version=f'fusion-pack {VERSION}')
    args = parser.parse_args(argv)
    if args.inspect or args.list_games:
        if args.rom or args.bios or args.output or args.manifest or (args.inspect and args.list_games):
            parser.error('Use --inspect or --list-games on its own (optionally with --json)')
    elif not args.rom or not args.bios:
        parser.error('Supply a ROM and --bios. Run fusion-pack --help for an example.')
    try:
        if args.list_games:
            games = [dict(name=GAME_NAME, sha1=FUSION_SHA1)]
            print(json.dumps(games, indent=2) if args.json else f'{GAME_NAME}\nSHA-1: {FUSION_SHA1}')
            return 0
        if args.inspect:
            report = inspect_package(args.inspect)
            verb, output = 'Verified', args.inspect.absolute()
        else:
            output = (args.output or Path('Fusion.nds')).expanduser().absolute()
            if output.suffix.lower() != '.nds':
                parser.error('The output filename must end in .nds')
            report = build(runtime_directory(), args.rom.expanduser(), args.bios.expanduser(),
                           output, write_manifest=args.manifest)
            verb = 'Created'
        if args.json:
            print(json.dumps(dict(tool_version=VERSION, output=str(output), **report), indent=2))
        else:
            print(f'{verb}: {output}\nSize: {report["package_bytes"]:,} bytes\nSHA-256: {report["package_sha256"]}')
            if not args.inspect:
                print('Copy to the flashcart SD root as Fusion.nds. Keep your existing _fusion folder and saves.')
                if args.manifest:
                    print(f'Build report: {output.with_suffix(".manifest.json")}')
        return 0
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, RuntimeError) as error:
        if args.json:
            print(json.dumps(dict(error=str(error))), file=sys.stderr)
        else:
            print(f'fusion-pack: {error}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('fusion-pack: Cancelled.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    sys.exit(main())
