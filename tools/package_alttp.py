#!/usr/bin/env python3
"""Build an experimental Zelda DS inventory package from local US ROM and BIOS."""
import argparse
import json
from pathlib import Path
from game_profiles import ALTTP
from package_fusion import build, inspect_package, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, default=ROOT/'artifacts/alttp-package-runtime')
    parser.add_argument('--rom', type=Path)
    parser.add_argument('--bios', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--inspect', type=Path)
    args = parser.parse_args()
    try:
        if args.inspect:
            report = inspect_package(args.inspect, profile=ALTTP)
        else:
            if not all((args.rom, args.bios, args.output)):
                parser.error('--rom, --bios and --output are required')
            report = build(args.runtime, args.rom, args.bios, args.output, profile=ALTTP)
        print(json.dumps(report, indent=2))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
