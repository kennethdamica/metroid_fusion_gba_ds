#!/usr/bin/env python3
"""Install the pinned native Apple Silicon test core into this project."""
import hashlib
from pathlib import Path
import platform
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://github.com/JesseTG/melonds-ds/releases/download/v1.4.0/melondsds_libretro-macos-arm64-Release.zip'
SHA256 = 'c02b8031408687091be8f86b2944ff6a29a4c65305828748d407a9daa7d18056'

def main():
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise SystemExit('This setup is pinned for Apple Silicon macOS.')
    if sys.version_info < (3, 13):
        raise SystemExit('Use Python 3.13 or later.')
    archive = ROOT / '.tools/downloads/melondsds-1.4.0-arm64.zip'
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        temporary = archive.with_suffix('.download')
        subprocess.run(['curl', '-fL', '--retry', '3', URL, '-o', str(temporary)], check=True)
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != SHA256:
            raise SystemExit('Download checksum mismatch')
        temporary.replace(archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        raise SystemExit('Cached archive checksum mismatch')
    destination = ROOT / '.tools/melonds'
    with zipfile.ZipFile(archive) as package:
        for name in package.namelist():
            if not (destination / name).resolve().is_relative_to(destination.resolve()):
                raise SystemExit('Unsafe archive path')
        package.extractall(destination)
    python = ROOT / '.venv/bin/python'
    if not python.exists():
        subprocess.run([sys.executable, '-m', 'venv', str(ROOT / '.venv')], check=True)
    subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt')], check=True)
    print('Native melonDS DS 1.4.0 and Python test dependencies ready.')

if __name__ == '__main__':
    main()
