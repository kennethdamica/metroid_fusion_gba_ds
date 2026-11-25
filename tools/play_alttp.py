#!/usr/bin/env python3
"""Launch the Zelda package in a separate patched-melonDS desktop profile."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
from game_profiles import ALTTP
from package_fusion import ROOT, inspect_package


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package',type=Path,default=ROOT/'artifacts/menu-banners-ds/Zelda.nds')
    p.add_argument('--prepare-only',action='store_true')
    p.add_argument('--save',type=Path,help='Copy an 8 KiB Zelda save only if this isolated profile has none')
    args=p.parse_args()
    package=args.package.resolve();inspect_package(package,profile=ALTTP)
    source=ROOT/'artifacts/melonds-desktop'
    source_app=source/'melonDS Fusion.app'
    trusted=json.loads((source/'manifest.json').read_text())
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    if trusted['jit'] or sha(source_app/'Contents/MacOS/melonDS')!=trusted['executable_sha256']:
        raise RuntimeError('Build the pinned patched desktop app first')
    dest=ROOT/'artifacts/melonds-alttp';dest.mkdir(parents=True,exist_ok=True)
    app=dest/'melonDS Zelda.app'
    if not app.exists():
        shutil.copytree(source_app,app,symlinks=True)
        plist=app/'Contents/Info.plist';info=plistlib.loads(plist.read_bytes())
        info.update(CFBundleIdentifier='local.gba-ds.melonds-zelda',CFBundleName='melonDS Zelda',CFBundleDisplayName='melonDS Zelda')
        plist.write_bytes(plistlib.dumps(info))
        subprocess.run(['codesign','--force','--deep','--sign','-',str(app)],check=True)
        (dest/'manifest.json').write_text(json.dumps(dict(source=trusted,executable_sha256=sha(app/'Contents/MacOS/melonDS')),indent=2)+'\n')
    manifest=json.loads((dest/'manifest.json').read_text())
    if sha(app/'Contents/MacOS/melonDS')!=manifest['executable_sha256']:
        raise RuntimeError('Zelda desktop executable differs from its recorded build')
    profile=dest/'portable';sd=profile/'sdcard';sd.mkdir(parents=True,exist_ok=True)
    save=sd/ALTTP.data_root/'rom.sav'
    if args.save and not save.exists():
        if args.save.stat().st_size!=8192:raise ValueError('Expected an 8 KiB Zelda save')
        save.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(args.save,save)
    config=profile/'melonDS.toml'
    if not config.exists():
        q=lambda value:json.dumps(str(value))
        # Explicit Instance0 is required: melonDS adds scalar settings there,
        # and its TOML serializer aborts if the parent was an implicit table.
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
ImagePath = {q(profile/'dldi.bin')}
FolderPath = {q(sd)}
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
Start = 16777220
Select = 16777219
Left = 16777234
Up = 16777235
Right = 16777236
Down = 16777237
L = 81
R = 87
HK_FastForwardToggle = 70
HK_Pause = 80
''')
    shutil.copy2(package,sd/ALTTP.filename)
    print(f'Patched Zelda app: {app}')
    print('Arrows move; X uses the equipped item; Z is B; Backspace opens inventory; Enter opens the save menu. Click an owned bottom-screen item to equip; use INVENTORY/MAP tabs and map floor buttons.')
    print(f'Save: {save}')
    if not args.prepare_only:subprocess.run(['open','-a',str(app),'--args',str(package)],check=True)


if __name__=='__main__':main()
