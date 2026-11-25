#!/usr/bin/env python3
"""Prepare an isolated desktop profile and launch Fusion in patched melonDS."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tomllib
from package_fusion import ROOT, DATA_ROOT, inspect_package


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package',type=Path,default=ROOT/'artifacts/menu-banners-ds/Fusion.nds')
    p.add_argument('--prepare-only',action='store_true')
    args=p.parse_args()
    package=args.package.resolve()
    inspect_package(package)
    dest=ROOT/'artifacts/melonds-desktop'
    app=dest/'melonDS Fusion.app'
    manifest=json.loads((dest/'manifest.json').read_text())
    executable=app/'Contents/MacOS/melonDS'
    if hashlib.sha256(executable.read_bytes()).hexdigest()!=manifest['executable_sha256'] or manifest['jit']:
        raise RuntimeError('Desktop app differs from the recorded interpreter build')
    profile=dest/'portable'
    sd=profile/'sdcard'
    sd.mkdir(parents=True,exist_ok=True)
    config=profile/'melonDS.toml'
    # Seed an existing stock-app package save once, without modifying its source.
    target_save=sd/DATA_ROOT/'rom.sav'
    stock_config=Path.home()/'Library/Preferences/melonDS/melonDS.toml'
    if not target_save.exists() and stock_config.exists():
        stock=tomllib.loads(stock_config.read_text())
        folder=stock.get('DLDI',{}).get('FolderPath')
        if folder:
            source_save=Path(folder)/DATA_ROOT/'rom.sav'
            if source_save.is_file():
                target_save.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source_save,target_save)
                print(f'Copied existing save into the separate desktop profile: {target_save}')
    if not config.exists():
        quote=lambda x:json.dumps(str(x))
        config.write_text(f'''LimitFPS = true
TargetFPS = 60.0
FastForwardFPS = 240.0
PauseLostFocus = false
AudioSync = false

[Emu]
ConsoleType = 0
DirectBoot = true
ExternalBIOSEnable = false

["3D"]
Renderer = 0

[DLDI]
Enable = true
ImageSize = 1
ReadOnly = false
FolderSync = true
ImagePath = {quote(profile/'dldi.bin')}
FolderPath = {quote(sd)}

[Instance0]

[Instance0.Window0]
Width = 512
Height = 768
ScreenLayout = 0
ScreenGap = 0
ScreenFilter = false

[Instance0.Keyboard]
A = 88
B = 90
X = 83
Y = 65
L = 81
R = 87
Start = 16777220
Select = 16777219
Left = 16777234
Up = 16777235
Right = 16777236
Down = 16777237
HK_FastForward = 16777217
HK_FastForwardToggle = 70
HK_Pause = 80
''')
    print(f'Patched app: {app}')
    print('Controls: arrows move, X=A, Z=B, Enter=Start, Backspace=Select, Q/W=L/R, F=fast-forward, P=pause.')
    if not args.prepare_only:
        subprocess.run(['open','-a',str(app),str(package)],check=True)


if __name__=='__main__':
    main()
